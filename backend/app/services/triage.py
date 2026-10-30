import re
import uuid
import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional, Literal
from app.core.config import settings
from app.services.geospatial import haversine_distance_meters, point_to_polyline_distance_meters
from app.models.schemas import HazardType, RouteStatus

# In-memory or local SQLite DB file
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "krisis_store.db")

URGENT_TOKENS = ["trapped", "fire", "emergency", "blocked", "help", "collapse"]

# Pre-configured arterial road segments (including hospital arterial roads)
# Coordinates format: [[lon, lat], [lon, lat]]
PRECONFIGURED_ROUTES = [
    {
        "route_id": "road_seg_104",
        "name": "Main Hospital Arterial Road",
        "coordinates": [[77.4421, 12.6580], [77.4435, 12.6592], [77.4450, 12.6605]]
    },
    {
        "route_id": "road_seg_105",
        "name": "North Transit Emergency Corridor",
        "coordinates": [[77.4380, 12.6620], [77.4400, 12.6650]]
    },
    {
        "route_id": "road_seg_106",
        "name": "South Bypass Access Route",
        "coordinates": [[77.4410, 12.6510], [77.4440, 12.6530]]
    }
]

# Critical infrastructure locations: [name, lat, lon]
CRITICAL_INFRASTRUCTURE = [
    {"name": "District General Hospital", "lat": 12.6590, "lon": 77.4430},
    {"name": "Central Fire Station", "lat": 12.6560, "lon": 77.4410},
    {"name": "Emergency Relief Depot", "lat": 12.6610, "lon": 77.4460}
]


def init_db():
    """Initialize SQLite tables for incident clusters and individual reports."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clusters (
            cluster_id TEXT PRIMARY KEY,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            report_count INTEGER NOT NULL,
            hazard_type TEXT NOT NULL,
            priority_score REAL NOT NULL,
            uncertainty_escalated INTEGER NOT NULL,
            first_reported_at TEXT NOT NULL,
            last_reported_at TEXT NOT NULL,
            sum_visual_damage REAL NOT NULL,
            sum_nlp_urgency REAL NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            cluster_id TEXT,
            text TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            priority_score REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


def classify_hazard(text: str) -> HazardType:
    """Classify hazard type based on keyword tokens."""
    t = text.lower()
    if any(k in t for k in ["flood", "water", "drown", "submerged", "overflow", "river"]):
        return "flood"
    if any(k in t for k in ["road", "blocked", "traffic", "landslide", "tree fell", "obstruction", "passage"]):
        return "blocked_road"
    return "structural_damage"


def calculate_nlp_urgency(text: str) -> float:
    """Calculates NLP urgency score from 0.0 to 100.0."""
    t = text.lower()
    urgent_matches = sum(1 for token in URGENT_TOKENS if re.search(rf"\b{token}\b", t))
    base = 30.0
    score = base + (urgent_matches * 20.0)
    # Exclamation marks or caps
    if "!" in text or text.isupper():
        score += 10.0
    return min(100.0, score)


def calculate_visual_damage(has_image: bool, visual_clarity: float, text: str) -> float:
    """
    Computes visual damage indicator from 0.0 to 100.0.
    In production this interfaces with Vision-LLM or computer vision models.
    """
    if not has_image:
        return 40.0  # text-only median assessment
    
    # Assess severity from text correlation and image quality
    t = text.lower()
    severity = 50.0
    if any(w in t for w in ["destroyed", "collapsed", "fire", "heavy", "severe", "crushed"]):
        severity += 35.0
    elif any(w in t for w in ["crack", "leak", "minor", "small"]):
        severity -= 15.0
    return min(100.0, max(10.0, severity * visual_clarity))


def calculate_infrastructure_proximity_score(lat: float, lon: float) -> float:
    """
    Calculate proximity score (0 to 100) based on distance to critical infrastructure.
    Closer to hospital/fire station = higher score.
    """
    min_dist = float("inf")
    for infra in CRITICAL_INFRASTRUCTURE:
        d = haversine_distance_meters(lat, lon, infra["lat"], infra["lon"])
        if d < min_dist:
            min_dist = d

    # Also check proximity to hospital arterial routes
    for r in PRECONFIGURED_ROUTES:
        d_route = point_to_polyline_distance_meters(lat, lon, r["coordinates"])
        if d_route < min_dist:
            min_dist = d_route

    # Distance mapping: <= 50m -> 100, 500m -> 50, >= 2000m -> 10
    if min_dist <= 50.0:
        return 100.0
    elif min_dist <= 500.0:
        return 100.0 - ((min_dist - 50.0) / 450.0) * 50.0
    elif min_dist <= 2000.0:
        return 50.0 - ((min_dist - 500.0) / 1500.0) * 40.0
    else:
        return 10.0


def calculate_priority_score(
    visual_damage: float,
    nlp_urgency: float,
    infra_proximity: float
) -> float:
    """
    Scoring algorithm:
    priority_score = (visual_damage * 0.4) + (nlp_urgency * 0.3) + (infrastructure_proximity * 0.3)
    normalized to 0-100.
    """
    score = (visual_damage * 0.4) + (nlp_urgency * 0.3) + (infra_proximity * 0.3)
    return round(min(100.0, max(0.0, score)), 2)


def check_uncertainty_escalation(
    has_image: bool,
    visual_confidence: float,
    text: str
) -> bool:
    """
    Uncertainty Escalation:
    If visual confidence < VISUAL_CONFIDENCE_THRESHOLD (0.50)
    but text contains urgent tokens (["trapped", "fire", "emergency", "blocked", "help", "collapse"]),
    explicitly set uncertainty_escalated = True.
    """
    t = text.lower()
    has_urgent_token = any(token in t for token in URGENT_TOKENS)
    is_low_visual_confidence = (not has_image) or (visual_confidence < settings.VISUAL_CONFIDENCE_THRESHOLD)

    return bool(is_low_visual_confidence and has_urgent_token)


def merge_or_create_cluster(
    lat: float,
    lon: float,
    hazard_type: HazardType,
    priority_score: float,
    uncertainty_escalated: bool,
    now_iso: str
) -> tuple[str, bool]:
    """
    Finds if an existing cluster is within SPATIAL_CLUSTER_RADIUS_METERS (50m).
    If yes, merges into that cluster and increments report_count.
    Otherwise, creates a new cluster.
    Returns (cluster_id, was_merged).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT cluster_id, latitude, longitude, report_count, priority_score, uncertainty_escalated, first_reported_at FROM clusters")
    clusters = cursor.fetchall()

    target_cluster = None
    for c_id, c_lat, c_lon, count, p_score, u_esc, f_time in clusters:
        dist = haversine_distance_meters(lat, lon, c_lat, c_lon)
        if dist <= settings.SPATIAL_CLUSTER_RADIUS_METERS:
            target_cluster = (c_id, c_lat, c_lon, count, p_score, u_esc, f_time)
            break

    if target_cluster:
        c_id, c_lat, c_lon, count, old_score, old_esc, f_time = target_cluster
        new_count = count + 1
        # Rolling weighted priority score update (highest urgency weighted)
        updated_score = round(max(old_score, (old_score * count + priority_score) / new_count), 2)
        combined_escalated = int(bool(old_esc or uncertainty_escalated))
        
        cursor.execute("""
            UPDATE clusters
            SET report_count = ?, priority_score = ?, uncertainty_escalated = ?, last_reported_at = ?
            WHERE cluster_id = ?
        """, (new_count, updated_score, combined_escalated, now_iso, c_id))
        conn.commit()
        conn.close()
        return c_id, True
    else:
        new_cluster_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO clusters (
                cluster_id, latitude, longitude, report_count, hazard_type,
                priority_score, uncertainty_escalated, first_reported_at, last_reported_at,
                sum_visual_damage, sum_nlp_urgency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_cluster_id, lat, lon, 1, hazard_type,
            priority_score, int(uncertainty_escalated), now_iso, now_iso,
            0.0, 0.0
        ))
        conn.commit()
        conn.close()
        return new_cluster_id, False


