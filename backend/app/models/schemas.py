from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Valid literals from api_contract.json
SourceType = Literal["web", "whatsapp", "sms"]
ReportStatus = Literal["success", "quarantined", "escalated"]
HazardType = Literal["flood", "structural_damage", "blocked_road"]
RouteStatus = Literal["blocked", "passable", "degraded"]


class ReportCreateRequest(BaseModel):
    image_base64: Optional[str] = None
    text: str
    latitude: float
    longitude: float
    source: SourceType


class ReportCreateResponse(BaseModel):
    status: ReportStatus
    report_id: str
    message: str


class IncidentClusterResponse(BaseModel):
    cluster_id: str
    latitude: float
    longitude: float
    report_count: int
    hazard_type: HazardType
    priority_score: float
    uncertainty_escalated: bool
    first_reported_at: str
    last_reported_at: str


class RoutePassabilityResponse(BaseModel):
    route_id: str
    name: str
    status: RouteStatus
    severed_by_incident_id: Optional[str] = None
    coordinates: list[list[float]]  # GeoJSON style: [[lon, lat], [lon, lat], ...]

