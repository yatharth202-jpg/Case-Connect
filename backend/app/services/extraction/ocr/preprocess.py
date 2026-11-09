import hashlib
import io
import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import imagehash
import numpy as np
from PIL import ExifTags, Image

from backend.app.config import get_extraction_config


def _estimate_skew_angle_deg(gray: np.ndarray) -> float:
    """
    Estimates document skew angle in degrees (-45..+45) from foreground text lines
    using morphological line connection and minimum-area bounding boxes / Hough lines.
    """
    h, w = gray.shape[:2]
    if h < 16 or w < 16:
        return 0.0

    # Invert so ink is positive
    inv = cv2.bitwise_not(gray)
    _, thresh = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    # Connect horizontal characters into text lines
    kernel_w = max(5, min(40, w // 25))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 3))
    connected = cv2.dilate(thresh, kernel, iterations=1)

    edges = cv2.Canny(connected, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180.0,
        threshold=max(20, w // 12),
        minLineLength=max(25, w // 10),
        maxLineGap=20,
    )
    angles = []
    if lines is not None:
        for line in lines:
            flat = np.asarray(line).reshape(-1)
            if len(flat) < 4:
                continue
            x1, y1, x2, y2 = flat[:4]
            dx = float(x2 - x1)
            dy = float(y2 - y1)
            if abs(dx) < 1e-3:
                continue
            ang = math.degrees(math.atan2(dy, dx))
            if -45.0 <= ang <= 45.0:
                angles.append(ang)

    if angles:
        return round(float(np.median(angles)), 2)

    # Fallback: minAreaRect over foreground coordinates if Hough found no lines
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 50:
        return 0.0
    rect = cv2.minAreaRect(coords)
    angle = float(rect[-1])
    if angle < -45.0:
        angle = -(90.0 + angle)
    elif angle > 45.0:
        angle = 90.0 - angle
    else:
        angle = -angle
    if abs(angle) > 45.0:
        return 0.0
    return round(float(angle), 2)


def estimate_stroke_uniformity_cv(gray: np.ndarray) -> float:
    """
    Computes the coefficient of variation (std / mean) of foreground stroke widths
    using a distance transform on binarized ink.
    Printed fonts have low variation; handwritten strokes have higher variation.
    """
    inv = cv2.bitwise_not(gray)
    _, binary = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    if np.count_nonzero(binary) < 30:
        return 0.0
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
    fg_vals = dist[dist > 0.5]
    if len(fg_vals) < 20:
        return 0.0
    mean_v = float(np.mean(fg_vals))
    if mean_v <= 1e-5:
        return 0.0
    cv_val = float(np.std(fg_vals) / mean_v)
    return round(cv_val, 4)


def assess_image_quality(
    pil_img: Image.Image,
    dpi_hint: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Evaluates image quality against configurable thresholds in `extraction.image_quality`:
    - blur_score: variance of Laplacian
    - contrast: standard deviation of grayscale intensities
    - brightness: mean grayscale intensity
    - skew_deg: estimated skew angle in degrees
    - dpi: reported or effective resolution
    Returns dict with `passed`, `status` ('ready' or 'needs_better_image'), `reason`, and `metrics`.
    """
    iq_cfg = get_extraction_config().get("image_quality", {})
    min_blur = float(iq_cfg.get("min_blur_score", 45.0))
    min_dpi = int(iq_cfg.get("min_dpi", 120))
    min_w = int(iq_cfg.get("min_width_px", 150))
    min_h = int(iq_cfg.get("min_height_px", 80))
    max_skew = float(iq_cfg.get("max_skew_deg", 25.0))
    min_contrast = float(iq_cfg.get("min_contrast", 20.0))
    min_brightness = float(iq_cfg.get("min_brightness", 15.0))
    max_brightness = float(iq_cfg.get("max_brightness", 252.0))

    rgb = np.array(pil_img.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape[:2]

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(np.std(gray))
    brightness = float(np.mean(gray))
    skew_deg = _estimate_skew_angle_deg(gray)
    stroke_cv = estimate_stroke_uniformity_cv(gray)

    # Check DPI from image info or hint
    img_dpi = pil_img.info.get("dpi")
    if dpi_hint:
        effective_dpi = int(dpi_hint)
    elif isinstance(img_dpi, (tuple, list)) and len(img_dpi) >= 1 and img_dpi[0]:
        effective_dpi = int(round(float(img_dpi[0])))
    else:
        # Estimate effective DPI assuming standard A4 width (8.27 in) or minimum pixel check
        effective_dpi = max(min_dpi, int(round(max(width, height) / 8.27))) if (width >= min_w and height >= min_h) else int(round(max(width, height) / 8.27))

    reasons = []
    if width < min_w or height < min_h:
        reasons.append(
            f"Image dimensions ({width}x{height}px) are below minimum required resolution ({min_w}x{min_h}px)"
        )
    if effective_dpi < min_dpi:
        reasons.append(
            f"Image resolution ({effective_dpi} DPI) is below minimum threshold ({min_dpi} DPI)"
        )
    if lap_var < min_blur:
        reasons.append(
            f"Image blur score ({lap_var:.1f}) is below minimum threshold ({min_blur:.1f}); image appears out of focus"
        )
    if contrast < min_contrast:
        reasons.append(
            f"Image contrast ({contrast:.1f}) is below minimum threshold ({min_contrast:.1f})"
        )
    if brightness < min_brightness or brightness > max_brightness:
        reasons.append(
            f"Image brightness ({brightness:.1f}) is outside acceptable range ({min_brightness:.1f}..{max_brightness:.1f})"
        )
    if abs(skew_deg) > max_skew:
        reasons.append(
            f"Image skew angle ({skew_deg:.1f} deg) exceeds maximum threshold ({max_skew:.1f} deg)"
        )

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "status": "ready" if passed else "needs_better_image",
        "reason": "; ".join(reasons) if reasons else None,
        "metrics": {
            "blur_score": round(lap_var, 2),
            "contrast": round(contrast, 2),
            "brightness": round(brightness, 2),
            "skew_deg": round(skew_deg, 2),
            "dpi": effective_dpi,
            "width": width,
            "height": height,
            "stroke_uniformity_cv": stroke_cv,
        },
    }


def preprocess_for_ocr(
    pil_img: Image.Image,
    quality_metrics: Optional[Dict[str, Any]] = None,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Applies config-driven OpenCV preprocessing for OCR:
    1. Deskew if abs(skew_deg) >= deskew_min_deg.
    2. Fast non-local means denoising.
    3. Adaptive Gaussian thresholding / contrast normalization.
    Returns (preprocessed_pil_image, preprocess_params_dict).
    """
    iq_cfg = get_extraction_config().get("image_quality", {})
    prep_cfg = iq_cfg.get("preprocess", {})
    deskew_min = float(prep_cfg.get("deskew_min_deg", 0.5))
    denoise_h = float(prep_cfg.get("denoise_h", 8.0))
    block_size = int(prep_cfg.get("adaptive_block_size", 31))
    if block_size % 2 == 0:
        block_size += 1
    adaptive_c = int(prep_cfg.get("adaptive_c", 10))

    rgb = np.array(pil_img.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    skew_deg = (
        float(quality_metrics.get("skew_deg", 0.0))
        if quality_metrics and "skew_deg" in quality_metrics
        else _estimate_skew_angle_deg(gray)
    )

    applied_deskew = 0.0
    if abs(skew_deg) >= deskew_min:
        h, w = gray.shape[:2]
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, skew_deg, 1.0)
        gray = cv2.warpAffine(
            gray,
            rot_mat,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        applied_deskew = round(skew_deg, 2)

    if denoise_h > 0:
        denoised = cv2.fastNlMeansDenoising(gray, None, h=denoise_h, templateWindowSize=7, searchWindowSize=21)
    else:
        denoised = gray

    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        adaptive_c,
    )

    out_pil = Image.fromarray(binary).convert("RGB")
    params = {
        "deskew_applied_deg": applied_deskew,
        "denoise_h": denoise_h,
        "adaptive_block_size": block_size,
        "adaptive_c": adaptive_c,
    }
    return out_pil, params


def _convert_gps_coord(coord_tuple, ref: str) -> Optional[float]:
    try:
        deg = float(coord_tuple[0])
        minutes = float(coord_tuple[1])
        seconds = float(coord_tuple[2])
        val = deg + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ("S", "W"):
            val = -val
        return round(val, 6)
    except Exception:
        return None


def extract_exif_and_hashes(pil_img: Image.Image) -> Dict[str, Any]:
    """
    Extracts EXIF metadata (capture_time, device_make, device_model, gps, software)
    tagged explicitly as 'as reported by file', plus SHA-256 of raw PNG bytes and
    perceptual hash (imagehash.phash) for duplicate-image detection across a case.
    """
    exif_out: Dict[str, Any] = {
        "disclaimer": "as reported by file",
        "capture_time": None,
        "device_make": None,
        "device_model": None,
        "software": None,
        "gps": None,
    }

    try:
        raw_exif = pil_img.getexif()
        if raw_exif:
            tag_map = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}
            if "DateTimeOriginal" in tag_map or "DateTime" in tag_map:
                exif_out["capture_time"] = str(tag_map.get("DateTimeOriginal") or tag_map.get("DateTime")).strip()
            if "Make" in tag_map:
                exif_out["device_make"] = str(tag_map["Make"]).strip()
            if "Model" in tag_map:
                exif_out["device_model"] = str(tag_map["Model"]).strip()
            if "Software" in tag_map:
                exif_out["software"] = str(tag_map["Software"]).strip()

            # Check GPS IFD (0x8825)
            gps_ifd = None
            try:
                gps_ifd = raw_exif.get_ifd(0x8825)
            except Exception:
                gps_ifd = tag_map.get("GPSInfo")
            if isinstance(gps_ifd, dict) and gps_ifd:
                gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}
                lat = _convert_gps_coord(gps_tags.get("GPSLatitude"), str(gps_tags.get("GPSLatitudeRef", "N")))
                lon = _convert_gps_coord(gps_tags.get("GPSLongitude"), str(gps_tags.get("GPSLongitudeRef", "E")))
                if lat is not None and lon is not None:
                    exif_out["gps"] = {"lat": lat, "lon": lon, "as_reported_by_file": True}
    except Exception:
        pass

    # Compute perceptual hash and page image SHA-256
    phash_hex = str(imagehash.phash(pil_img))
    buf = io.BytesIO()
    pil_img.convert("RGB").save(buf, format="PNG")
    img_sha256 = hashlib.sha256(buf.getvalue()).hexdigest()

    return {
        "exif": exif_out,
        "perceptual_hash": phash_hex,
        "page_image_sha256": img_sha256,
    }


def phash_distance(hash_a: Optional[str], hash_b: Optional[str]) -> int:
    """Computes Hamming distance between two hex perceptual hashes."""
    if not hash_a or not hash_b:
        return 999
    try:
        return int(imagehash.hex_to_hash(hash_a) - imagehash.hex_to_hash(hash_b))
    except Exception:
        return 999
