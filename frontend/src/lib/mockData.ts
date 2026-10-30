import { IncidentCluster, RoutePassability } from "@/types/api";

// Default realistic disaster zone: Houston, TX Major Flood Grid
// Coordinates: Lat: 29.7604, Lng: -95.3698 (Buffalo Bayou / Downtown / Medical Center)
export const DEFAULT_DISASTER_COORDS = {
  lat: 29.7604,
  lng: -95.3698,
  city: "Houston, TX",
  zoneName: "Buffalo Bayou & Metro Medical Basin",
};

export const MOCK_INCIDENTS: IncidentCluster[] = [
  {
    cluster_id: "7d9b9a6c-9f8e-4a62-97b7-6bcfc9e2b101",
    latitude: 29.7604,
    longitude: -95.3698,
    report_count: 12,
    hazard_type: "flood",
    priority_score: 89.5,
    uncertainty_escalated: false,
    first_reported_at: "2026-10-30T13:20:00Z",
    last_reported_at: "2026-10-30T13:45:00Z",
  },
  {
    cluster_id: "c41f7e02-48a5-4f31-89e9-74d3999e0112",
    latitude: 29.7685,
    longitude: -95.3620,
    report_count: 19,
    hazard_type: "structural_damage",
    priority_score: 95.8,
    uncertainty_escalated: true,
    first_reported_at: "2026-10-30T12:50:00Z",
    last_reported_at: "2026-10-30T14:10:00Z",
  },
  {
    cluster_id: "b21a8123-5e92-4114-8f77-ee8d90471f45",
    latitude: 29.7520,
    longitude: -95.3780,
    report_count: 7,
    hazard_type: "blocked_road",
    priority_score: 68.2,
    uncertainty_escalated: false,
    first_reported_at: "2026-10-30T13:05:00Z",
    last_reported_at: "2026-10-30T13:30:00Z",
  },
  {
    cluster_id: "e5033a10-23bb-4de9-9e8c-87d219488a99",
    latitude: 29.7710,
    longitude: -95.3850,
    report_count: 4,
    hazard_type: "flood",
    priority_score: 54.0,
    uncertainty_escalated: false,
    first_reported_at: "2026-10-30T13:40:00Z",
    last_reported_at: "2026-10-30T14:00:00Z",
  },
  {
    cluster_id: "f882190c-03c4-42b7-a3e9-a41e974e6371",
    latitude: 29.7450,
    longitude: -95.3610,
    report_count: 3,
    hazard_type: "blocked_road",
    priority_score: 36.5,
    uncertainty_escalated: false,
    first_reported_at: "2026-10-30T14:02:00Z",
    last_reported_at: "2026-10-30T14:15:00Z",
  },
  {
    cluster_id: "a190ef22-771c-43be-82a1-cc0981923db8",
    latitude: 29.7390,
    longitude: -95.3750,
    report_count: 1,
    hazard_type: "structural_damage",
    priority_score: 21.0,
    uncertainty_escalated: false,
    first_reported_at: "2026-10-30T14:12:00Z",
    last_reported_at: "2026-10-30T14:12:00Z",
  },
];

export const MOCK_ROUTES: RoutePassability[] = [
  {
    route_id: "road_seg_i45_north",
    name: "I-45 Northbound Emergency Corridor",
    status: "blocked",
    severed_by_incident_id: "c41f7e02-48a5-4f31-89e9-74d3999e0112",
    coordinates: [
      [-95.3620, 29.7685],
      [-95.3650, 29.7730],
      [-95.3680, 29.7780],
    ],
  },
  {
    route_id: "road_seg_buffalo_bayou",
    name: "Memorial Drive Parkway",
    status: "blocked",
    severed_by_incident_id: "7d9b9a6c-9f8e-4a62-97b7-6bcfc9e2b101",
    coordinates: [
      [-95.3850, 29.7620],
      [-95.3750, 29.7610],
      [-95.3698, 29.7604],
    ],
  },
  {
    route_id: "road_seg_med_center",
    name: "Main St / Texas Medical Center Access",
    status: "passable",
    severed_by_incident_id: null,
    coordinates: [
      [-95.3780, 29.7520],
      [-95.3820, 29.7420],
      [-95.3860, 29.7350],
      [-95.3900, 29.7280],
    ],
  },
  {
    route_id: "road_seg_i10_west",
    name: "I-10 West Evacuation Trunk",
    status: "passable",
    severed_by_incident_id: null,
    coordinates: [
      [-95.3500, 29.7720],
      [-95.3650, 29.7735],
      [-95.3850, 29.7750],
      [-95.4050, 29.7760],
    ],
  },
  {
    route_id: "road_seg_louisiana_st",
    name: "Louisiana St Downtown Feed",
    status: "degraded",
    severed_by_incident_id: "b21a8123-5e92-4114-8f77-ee8d90471f45",
    coordinates: [
      [-95.3660, 29.7570],
      [-95.3710, 29.7545],
      [-95.3780, 29.7520],
    ],
  },
];
