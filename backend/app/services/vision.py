import io
import logging
from typing import Optional

logger = logging.getLogger("krisis.vision")

try:
    from PIL import Image
except ImportError:
    Image = None

# Lazy-loaded Ultralytics YOLO model instance
_yolo_model = None


def get_yolo_model():
    """Lazy loader for YOLOv8n to save startup time and memory."""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # Load lightweight YOLOv8 Nano model
            _yolo_model = YOLO("yolov8n.pt")
            logger.info("YOLOv8n model loaded successfully for vision inference.")
        except Exception as e:
            logger.warning(f"Could not initialize Ultralytics YOLOv8n: {e}. Using heuristic fallback.")
            _yolo_model = False
    return _yolo_model


def assess_damage(image_bytes: Optional[bytes]) -> tuple[float, float]:
    """
    Assess visual damage using Ultralytics YOLOv8 (yolov8n.pt) or robust heuristic fallback.
    
    Returns:
        (visual_damage, confidence)
        visual_damage: float between 0.0 and 1.0 (indicating destruction/obstruction severity)
        confidence: float between 0.0 and 1.0 (mean detection or model confidence)
    """
    if not image_bytes:
        return 0.40, 0.0

    pil_img = None
    if Image is not None:
        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            logger.error(f"Failed to decode image bytes: {e}")
            return 0.30, 0.10

    model = get_yolo_model()
    if model and pil_img is not None:
        try:
            # Run inference on PIL Image with nano model (CPU mode)
            results = model(pil_img, verbose=False)
            if results and len(results) > 0:
                result = results[0]
                boxes = result.boxes
                if boxes is not None and len(boxes) > 0:
                    confidences = [float(c) for c in boxes.conf.cpu().numpy()]
                    class_ids = [int(cls) for cls in boxes.cls.cpu().numpy()]
                    class_names = [result.names.get(cid, "") for cid in class_ids]
                    
                    mean_conf = sum(confidences) / len(confidences)
                    
                    # Hazard/obstruction relevant classes in COCO:
                    # car, motorcycle, bus, truck, boat, stop sign, fire hydrant, person
                    hazard_keywords = {"car", "truck", "bus", "boat", "fire hydrant", "motorcycle", "train"}
                    has_vehicle_hazard = any(name in hazard_keywords for name in class_names)
                    
                    # Compute damage score based on detected density and objects
                    # High density of objects/clutter or boats on roads typically indicates flooding/debris
                    box_count_factor = min(0.5, len(boxes) * 0.08)
                    base_damage = 0.50 + box_count_factor
                    if any(name == "boat" for name in class_names):
                        base_damage = max(base_damage, 0.85)
                    elif has_vehicle_hazard:
                        base_damage = max(base_damage, 0.65)
                    
                    visual_damage = min(1.0, max(0.1, base_damage))
                    return round(visual_damage, 2), round(mean_conf, 2)
                else:
                    # No recognizable objects detected (e.g. rubble, murky flood water, darkness)
                    return 0.50, 0.35
        except Exception as e:
            logger.warning(f"YOLO inference error: {e}. Falling back to image heuristics.")

    # Robust Heuristic Fallback based on pixel variance/contrast
    if pil_img is not None:
        try:
            from PIL import ImageStat
            stat = ImageStat.Stat(pil_img.convert("L"))
            mean_brightness = stat.mean[0]
            stddev = stat.stddev[0]
            # Dark/blurry indicates uncertain image
            if mean_brightness < 40 or stddev < 18:
                return 0.45, 0.30  # Low visual confidence
            return 0.60, 0.70
        except Exception:
            pass

    return 0.50, 0.50

