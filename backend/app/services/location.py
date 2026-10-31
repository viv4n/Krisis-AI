import logging
import random
import re
from typing import Optional

logger = logging.getLogger("krisis.location")

# Houston base reference coordinates for frontend tactical map viewport
HOUSTON_BASE_LAT = 29.7604
HOUSTON_BASE_LNG = -95.3698

# Local dictionary for Houston disaster response landmarks
HOUSTON_LANDMARKS = [
    (r"\b(main(\s+st|\s+street)?)\b", 29.7558, -95.3683),
    (r"\b(fannin(\s+st|\s+street)?)\b", 29.7402, -95.3789),
    (r"\b(buffalo\s+bayou)\b", 29.7645, -95.3625),
    (r"\b(i-?10|interstate\s+10|katy\s+fwy)\b", 29.7750, -95.4000),
    (r"\b(i-?45|gulf\s+fwy)\b", 29.7400, -95.3600),
    (r"\b(memorial(\s+dr|\s+drive)?)\b", 29.7610, -95.3900),
    (r"\b(post\s+oak)\b", 29.7450, -95.4600),
    (r"\b(heights(\s+blvd)?)\b", 29.7800, -95.3980),
    (r"\b(montrose)\b", 29.7430, -95.3920),
    (r"\b(hospital|medical\s+center|med\s+center|tmc)\b", 29.7100, -95.3970),
    (r"\b(downtown)\b", 29.7604, -95.3698),
]

_geolocator = None


def get_geolocator():
    """Lazy loader for geopy Nominatim geocoder."""
    global _geolocator
    if _geolocator is None:
        try:
            from geopy.geocoders import Nominatim
            _geolocator = Nominatim(user_agent="krisis_ai_emergency_response_mapper", timeout=4)
        except Exception as e:
            logger.warning(f"Could not initialize geopy Nominatim: {e}")
            _geolocator = False
    return _geolocator


def get_houston_fallback_coordinates() -> tuple[float, float]:
    """
    CRITICAL HOUSTON FALLBACK:
    Assign randomized coordinates within Houston, Texas:
    Base Lat: 29.7604, Base Lng: -95.3698, apply random offset between -0.02 and +0.02.
    Guaranteed to NEVER return null.
    """
    lat_offset = random.uniform(-0.02, 0.02)
    lng_offset = random.uniform(-0.02, 0.02)
    lat = round(HOUSTON_BASE_LAT + lat_offset, 6)
    lng = round(HOUSTON_BASE_LNG + lng_offset, 6)
    return lat, lng


def extract_explicit_coordinates(text: Optional[str]) -> Optional[tuple[float, float]]:
    """
    Regex parser to find explicitly typed coordinates in incoming captions/messages:
    - Key-value: "lat: 29.76, lng: -95.36" or "latitude=29.76, longitude=-95.36"
    - Formats like: "29.76, -95.36", "(29.76, -95.36)", "[29.76, -95.36]"
    """
    if not text:
        return None

    # Key-value labeled formats (lat: ..., lng/lon: ...)
    kv_match = re.search(
        r"(?:lat(?:itude)?)\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)[,\s]+(?:lon(?:gitude)?|lng)\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )
    if kv_match:
        try:
            lat = float(kv_match.group(1))
            lng = float(kv_match.group(2))
            if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                logger.info(f"Explicit key-value coordinates found: ({lat}, {lng})")
                return round(lat, 6), round(lng, 6)
        except ValueError:
            pass

    # Reverse key-value (lng: ..., lat: ...)
    rev_kv_match = re.search(
        r"(?:lon(?:gitude)?|lng)\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)[,\s]+(?:lat(?:itude)?)\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )
    if rev_kv_match:
        try:
            lng = float(rev_kv_match.group(1))
            lat = float(rev_kv_match.group(2))
            if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                logger.info(f"Explicit reverse key-value coordinates found: ({lat}, {lng})")
                return round(lat, 6), round(lng, 6)
        except ValueError:
            pass

    # Standard comma-separated pair (e.g. 29.7604, -95.3698)
    pair_match = re.search(
        r"[\[\(]?\s*([+-]?\d{1,2}(?:\.\d+)?)\s*,\s*([+-]?\d{1,3}(?:\.\d+)?)\s*[\]\)]?",
        text
    )
    if pair_match:
        try:
            lat = float(pair_match.group(1))
            lng = float(pair_match.group(2))
            if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                logger.info(f"Explicit pair coordinates found: ({lat}, {lng})")
                return round(lat, 6), round(lng, 6)
        except ValueError:
            pass

    return None


def extract_location_from_text(text: Optional[str]) -> tuple[float, float]:
    """
    Bulletproof GPS Extractor for Telegram captions and SMS:
    1. Check for explicitly typed coordinates via regex (e.g. '29.76, -95.36' or 'lat: 29.76, lng: -95.36').
    2. Check local Houston landmark patterns.
    3. Try geopy Nominatim lookup.
    4. CRITICAL HOUSTON FALLBACK: Houston Base Lat: 29.7604, Base Lng: -95.3698 with random offset (-0.02 to +0.02).
       NEVER returns null coordinates.
    """
    if not text or not text.strip():
        return get_houston_fallback_coordinates()

    # 1. Regex check for explicit coordinates
    explicit_coords = extract_explicit_coordinates(text)
    if explicit_coords is not None:
        return explicit_coords

    t_lower = text.lower().strip()

    # 2. Local Houston landmark matching
    for pattern, lat, lng in HOUSTON_LANDMARKS:
        if re.search(pattern, t_lower):
            logger.info(f"Houston landmark pattern '{pattern}' matched -> ({lat}, {lng})")
            return lat, lng

    # 3. Geopy Nominatim geocoding
    geolocator = get_geolocator()
    if geolocator:
        try:
            # Look for location phrases after in/at/near/on or pass snippet
            snippets = []
            phrases = re.findall(r"\b(?:in|at|near|on)\s+([A-Za-z0-9\s,\.-]+)", text, re.IGNORECASE)
            for phrase in phrases:
                cleaned = phrase.strip().rstrip(".,;!")
                if cleaned and len(cleaned) > 2:
                    snippets.append(cleaned)
                    if "houston" not in cleaned.lower():
                        snippets.append(f"{cleaned}, Houston, Texas")

            snippets.append(text[:100])
            for q in snippets:
                loc = geolocator.geocode(q)
                if loc and loc.latitude and loc.longitude:
                    logger.info(f"Nominatim resolved '{q}' -> ({loc.latitude}, {loc.longitude})")
                    return round(float(loc.latitude), 6), round(float(loc.longitude), 6)
        except Exception as e:
            logger.warning(f"Nominatim geocode failed: {e}")

    # 4. Critical Houston Fallback
    fallback_lat, fallback_lng = get_houston_fallback_coordinates()
    logger.info(f"Applying guaranteed Houston random offset fallback: ({fallback_lat}, {fallback_lng})")
    return fallback_lat, fallback_lng
