import {
  IncidentCluster,
  RoutePassability,
  SubmitReportPayload,
  SubmitReportResponse,
} from "@/types/api";
import { MOCK_INCIDENTS, MOCK_ROUTES } from "./mockData";

const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BACKEND_BASE_URL = RAW_API_URL.replace(/\/+$/, "");

/**
 * Returns dynamic WebSocket URL from NEXT_PUBLIC_API_URL,
 * supporting https -> wss and http -> ws with fallback to localhost.
 */
function getWebSocketUrl(): string {
  if (BACKEND_BASE_URL.startsWith("https://")) {
    return BACKEND_BASE_URL.replace(/^https:\/\//, "wss://") + "/ws/incidents";
  }
  if (BACKEND_BASE_URL.startsWith("http://")) {
    return BACKEND_BASE_URL.replace(/^http:\/\//, "ws://") + "/ws/incidents";
  }
  return `ws://${BACKEND_BASE_URL}/ws/incidents`;
}

let activeMockIncidents: IncidentCluster[] = [...MOCK_INCIDENTS];

export interface FetchResult<T> {
  data: T;
  isFallback: boolean;
}

/**
 * Fetch incident clusters dynamically from backend, falling back to mock dataset only if backend unreachable
 */
export async function fetchIncidents(): Promise<FetchResult<IncidentCluster[]>> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    const res = await fetch(`${BACKEND_BASE_URL}/api/v1/incidents`, {
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data: IncidentCluster[] = await res.json();
    return { data, isFallback: false };
  } catch {
    return {
      data: [...activeMockIncidents],
      isFallback: true,
    };
  }
}

/**
 * Fetch route passability status dynamically from backend, falling back only if unreachable
 */
export async function fetchRoutePassability(): Promise<FetchResult<RoutePassability[]>> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    const res = await fetch(`${BACKEND_BASE_URL}/api/v1/routes/passability`, {
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data: RoutePassability[] = await res.json();
    return { data, isFallback: false };
  } catch {
    return {
      data: [...MOCK_ROUTES],
      isFallback: true,
    };
  }
}

/**
 * Submit citizen damage report to backend or realistic mock fallback
 */
export async function submitReport(
  payload: SubmitReportPayload
): Promise<{ response: SubmitReportResponse; isFallback: boolean }> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const res = await fetch(`${BACKEND_BASE_URL}/api/v1/report`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const response: SubmitReportResponse = await res.json();
    return { response, isFallback: false };
  } catch {
    const reportId = crypto.randomUUID();
    const isEscalated =
      payload.text.toLowerCase().includes("urgent") ||
      payload.text.toLowerCase().includes("trap") ||
      payload.text.toLowerCase().includes("help");

    const status: "success" | "quarantined" | "escalated" = isEscalated
      ? "escalated"
      : "success";

    const hazardGuess = payload.text.toLowerCase().includes("flood")
      ? "flood"
      : payload.text.toLowerCase().includes("road") || payload.text.toLowerCase().includes("block")
      ? "blocked_road"
      : "structural_damage";

    const newCluster: IncidentCluster = {
      cluster_id: reportId,
      latitude: payload.latitude,
      longitude: payload.longitude,
      report_count: 1,
      hazard_type: hazardGuess,
      priority_score: isEscalated ? 93.0 : 66.0,
      uncertainty_escalated: isEscalated,
      first_reported_at: new Date().toISOString(),
      last_reported_at: new Date().toISOString(),
    };

    activeMockIncidents = [newCluster, ...activeMockIncidents];

    const fallbackResponse: SubmitReportResponse = {
      status,
      report_id: reportId,
      message: isEscalated
        ? "Report ingested: Critical distress signals detected. Escalated for human review."
        : "Report ingested successfully into spatial consensus engine.",
    };

    return { response: fallbackResponse, isFallback: true };
  }
}

export type WebSocketIncidentPayload =
  | IncidentCluster[]
  | IncidentCluster
  | {
      type?: string;
      incident?: IncidentCluster;
      incidents?: IncidentCluster[];
      cluster_id?: string;
      priority_score?: number;
      [key: string]: unknown;
    };

/**
 * Connect to backend real-time WebSocket for live incident streaming.
 * Automatically reconnects with backoff if disconnected.
 */
export function subscribeToIncidents(
  onUpdate: (data: WebSocketIncidentPayload) => void
): () => void {
  const wsUrl = getWebSocketUrl();
  let socket: WebSocket | null = null;
  let isClosedManually = false;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

  function connect() {
    if (isClosedManually) return;
    try {
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        // Connected to real-time stream
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          onUpdate(payload);
        } catch (err) {
          console.error("WebSocket frame parsing error:", err);
        }
      };

      socket.onclose = () => {
        if (!isClosedManually) {
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };

      socket.onerror = () => {
        socket?.close();
      };
    } catch {
      if (!isClosedManually) {
        reconnectTimeout = setTimeout(connect, 5000);
      }
    }
  }

  connect();

  return () => {
    isClosedManually = true;
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    if (socket) socket.close();
  };
}
