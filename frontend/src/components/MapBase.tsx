"use client";

import React, { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import { IncidentCluster, RoutePassability } from "@/types/api";
import { useAppTheme } from "@/components/ThemeProvider";

export interface MapBaseProps {
  incidents: IncidentCluster[];
  routes: RoutePassability[];
  selectedClusterId: string | null;
  onSelectCluster: (clusterId: string) => void;
  onLocationSelect?: (lat: number, lng: number) => void;
}

const HOUSTON_CENTER: [number, number] = [29.7604, -95.3698];

function MapController({
  selectedCluster,
}: {
  selectedCluster: IncidentCluster | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (selectedCluster) {
      map.flyTo([selectedCluster.latitude, selectedCluster.longitude], 15, {
        duration: 1.0,
      });
    }
  }, [selectedCluster, map]);

  return null;
}

function MapClickListener({
  onLocationSelect,
}: {
  onLocationSelect?: (lat: number, lng: number) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (!onLocationSelect) return;
    const handleClick = (e: L.LeafletMouseEvent) => {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    };
    map.on("click", handleClick);
    return () => {
      map.off("click", handleClick);
    };
  }, [map, onLocationSelect]);

  return null;
}

function createClusterIcon(
  incident: IncidentCluster,
  isSelected: boolean,
  palette: string
): L.DivIcon {
  const priority = incident.priority_score;
  const isHigh = priority > 75;
  const isMed = priority >= 40 && priority <= 75;
  const isEscalated = incident.uncertainty_escalated;

  let bg = "#38BDF8";
  const fg = "#090B10";
  let border = "#0284C7";

  if (palette === "cyber-neon") {
    bg = isHigh ? "#F43F5E" : isMed ? "#FB923C" : "#38BDF8";
    border = isHigh ? "#BE123C" : isMed ? "#EA580C" : "#0284C7";
  } else if (palette === "emerald-grid") {
    bg = isHigh ? "#F43F5E" : isMed ? "#F59E0B" : "#10B981";
    border = isHigh ? "#BE123C" : isMed ? "#D97706" : "#059669";
  } else if (palette === "monochrome") {
    bg = isHigh ? "#EF4444" : isMed ? "#F59E0B" : "#D97706";
    border = isHigh ? "#B91C1C" : isMed ? "#B45309" : "#92400E";
  }

  const pulse = isHigh
    ? `<span class="absolute inline-flex h-10 w-10 rounded-full animate-ping opacity-60" style="background-color: ${bg}"></span>`
    : "";

  const selectedRing = isSelected
    ? `box-shadow: 0 0 0 3px #FFFFFF, 0 0 0 6px ${bg}; transform: scale(1.18);`
    : "";

  const html = `
    <div class="relative flex items-center justify-center transition-all duration-200" style="${selectedRing}">
      ${pulse}
      <div class="relative flex items-center justify-center w-8 h-8 rounded-full font-mono font-black text-xs shadow-xl" style="background-color: ${bg}; color: ${fg}; border: 2px solid ${border};">
        <span>${Math.round(incident.priority_score)}</span>
      </div>
      ${
        isEscalated
          ? `<span class="absolute -top-1 -right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-red-600 text-[9px] font-black text-white border border-white">!</span>`
          : ""
      }
    </div>
  `;

  return L.divIcon({
    html,
    className: "cluster-pin",
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });
}

export default function MapBase({
  incidents,
  routes,
  selectedClusterId,
  onSelectCluster,
  onLocationSelect,
}: MapBaseProps) {
  const selectedCluster =
    incidents.find((inc) => inc.cluster_id === selectedClusterId) || null;

  const { palette } = useAppTheme();

  return (
    <div className="relative w-full h-full min-h-[550px] overflow-hidden select-none">
      <MapContainer
        center={HOUSTON_CENTER}
        zoom={13}
        zoomControl={false}
        className="w-full h-full"
      >
        {/* OpenStreetMap 100% Free Public Tiles - Never Requires an API Key */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <MapController selectedCluster={selectedCluster} />
        <MapClickListener onLocationSelect={onLocationSelect} />

        {/* Route Passability Overlays */}
        {routes.map((route) => {
          const latLngCoords: [number, number][] = route.coordinates.map(
            (c) => [c[1], c[0]]
          );

          const isBlocked = route.status === "blocked";
          const isPassable = route.status === "passable";

          let strokeColor = "#10B981";
          if (isBlocked) {
            strokeColor = "#F43F5E";
          } else if (!isPassable) {
            strokeColor = "#F59E0B";
          }

          return (
            <Polyline
              key={route.route_id}
              positions={latLngCoords}
              pathOptions={{
                color: strokeColor,
                weight: isBlocked ? 6 : 5,
                opacity: 0.9,
                dashArray: isBlocked ? "6, 8" : undefined,
                lineCap: "round",
                lineJoin: "round",
              }}
            >
              <Popup className="tactical-popup">
                <div className="p-3 text-xs min-w-[210px] tactical-card">
                  <div className="text-[10px] uppercase font-mono tracking-wider text-matrix-muted">
                    {route.route_id}
                  </div>
                  <div className="font-semibold text-matrix-text mt-0.5 text-sm">
                    {route.name}
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-matrix-muted font-mono">Passability:</span>
                    <span
                      className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded ${
                        isBlocked
                          ? "bg-red-500/20 text-red-400 border border-red-500/40"
                          : isPassable
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                          : "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                      }`}
                    >
                      {route.status}
                    </span>
                  </div>
                  {route.severed_by_incident_id && (
                    <div className="mt-2 text-[10px] text-red-400 font-mono">
                      Severed by: {route.severed_by_incident_id.slice(0, 8)}...
                    </div>
                  )}
                </div>
              </Popup>
            </Polyline>
          );
        })}

        {/* Incident Clusters */}
        {incidents.map((incident) => {
          const isSelected = incident.cluster_id === selectedClusterId;
          const icon = createClusterIcon(incident, isSelected, palette);

          return (
            <Marker
              key={incident.cluster_id}
              position={[incident.latitude, incident.longitude]}
              icon={icon}
              eventHandlers={{
                click: () => onSelectCluster(incident.cluster_id),
              }}
            >
              <Popup className="tactical-popup">
                <div className="p-3.5 text-xs min-w-[220px] tactical-card">
                  <div className="flex items-center justify-between border-b border-matrix-border pb-2 mb-2">
                    <span className="text-[11px] font-mono text-matrix-muted">
                      ID: {incident.cluster_id.slice(0, 8)}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-matrix-bg text-matrix-text border border-matrix-border">
                      SCORE {Math.round(incident.priority_score)}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    <div className="text-matrix-text font-medium">
                      Hazard:{" "}
                      <span className="capitalize font-semibold text-matrix-accent">
                        {incident.hazard_type.replace("_", " ")}
                      </span>
                    </div>
                    <div className="text-matrix-muted text-[11px]">
                      Merged Reports:{" "}
                      <strong className="text-matrix-text font-mono">
                        {incident.report_count}
                      </strong>{" "}
                      via spatial consensus
                    </div>
                    {incident.uncertainty_escalated && (
                      <div className="mt-1 bg-red-500/20 border border-red-500/40 text-red-400 text-[10px] font-semibold px-2 py-1 rounded">
                        ⚠️ UNCERTAINTY ESCALATED
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => onSelectCluster(incident.cluster_id)}
                    className="w-full mt-3 py-1.5 bg-matrix-accent text-white font-mono font-bold rounded text-xs transition hover:opacity-90 shadow-md"
                  >
                    SELECT IN QUEUE
                  </button>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
