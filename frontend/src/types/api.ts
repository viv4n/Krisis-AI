export type HazardType = "flood" | "structural_damage" | "blocked_road" | string;

export interface IncidentCluster {
  cluster_id: string;
  latitude: number;
  longitude: number;
  report_count: number;
  hazard_type: HazardType;
  priority_score: number;
  uncertainty_escalated: boolean;
  first_reported_at: string;
  last_reported_at: string;
}

export type RouteStatus = "blocked" | "passable" | "degraded" | string;

export interface RoutePassability {
  route_id: string;
  name: string;
  status: RouteStatus;
  severed_by_incident_id: string | null;
  coordinates: [number, number][]; // [longitude, latitude] pairs as per API contract
}

export interface SubmitReportPayload {
  image_base64?: string;
  text: string;
  latitude: number;
  longitude: number;
  source: "web" | "whatsapp" | "sms";
}

export interface SubmitReportResponse {
  status: "success" | "quarantined" | "escalated" | string;
  report_id: string;
  message: string;
}