def get_all_clusters() -> list[dict]:
    """Return all active clusters sorted by priority_score descending."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cluster_id, latitude, longitude, report_count, hazard_type,
               priority_score, uncertainty_escalated, first_reported_at, last_reported_at
        FROM clusters
        ORDER BY priority_score DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "cluster_id": r[0],
            "latitude": r[1],
            "longitude": r[2],
            "report_count": r[3],
            "hazard_type": r[4],
            "priority_score": float(r[5]),
            "uncertainty_escalated": bool(r[6]),
            "first_reported_at": r[7],
            "last_reported_at": r[8]
        })
    return results


def get_route_passabilities() -> list[dict]:
    """
    Returns pre-configured road segments with dynamic blocked/passable/degraded status
    based on active clusters within proximity of each route.
    """
    clusters = get_all_clusters()
    routes = []

    for route in PRECONFIGURED_ROUTES:
        route_coords = route["coordinates"]
        severed_by = None
        status: RouteStatus = "passable"

        for cl in clusters:
            dist = point_to_polyline_distance_meters(cl["latitude"], cl["longitude"], route_coords)
            # If high severity incident or blocked_road within 40 meters, route is blocked
            if dist <= 40.0:
                if cl["hazard_type"] == "blocked_road" or cl["priority_score"] >= 70.0:
                    status = "blocked"
                    severed_by = cl["cluster_id"]
                    break
                elif cl["priority_score"] >= 40.0:
                    status = "degraded"
                    severed_by = cl["cluster_id"]
            elif dist <= 80.0 and status == "passable" and cl["priority_score"] >= 80.0:
                status = "degraded"
                severed_by = cl["cluster_id"]

        routes.append({
            "route_id": route["route_id"],
            "name": route["name"],
            "status": status,
            "severed_by_incident_id": severed_by,
            "coordinates": route_coords
        })

    return routes

