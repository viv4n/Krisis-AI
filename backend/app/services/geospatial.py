import math
from typing import Optional

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth
    in meters using the Haversine formula.
    """
    R = 6371000.0  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    
    # Avoid domain errors due to floating-point rounding
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def point_to_segment_distance_meters(
    plat: float, plon: float,
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    Compute shortest distance in meters from a point (plat, plon) to a line segment (lat1, lon1)-(lat2, lon2).
    Uses projection in local equidistant approximation.
    """
    # Sample intermediate steps along segment for accurate Haversine representation
    steps = 10
    min_dist = float("inf")
    for step in range(steps + 1):
        ratio = step / steps
        inter_lat = lat1 + (lat2 - lat1) * ratio
        inter_lon = lon1 + (lon2 - lon1) * ratio
        dist = haversine_distance_meters(plat, plon, inter_lat, inter_lon)
        if dist < min_dist:
            min_dist = dist
    return min_dist


def point_to_polyline_distance_meters(
    plat: float, plon: float,
    coordinates: list[list[float]]  # GeoJSON: [[lon, lat], [lon, lat], ...]
) -> float:
    """
    Calculate distance from point (plat, plon) to a GeoJSON polyline.
    """
    if not coordinates:
        return float("inf")
    if len(coordinates) == 1:
        return haversine_distance_meters(plat, plon, coordinates[0][1], coordinates[0][0])

    min_dist = float("inf")
    for i in range(len(coordinates) - 1):
        lon1, lat1 = coordinates[i]
        lon2, lat2 = coordinates[i + 1]
        dist = point_to_segment_distance_meters(plat, plon, lat1, lon1, lat2, lon2)
        if dist < min_dist:
            min_dist = dist
    return min_dist

