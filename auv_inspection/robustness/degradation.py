"""Seeded underwater and camera degradations with five severity levels per factor.

Used to build evaluation sets with held-out conditions (GENERALIZATION_PLAN.md, P1 and
section 3.8). Never apply these as live preprocessing: the same processing would have
to be applied to train, calibration, test and live frames alike.

Physical basis of the water model (all coefficients are severity presets chosen to span
clear to very turbid water at the 2 m inspection standoff, not fitted Jerlov values):

    I = J·exp(-β z) + blur_{φz}(J·(exp(-G z) - exp(-β z))) + B∞·(1 - exp(-β z))
        direct          small-angle forward scattering         backscatter

Akkaynak & Treibitz (CVPR 2018) for the direct/backscatter terms; Ismiroglou et al.
(2025) for the forward-scattering term, G < β, and a Gaussian random field that makes
the medium non-uniform. Marine snow follows the particle overlay idea of the Marine
Snow Removal Benchmark (Sato/Kaneko et al., 2021-2024). Sensor noise is Poisson-Gaussian.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path

import cv2
import numpy as np

SEVERITY_LEVELS = (1, 2, 3, 4, 5)

# Mean attenuation β (1/m) per severity; transmission at 2 m goes from ~0.74 to ~0.09.
TURBIDITY_BETA_PER_M = (0.15, 0.3, 0.5, 0.8, 1.2)
# Relative RGB attenuation (red absorbed fastest) and veiling-light colour, both RGB.
TURBIDITY_RGB_RATIO = (1.6, 1.0, 0.9)
BACKSCATTER_RGB = (0.03, 0.20, 0.28)
FORWARD_ATTENUATION_RATIO = 0.6  # G = ratio·β, so some scattered light still reaches the lens
FORWARD_BLUR_PX_PER_M = (0.5, 1.0, 1.5, 2.0, 3.0)
MEDIUM_INHOMOGENEITY = (0.1, 0.15, 0.2, 0.25, 0.3)  # GRF scales z by 1 ± this

MARINE_SNOW_PARTICLES = (30, 80, 180, 350, 600)
MARINE_SNOW_MAX_RADIUS_PX = (1.5, 2.0, 2.5, 3.5, 4.5)
MARINE_SNOW_STREAK_FRACTION = 0.15

SENSOR_PHOTONS_AT_WHITE = (400.0, 150.0, 60.0, 25.0, 10.0)
SENSOR_READ_NOISE = (0.004, 0.008, 0.015, 0.025, 0.04)
MOTION_BLUR_LENGTH_PX = (3, 7, 11, 17, 25)
DEFOCUS_RADIUS_PX = (1, 2, 3, 5, 7)
ILLUMINATION_GAIN = (0.8, 0.65, 0.5, 0.35, 0.25)  # weaker lights / exposure, applied to scene radiance
JPEG_QUALITY = (70, 50, 35, 20, 10)

DEFAULT_STANDOFF_M = 2.0


@dataclass(frozen=True)
class Degradation:
    factor: str
    severity: int


def check_severity(severity: int) -> int:
    if severity not in SEVERITY_LEVELS:
        raise ValueError(f"Severity must be one of {SEVERITY_LEVELS}, got {severity}")
    return severity - 1


def to_float(frame: np.ndarray) -> np.ndarray:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected a BGR uint8 frame")
    return frame.astype(np.float32) / 255.0


def to_uint8(image: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(image * 255.0), 0, 255).astype(np.uint8)


def bgr(rgb: tuple[float, float, float]) -> np.ndarray:
    return np.asarray(rgb[::-1], np.float32)


def uniform_depth(shape: tuple[int, int], standoff_m: float = DEFAULT_STANDOFF_M) -> np.ndarray:
    """Constant range until P2 supplies geometric per-pixel depth.

    A structure-vs-background split was tried and rejected: nearby seabed pixels are
    outside the ROI, so treating them as distant water erased them and left a hard edge.
    """
    return np.full(shape, standoff_m, np.float32)


def gaussian_random_field(shape: tuple[int, int], rng: np.random.Generator,
                          exponent: float = 3.0) -> np.ndarray:
    """Scale-free smooth noise in [-1, 1], resembling turbid-water density variations."""
    height, width = shape
    noise = np.fft.fft2(rng.standard_normal(shape))
    fy = np.fft.fftfreq(height)[:, None]
    fx = np.fft.fftfreq(width)[None, :]
    radius = np.hypot(fx, fy)
    radius[0, 0] = 1.0
    field = np.real(np.fft.ifft2(noise / radius ** (exponent / 2.0)))
    field -= field.mean()
    return (field / max(np.abs(field).max(), 1e-6)).astype(np.float32)


def blur_by_depth(image: np.ndarray, sigma_px: np.ndarray, bands: int = 4) -> np.ndarray:
    """Depth-varying Gaussian blur by interpolating a few uniformly blurred copies."""
    low, high = float(sigma_px.min()), float(sigma_px.max())
    if high < 0.3:
        return image
    levels = np.linspace(low, high, bands) if high - low > 1e-3 else np.array([high])
    stack = [cv2.GaussianBlur(image, (0, 0), max(level, 0.3)) for level in levels]
    if len(stack) == 1:
        return stack[0]
    position = (sigma_px - low) / (high - low) * (bands - 1)
    lower = np.clip(np.floor(position).astype(int), 0, bands - 2)
    weight = (position - lower)[..., None]
    stack_array = np.stack(stack)
    rows, cols = np.indices(sigma_px.shape)
    return (stack_array[lower, rows, cols] * (1 - weight)
            + stack_array[lower + 1, rows, cols] * weight)


def turbidity(image: np.ndarray, severity: int, rng: np.random.Generator,
              depth_m: np.ndarray) -> np.ndarray:
    level = check_severity(severity)
    ratio = bgr(TURBIDITY_RGB_RATIO)
    beta = TURBIDITY_BETA_PER_M[level] * ratio
    field = gaussian_random_field(depth_m.shape, rng)
    z = (depth_m * (1.0 + MEDIUM_INHOMOGENEITY[level] * field))[..., None]
    direct_transmission = np.exp(-beta * z)
    forward_transmission = np.exp(-FORWARD_ATTENUATION_RATIO * beta * z)
    forward = blur_by_depth(image * (forward_transmission - direct_transmission),
                            FORWARD_BLUR_PX_PER_M[level] * z[..., 0])
    backscatter = bgr(BACKSCATTER_RGB) * (1.0 - direct_transmission)
    return image * direct_transmission + forward + backscatter


def marine_snow(image: np.ndarray, severity: int, rng: np.random.Generator) -> np.ndarray:
    level = check_severity(severity)
    height, width = image.shape[:2]
    alpha = np.zeros((height, width), np.float32)
    for _ in range(MARINE_SNOW_PARTICLES[level]):
        radius = rng.uniform(0.5, MARINE_SNOW_MAX_RADIUS_PX[level])
        cx, cy = float(rng.uniform(0, width)), float(rng.uniform(0, height))
        streak = rng.random() < MARINE_SNOW_STREAK_FRACTION  # motion during exposure
        length = rng.uniform(2.0, 4.0) * radius if streak else 0.0
        angle = rng.uniform(0, np.pi)
        # Draw into a small local patch only; full-frame stamps made level 5 take ~2 s.
        margin = int(np.ceil(length + 3 * radius + 2))
        x0, y0 = max(int(cx) - margin, 0), max(int(cy) - margin, 0)
        x1, y1 = min(int(cx) + margin + 1, width), min(int(cy) + margin + 1, height)
        if x1 <= x0 or y1 <= y0:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dx, dy = xx - cx, yy - cy
        if streak:  # distance to a short segment through the centre
            along = np.clip(dx * np.cos(angle) + dy * np.sin(angle), 0.0, length)
            dx, dy = dx - along * np.cos(angle), dy - along * np.sin(angle)
        stamp = np.exp(-(dx ** 2 + dy ** 2) / (2.0 * radius ** 2)) * rng.uniform(0.3, 0.9)
        alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], stamp)
    particle_colour = np.asarray([0.85, 0.92, 0.95], np.float32)  # BGR, slightly blue-white
    return image * (1.0 - alpha[..., None]) + particle_colour * alpha[..., None]


def illumination(image: np.ndarray, severity: int, rng: np.random.Generator) -> np.ndarray:
    level = check_severity(severity)
    height, width = image.shape[:2]
    # Weaker lights also shift the hotspot: a broad off-centre falloff on top of the gain.
    cy, cx = rng.uniform(0.35, 0.65) * height, rng.uniform(0.35, 0.65) * width
    yy, xx = np.indices((height, width), dtype=np.float32)
    falloff = np.exp(-(((xx - cx) / width) ** 2 + ((yy - cy) / height) ** 2) * (level + 1))
    return image * (ILLUMINATION_GAIN[level] * (0.6 + 0.4 * falloff))[..., None]


def defocus(image: np.ndarray, severity: int, rng: np.random.Generator) -> np.ndarray:
    radius = DEFOCUS_RADIUS_PX[check_severity(severity)]
    kernel = np.zeros((2 * radius + 1, 2 * radius + 1), np.float32)
    cv2.circle(kernel, (radius, radius), radius, 1.0, -1)
    return cv2.filter2D(image, -1, kernel / kernel.sum(), borderType=cv2.BORDER_REFLECT)


def motion_blur(image: np.ndarray, severity: int, rng: np.random.Generator) -> np.ndarray:
    length = MOTION_BLUR_LENGTH_PX[check_severity(severity)]
    kernel = np.zeros((length, length), np.float32)
    kernel[length // 2, :] = 1.0
    rotation = cv2.getRotationMatrix2D(((length - 1) / 2, (length - 1) / 2),
                                       float(rng.uniform(0, 180)), 1.0)
    kernel = cv2.warpAffine(kernel, rotation, (length, length))
    return cv2.filter2D(image, -1, kernel / max(kernel.sum(), 1e-6), borderType=cv2.BORDER_REFLECT)


def sensor_noise(image: np.ndarray, severity: int, rng: np.random.Generator) -> np.ndarray:
    level = check_severity(severity)
    photons = SENSOR_PHOTONS_AT_WHITE[level]
    shot = rng.poisson(np.clip(image, 0, 1) * photons).astype(np.float32) / photons
    return shot + rng.normal(0.0, SENSOR_READ_NOISE[level], image.shape).astype(np.float32)


def jpeg(image: np.ndarray, severity: int, rng: np.random.Generator) -> np.ndarray:
    quality = JPEG_QUALITY[check_severity(severity)]
    success, encoded = cv2.imencode(".jpg", to_uint8(image), [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not success:
        raise OSError("JPEG encoding failed")
    return cv2.imdecode(encoded, cv2.IMREAD_COLOR).astype(np.float32) / 255.0


# Physical order: medium, particles in the medium, lighting/exposure, optics, motion, sensor, codec.
PIPELINE_ORDER = ("turbidity", "marine_snow", "illumination", "defocus", "motion_blur",
                  "sensor_noise", "jpeg")
FACTORS = {"marine_snow": marine_snow, "illumination": illumination, "defocus": defocus,
           "motion_blur": motion_blur, "sensor_noise": sensor_noise, "jpeg": jpeg}


def apply_degradations(frame: np.ndarray, degradations: list[Degradation], seed: int,
                       depth_m: np.ndarray | None = None) -> np.ndarray:
    """Apply factors in physical order; the same seed always yields the same image."""
    names = [item.factor for item in degradations]
    unknown = set(names) - set(PIPELINE_ORDER)
    if unknown or len(set(names)) != len(names):
        raise ValueError(f"Unknown or repeated factors: {sorted(unknown) or names}")
    image = to_float(frame)
    depth = depth_m if depth_m is not None else uniform_depth(frame.shape[:2])
    if depth.shape != frame.shape[:2]:
        raise ValueError("Depth map must match the frame size")
    by_name = {item.factor: item.severity for item in degradations}
    for index, name in enumerate(PIPELINE_ORDER):
        if name not in by_name:
            continue
        rng = np.random.default_rng([seed, index])  # independent stream per factor
        if name == "turbidity":
            image = turbidity(image, by_name[name], rng, depth)
        else:
            image = FACTORS[name](image, by_name[name], rng)
    return to_uint8(image)


def parse_degradation(text: str) -> Degradation:
    factor, _, severity = text.partition(":")
    if factor not in PIPELINE_ORDER or not severity.isdigit():
        raise argparse.ArgumentTypeError(f"Use factor:severity with factor in {PIPELINE_ORDER}")
    check_severity(int(severity))
    return Degradation(factor, int(severity))


def degrade_folder(source: Path, destination: Path, degradations: list[Degradation],
                   seed: int) -> dict:
    """Degrade every PNG in `source` into a new folder and record the exact parameters.

    Frame i uses seed + i, so particles and noise change between frames as in video while
    the whole folder stays reproducible.
    """
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    images = sorted(source.rglob("*.png"))
    if not images:
        raise FileNotFoundError(f"No PNG files in {source}")
    destination.mkdir(parents=True)
    for index, path in enumerate(images):
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if frame is None:
            raise OSError(f"Cannot read {path}")
        output = destination / path.relative_to(source)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output), apply_degradations(frame, degradations, seed + index)):
            raise OSError(f"Cannot write {output}")
    record = {"source": str(source.resolve()), "seed": seed, "images": len(images),
              "degradations": [asdict(item) for item in degradations],
              "depth_model": "uniform_standoff", "standoff_m": DEFAULT_STANDOFF_M}
    (destination / "degradation.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--degradation", type=parse_degradation, action="append", required=True,
                        help="factor:severity, repeatable, e.g. turbidity:3 --degradation marine_snow:2")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(degrade_folder(args.source, args.destination, args.degradation,
                                    args.seed), indent=2))


if __name__ == "__main__":
    main()
