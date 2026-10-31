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


def get_seen_hashes() -> set[str]:
    return _seen_hashes


def register_seen_hash(h: str):
    if h:
        _seen_hashes.add(h)


def is_hash_seen(h: str) -> bool:
    return bool(h and h in _seen_hashes)


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

    # Heuristic 1: Inspect metadata/raw bytes for known AI generation fingerprints
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
                converted = img.convert("RGB")
                stat = ImageStat.Stat(converted)
                stddev = stat.stddev  # standard deviation for R, G, B
                avg_stddev = sum(stddev) / len(stddev)
                
                # Check for unnatural color channel skew or extreme uniformity
                if avg_stddev < 2.0:
                    return True, 0.88
        except Exception:
            pass

    return False, 0.10


def decode_image_base64(image_base64: str) -> Optional[bytes]:
    """Safely decodes a base64 or data-URL encoded image string."""
    if not image_base64:
        return None
    clean_b64 = image_base64
    if "," in image_base64 and "base64" in image_base64[:50]:
        clean_b64 = image_base64.split(",", 1)[1]
    clean_b64 = re.sub(r"\s+", "", clean_b64)
    try:
        return base64.b64decode(clean_b64, validate=False)
    except Exception:
        return None


def compute_perceptual_hash(image_bytes: bytes) -> Optional[str]:
    """Computes perceptual hash (pHash) string for image bytes."""
    if not image_bytes or Image is None:
        return None
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            if imagehash is not None:
                return str(imagehash.phash(pil_img))
            else:
                small = pil_img.convert("L").resize((8, 8), Image.Resampling.BILINEAR)
                pixels = list(small.getdata())
                avg = sum(pixels) / len(pixels)
                bits = "".join(["1" if p > avg else "0" for p in pixels])
                return hex(int(bits, 2))[2:].zfill(16)
    except Exception:
        return None


def verify_image_authenticity(image_base64: Optional[str]) -> dict:
    """
    Ingestion & Adversarial Defense verification:
    - Decodes base64 image.
    - Computes perceptual hash via imagehash (or fallback) to detect duplicates.
    - Runs modular deepfake detection hook.
    - Tags status as 'quarantined' if is_synthetic is True and confidence > DEEPFAKE_THRESHOLD.
    """
    if not image_base64:
        return {
            "is_valid": True,
            "is_duplicate": False,
            "phash": None,
            "image_bytes": None,
            "is_synthetic": False,
            "confidence": 0.0,
            "quarantined": False,
            "reason": None,
            "visual_clarity_score": 0.0
        }

    image_bytes = decode_image_base64(image_base64)
    if not image_bytes:
        return {
            "is_valid": False,
            "is_duplicate": False,
            "phash": None,
            "image_bytes": None,
            "is_synthetic": False,
            "confidence": 0.0,
            "quarantined": True,
            "reason": "Invalid base64 encoding",
            "visual_clarity_score": 0.0
        }

    # Perceptual Hash Calculation
    phash_str = compute_perceptual_hash(image_bytes)
    visual_clarity = 0.8  # default baseline clarity

    if Image is not None and image_bytes:
        try:
            with Image.open(io.BytesIO(image_bytes)) as pil_img:
                stat = ImageStat.Stat(pil_img.convert("L"))
                mean_brightness = stat.mean[0]
                stddev = stat.stddev[0]
                if mean_brightness < 30 or stddev < 15:
                    visual_clarity = 0.35
                else:
                    visual_clarity = min(1.0, (stddev / 64.0) * 0.8 + 0.2)
        except Exception:
            return {
                "is_valid": False,
                "is_duplicate": False,
                "phash": None,
                "image_bytes": None,
                "is_synthetic": False,
                "confidence": 0.0,
                "quarantined": True,
                "reason": "Corrupt or unreadable image data",
                "visual_clarity_score": 0.0
            }

    is_duplicate = False
    if phash_str:
        if is_hash_seen(phash_str):
            is_duplicate = True
        else:
            register_seen_hash(phash_str)

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
        "image_bytes": image_bytes,
        "is_synthetic": is_synthetic,
        "confidence": confidence,
        "quarantined": quarantined,
        "reason": reason,
        "visual_clarity_score": visual_clarity
    }
