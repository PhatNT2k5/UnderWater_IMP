"""Linear feature transforms applied to tokens and bank before nearest-neighbour search (P4.3).

- `nuisance` (NFAD-style): remove the k directions along which the environment moves DINOv2
  tokens, estimated from the same bank-capture frames degraded at severity 1 (the bank's
  augmentation level; severities 2-5 stay unseen). z' = normalise(z - V V^T z), cosine search.
  Caveat (ShiftSplit-AD): damage may share these directions, so it is kept only if the
  development benchmark shows it helps.
- `mahalanobis`: whiten with the bank's mean and shrunk covariance, z' = (z - mu) Sigma^-1/2,
  Euclidean search (Mahalanobis PatchCore).
- a chain applies several in order (nuisance projection, then whitening of the projected bank).
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F

KINDS = ("nuisance", "mahalanobis")


@dataclass(frozen=True)
class FeatureTransform:
    kind: str
    matrix: torch.Tensor             # (C, C), applied as x @ matrix
    mean: torch.Tensor | None = None  # subtracted first (mahalanobis)

    @property
    def metric(self) -> str:
        return "euclidean" if self.kind == "mahalanobis" else "cosine"

    def apply(self, tokens: torch.Tensor) -> torch.Tensor:
        x = tokens.float()
        if self.mean is not None:
            x = x - self.mean
        x = x @ self.matrix
        return F.normalize(x, dim=-1) if self.metric == "cosine" else x

    def to(self, device: torch.device) -> "FeatureTransform":
        return FeatureTransform(self.kind, self.matrix.to(device),
                                None if self.mean is None else self.mean.to(device))

    def state(self) -> dict:
        return {"kind": self.kind, "matrix": self.matrix.cpu(),
                "mean": None if self.mean is None else self.mean.cpu()}


@dataclass(frozen=True)
class ChainedTransform:
    steps: tuple[FeatureTransform, ...]

    @property
    def metric(self) -> str:
        return self.steps[-1].metric

    def apply(self, tokens: torch.Tensor) -> torch.Tensor:
        for step in self.steps:
            tokens = step.apply(tokens)
        return tokens

    def to(self, device: torch.device) -> "ChainedTransform":
        return ChainedTransform(tuple(step.to(device) for step in self.steps))

    def state(self) -> list[dict]:
        return [step.state() for step in self.steps]


def from_state(state: dict | list) -> FeatureTransform | ChainedTransform:
    if isinstance(state, list):
        if not state:
            raise ValueError("Empty transform chain")
        return ChainedTransform(tuple(from_state(step) for step in state))
    if state["kind"] not in KINDS:
        raise ValueError(f"Unknown transform kind {state['kind']!r}")
    return FeatureTransform(state["kind"], state["matrix"], state.get("mean"))


def nuisance_projection(scatter: torch.Tensor, k: int) -> tuple[FeatureTransform, float]:
    """Projection removing the top-k eigenvectors of the nuisance scatter; returns explained share."""
    if not 0 < k < scatter.shape[0]:
        raise ValueError("k must be between 1 and the feature dimension - 1")
    values, vectors = torch.linalg.eigh(scatter.double())
    order = torch.argsort(values, descending=True)
    top = vectors[:, order[:k]]
    explained = float(values[order[:k]].sum() / values.clamp_min(0).sum())
    projection = torch.eye(scatter.shape[0], dtype=torch.float64) - top @ top.T
    return FeatureTransform("nuisance", projection.float()), explained


def mahalanobis_whitening(bank: torch.Tensor, shrinkage: float = 0.1) -> FeatureTransform:
    """Sigma_reg = (1 - s) Sigma + s * (trace / C) I; matrix = Sigma_reg^-1/2."""
    if not 0 <= shrinkage < 1:
        raise ValueError("shrinkage must be in [0, 1)")
    x = bank.double()
    mean = x.mean(0)
    centred = x - mean
    sigma = centred.T @ centred / max(len(x) - 1, 1)
    sigma = (1 - shrinkage) * sigma + shrinkage * torch.trace(sigma) / sigma.shape[0] * torch.eye(
        sigma.shape[0], dtype=torch.float64)
    values, vectors = torch.linalg.eigh(sigma)
    inverse_root = vectors @ torch.diag(values.clamp_min(1e-12).rsqrt()) @ vectors.T
    return FeatureTransform("mahalanobis", inverse_root.float(), mean.float())
