"""DINOv2 ViT-S/14 patch tokens for a camera frame (AnomalyDINO-style features).

The frame is resized by `scale` to the nearest multiple of the 14 px patch, so one token covers
14 / scale camera pixels (7 px at the default scale 2, about 4 cm at 2 m). Tokens are L2
normalised so that nearest-neighbour search is a cosine similarity.
Measured on the RTX 3050 4 GB without Unreal: 21.5 ms at scale 1, 114 ms at scale 2 (fp16).
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import torch
import torch.nn.functional as F

MODEL_NAME = "vit_small_patch14_dinov2.lvd142m"
PATCH_PX = 14
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass
class DinoExtractor:
    model: torch.nn.Module
    device: torch.device
    scale: float

    @property
    def dtype(self) -> torch.dtype:
        return torch.float16 if self.device.type == "cuda" else torch.float32


def load_extractor(device: torch.device, scale: float = 2.0) -> DinoExtractor:
    import timm  # dependency of anomalib; weights come from the Hugging Face cache
    if scale <= 0:
        raise ValueError("scale must be positive")
    model = timm.create_model(MODEL_NAME, pretrained=True, dynamic_img_size=True).to(device).eval()
    extractor = DinoExtractor(model, device, scale)
    model.to(extractor.dtype)
    return extractor


def input_size(height: int, width: int, scale: float) -> tuple[int, int]:
    """Network input (height, width): scaled frame rounded to whole patches."""
    return (max(1, round(height * scale / PATCH_PX)) * PATCH_PX,
            max(1, round(width * scale / PATCH_PX)) * PATCH_PX)


@torch.inference_mode()
def frame_tokens(extractor: DinoExtractor, frame_bgr: np.ndarray) -> torch.Tensor:
    """(grid_h, grid_w, channels) L2-normalised patch tokens of one BGR frame."""
    height, width = input_size(*frame_bgr.shape[:2], extractor.scale)
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb = cv2.resize((rgb - MEAN) / STD, (width, height), interpolation=cv2.INTER_LINEAR)
    batch = torch.from_numpy(rgb.transpose(2, 0, 1).copy()).unsqueeze(0).to(extractor.device, extractor.dtype)
    tokens = extractor.model.forward_features(batch)[0, extractor.model.num_prefix_tokens:]
    grid = tokens.reshape(height // PATCH_PX, width // PATCH_PX, -1)
    return F.normalize(grid.float(), dim=-1).to(extractor.dtype)


def roi_cells(roi: np.ndarray, grid_shape: tuple[int, int], erosion_px: int = 0) -> np.ndarray:
    """Grid cells whose centre lies inside the (optionally eroded) ROI."""
    mask = (roi > 0).astype(np.uint8)
    if erosion_px:
        size = 2 * erosion_px + 1
        mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))
    return cv2.resize(mask, (grid_shape[1], grid_shape[0]), interpolation=cv2.INTER_NEAREST) > 0
