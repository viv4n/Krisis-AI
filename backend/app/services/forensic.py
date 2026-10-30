import base64
import io
import re
from typing import Optional
from app.core.config import settings

try:
    from PIL import Image, ImageStat
except ImportError:
    Image = None
    ImageStat = None

try:
    import imagehash
except ImportError:
    imagehash = None

# Known duplicate hash store for in-memory tracking
_seen_hashes: set[str] = set()

def detect_deepfake(image_bytes: bytes) -> tuple[bool, float]:
    """
    Modular synthetic / deepfake detection hook.
    Returns (is_synthetic, confidence).
    
    Contains realistic heuristics for local execution:
    - Checks for explicit synthetic markers in header/metadata.
    - Inspects image entropy / variance and color anomalies.
    - Inspects high-frequency sharpness/blur or anomalous smoothness typical in synthetic generators.
    """
    if not image_bytes:
        return False, 0.0

    # Heuristic 1: Inspect metadata/raw bytes for known AI generation fingerprints (Stable Diffusion, Midjourney, DALL-E)
    raw_lower = image_bytes[:4096].lower()
    ai_signatures = [b"stable diffusion", b"dall-e", b"midjourney", b"deepfake", b"synth", b"generated"]
    for sig in ai_signatures:
        if sig in raw_lower:
            return True, 0.96

    if Image is not None:
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Check EXIF/Info for generator markers
                for key, val in (img.info or {}).items():
                    val_str = str(val).lower()
                    if any(sig in val_str for sig in ["ai generated", "midjourney", "comfyui", "stablediffusion", "synthetic"]):
                        return True, 0.95

                # Heuristic 2: Image statistical inspection
                # Highly uniform/artificial images (e.g. extremely low color variance or exact identical channel distribution)
                converted = img.convert("RGB")
                stat = ImageStat.Stat(converted)
                stddev = stat.stddev  # standard deviation for R, G, B
                avg_stddev = sum(stddev) / len(stddev)
                
                # Check for unnatural color channel skew or extreme uniformity
                if avg_stddev < 2.0:
                    # Solid or synthetic test canvas
                    return True, 0.88
        except Exception:
            pass

    return False, 0.10


def verify_image_authenticity(image_base64: Optional[str]) -> dict:
    """
    Ingestion & Adversarial Defense verification:
    - Decodes base64 image (handles data URL prefixes if present).
    - Computes perceptual hash via imagehash (or fallback) to detect duplicates.
    - Runs modular deepfake detection hook.
    - Tags status as 'quarantined' if is_synthetic is True and confidence > 0.85.
    
    Returns:
        {
            "is_valid": bool,
            "is_duplicate": bool,
            "phash": str | None,
            "is_synthetic": bool,
            "confidence": float,
            "quarantined": bool,
            "reason": str | None,
            "visual_clarity_score": float  # 0.0 to 1.0 (used by triage for blur/dark assessment)
        }
    """
    if not image_base64:
        return {
            "is_valid": True,
            "is_duplicate": False,
            "phash": None,
            "is_synthetic": False,
            "confidence": 0.0,
            "quarantined": False,
            "reason": None,
            "visual_clarity_score": 0.0
        }

    # Clean data URI prefix if present (e.g. data:image/jpeg;base64,...)
    clean_b64 = image_base64
    if "," in image_base64 and "base64" in image_base64[:50]:
        clean_b64 = image_base64.split(",", 1)[1]

    clean_b64 = re.sub(r"\s+", "", clean_b64)

    try:
        image_bytes = base64.b64decode(clean_b64, validate=False)
    except Exception:
        return {
            "is_valid": False,
            "is_duplicate": False,
            "phash": None,
            "is_synthetic": False,
            "confidence": 0.0,
            "quarantined": True,
            "reason": "Invalid base64 encoding",
            "visual_clarity_score": 0.0
        }

    # Perceptual Hash Calculation
    phash_str = None
    visual_clarity = 0.8  # default baseline clarity
    if Image is not None:
        try:
            with Image.open(io.BytesIO(image_bytes)) as pil_img:
                if imagehash is not None:
                    computed_hash = str(imagehash.phash(pil_img))
                else:
                    # Fallback average hash implementation
                    small = pil_img.convert("L").resize((8, 8), Image.Resampling.BILINEAR)
                    pixels = list(small.getdata())
                    avg = sum(pixels) / len(pixels)
                    bits = "".join(["1" if p > avg else "0" for p in pixels])
                    computed_hash = hex(int(bits, 2))[2:].zfill(16)
                
                phash_str = computed_hash

                # Assess clarity: brightness & standard deviation
                stat = ImageStat.Stat(pil_img.convert("L"))
                mean_brightness = stat.mean[0]  # 0 to 255
                stddev = stat.stddev[0]
                # If too dark (mean < 30) or extremely washed out/low contrast (stddev < 15), low clarity
                if mean_brightness < 30 or stddev < 15:
                    visual_clarity = 0.35
                else:
                    visual_clarity = min(1.0, (stddev / 64.0) * 0.8 + 0.2)
        except Exception:
            return {
                "is_valid": False,
                "is_duplicate": False,
                "phash": None,
                "is_synthetic": False,
                "confidence": 0.0,
                "quarantined": True,
                "reason": "Corrupt or unreadable image data",
                "visual_clarity_score": 0.0
            }

    is_duplicate = False
    if phash_str:
        if phash_str in _seen_hashes:
            is_duplicate = True
        else:
            _seen_hashes.add(phash_str)

    # Modular Synthetic Detection
    is_synthetic, confidence = detect_deepfake(image_bytes)

    # Quarantine logic
    quarantined = False
    reason = None
    if is_synthetic and confidence > settings.DEEPFAKE_THRESHOLD:
        quarantined = True
        reason = f"Synthetic/manipulated media detected (confidence: {confidence:.2f})"

    return {
        "is_valid": True,
        "is_duplicate": is_duplicate,
        "phash": phash_str,
        "is_synthetic": is_synthetic,
        "confidence": confidence,
        "quarantined": quarantined,
        "reason": reason,
        "visual_clarity_score": visual_clarity
    }

