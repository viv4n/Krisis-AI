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

# AI Safety Net spam/promotional patterns
SPAM_PATTERNS = [
    r"\b(buy now|discount|promo code|special offer|free crypto|bitcoin|ethereum|casino|viagra|lottery|earn money|subscribe to)\b",
    r"\b(click here|limited time offer|congratulations you won|cash prize|work from home|weight loss)\b",
]

NON_EMERGENCY_CHITCHAT = [
    r"^(hi|hello|hey|test|testing|yo|sup|good morning|good evening|good night|how are you|what's up|who is this|who are you)\b",
]

HAZARD_DISTRESS_KEYWORDS = [
    "flood", "water", "drown", "fire", "smoke", "burn", "collapse",
    "trapped", "help", "emergency", "blocked", "road", "tree", "damage",
    "injured", "hospital", "ambulance", "rescue", "hazard", "leak", "crush"
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
            phash TEXT,
            created_at TEXT NOT NULL
        )
    """)
    # Automatic migration: ensure phash column exists on older tables
    try:
        cursor.execute("ALTER TABLE reports ADD COLUMN phash TEXT;")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


init_db()


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Computes Hamming distance between two hex-encoded perceptual hashes.
    Each hex char represents 4 bits. Typical 16-hex hash is 64 bits.
    """
    if not hash1 or not hash2:
        return 64
    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        xor_result = val1 ^ val2
        return bin(xor_result).count("1")
    except (ValueError, TypeError):
        dist = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        dist += abs(len(hash1) - len(hash2))
        return dist


def find_duplicate_by_phash(phash: Optional[str], threshold: int = 5) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Query the database for recent reports with a phash.
    If the Hamming distance is less than threshold (e.g., 5),
    flags it as a duplicate and returns (is_duplicate, matched_report_id, matched_cluster_id).
    """
    if not phash:
        return False, None, None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT report_id, cluster_id, phash
        FROM reports
        WHERE phash IS NOT NULL AND phash != '' AND cluster_id IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 100
    """)
    rows = cursor.fetchall()
    conn.close()

    for r_id, c_id, stored_hash in rows:
        dist = hamming_distance(phash, stored_hash)
        if dist < threshold:
            return True, r_id, c_id

    return False, None, None


def check_ai_safety_net_spam(text: str) -> tuple[bool, str]:
    """
    Validation layer before heavy ML inference:
    Detects obvious non-emergency spam, commercial promotions, or pure chit-chat
    that contains no emergency distress or hazard tokens.
    """
    if not text or not text.strip():
        return True, "Empty text content"

    t = text.lower().strip()

    # Check for commercial / promotional spam patterns
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, t):
            return True, "Commercial or promotional spam detected"

    # Check for conversational chit-chat / test phrases without hazard words
    is_chitchat = any(re.search(p, t) for p in NON_EMERGENCY_CHITCHAT)
    if is_chitchat:
        has_hazard = any(h in t for h in HAZARD_DISTRESS_KEYWORDS)
        if not has_hazard:
            return True, "Non-emergency conversational noise / test text"

    # Extreme repetition / keyboard mash (e.g. "asdfasdfasdf" or "aaaaaaa")
    if len(t) > 6 and len(set(t.replace(" ", ""))) <= 2:
        return True, "Gibberish or repetitive character spam"

    return False, ""


def classify_hazard(text: str) -> HazardType:
    """Classify hazard type based on keyword tokens."""
    t = text.lower()
    if any(k in t for k in ["flood", "water", "drown", "submerged", "overflow", "river", "bayou"]):
        return "flood"
    if any(k in t for k in ["road", "blocked", "traffic", "landslide", "tree fell", "obstruction", "passage", "highway", "bridge"]):
        return "blocked_road"
    return "structural_damage"


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
    v_norm = visual_damage * 100.0 if visual_damage <= 1.0 else visual_damage
    n_norm = nlp_urgency * 100.0 if nlp_urgency <= 1.0 else nlp_urgency
    i_norm = infra_proximity

    score = (v_norm * 0.4) + (n_norm * 0.3) + (i_norm * 0.3)
    return round(min(100.0, max(0.0, score)), 2)


def check_uncertainty_escalation(
    has_image: bool,
    visual_confidence: float,
    text: str,
    nlp_urgency: float = 0.5,
    contains_critical: bool = False
) -> bool:
    """
    Uncertainty Escalation:
    If visual confidence < VISUAL_CONFIDENCE_THRESHOLD (0.50)
    and NLP urgency is high (urgency >= 0.65 or contains critical keywords),
    explicitly set uncertainty_escalated = True.
    """
    is_low_visual_conf = (not has_image) or (visual_confidence < settings.VISUAL_CONFIDENCE_THRESHOLD)
    t = text.lower()
    has_urgent_token = contains_critical or any(token in t for token in URGENT_TOKENS)
    is_high_nlp = has_urgent_token or (nlp_urgency >= 0.65)

    return bool(is_low_visual_conf and is_high_nlp)


def merge_into_existing_cluster(
    cluster_id: str,
    priority_score: float,
    uncertainty_escalated: bool,
    now_iso: str
) -> bool:
    """
    Directly increments report_count and updates priority_score, uncertainty_escalated,
    and last_reported_at for an existing cluster_id (e.g. from pHash deduplication).
    Returns True if cluster was found and updated, False otherwise.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT report_count, priority_score, uncertainty_escalated
        FROM clusters
        WHERE cluster_id = ?
    """, (cluster_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    old_count, old_score, old_esc = row
    new_count = old_count + 1
    updated_score = round(max(old_score, (old_score * old_count + priority_score) / new_count), 2)
    combined_esc = int(bool(old_esc or uncertainty_escalated))

    cursor.execute("""
        UPDATE clusters
        SET report_count = ?, priority_score = ?, uncertainty_escalated = ?, last_reported_at = ?
        WHERE cluster_id = ?
    """, (new_count, updated_score, combined_esc, now_iso, cluster_id))
    conn.commit()
    conn.close()
    return True


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
    cursor.execute("""
        SELECT cluster_id, latitude, longitude, report_count, priority_score, uncertainty_escalated, first_reported_at
        FROM clusters
    """)
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


def get_cluster_by_id(cluster_id: str) -> Optional[dict]:
    """Retrieve an active cluster dict by its cluster_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cluster_id, latitude, longitude, report_count, hazard_type,
               priority_score, uncertainty_escalated, first_reported_at, last_reported_at
        FROM clusters
        WHERE cluster_id = ?
    """, (cluster_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "cluster_id": row[0],
        "latitude": row[1],
        "longitude": row[2],
        "report_count": row[3],
        "hazard_type": row[4],
        "priority_score": float(row[5]),
        "uncertainty_escalated": bool(row[6]),
        "first_reported_at": row[7],
        "last_reported_at": row[8]
    }


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
            if dist <= 40.0:
                if cl["hazard_type"] == "blocked_road" or cl["priority_score"] >= 70.0:
                    status = "blocked"
                    severed_by = cl["cluster_id"]
                    break
                elif cl["priority_score"] >= 40.0:
                    status = "degraded"
                    severed_by = cl["cluster_id"]
            elif dist <= settings.ROUTE_PROXIMITY_THRESHOLD_METERS and status == "passable" and cl["priority_score"] >= 80.0:
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
