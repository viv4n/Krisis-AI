"use client";

import React, { useState, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import TacticalMap from "@/components/TacticalMap";
import TriageQueue from "@/components/TriageQueue";
import ClusterDetailModal from "@/components/ClusterDetailModal";
import CitizenSimulator from "@/components/CitizenSimulator";
import ThemeSettingsModal from "@/components/ThemeSettingsModal";
import { fetchIncidents, fetchRoutePassability, subscribeToIncidents } from "@/lib/api";
import { IncidentCluster, RoutePassability } from "@/types/api";

const DEFAULT_LAT = 29.7604;
const DEFAULT_LNG = -95.3698;

export default function Dashboard() {
  const [incidents, setIncidents] = useState<IncidentCluster[]>([]);
  const [routes, setRoutes] = useState<RoutePassability[]>([]);
  const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);
  const [inspectingCluster, setInspectingCluster] = useState<IncidentCluster | null>(null);
  const [isOffline, setIsOffline] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState<boolean>(false);
  const [isThemeModalOpen, setIsThemeModalOpen] = useState<boolean>(false);

  const [simulatorLat, setSimulatorLat] = useState<number>(DEFAULT_LAT);
  const [simulatorLng, setSimulatorLng] = useState<number>(DEFAULT_LNG);

  // Strict dynamic fetching from backend at http://localhost:8000/api/v1/...
  const loadData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [incidentsRes, routesRes] = await Promise.all([
        fetchIncidents(),
        fetchRoutePassability(),
      ]);

      setIncidents(incidentsRes.data);
      setRoutes(routesRes.data);
      setIsOffline(incidentsRes.isFallback || routesRes.isFallback);

      if (!selectedClusterId && incidentsRes.data.length > 0) {
        setSelectedClusterId(incidentsRes.data[0].cluster_id);
      }
    } catch {
      setIsOffline(true);
    } finally {
      setIsRefreshing(false);
    }
  }, [selectedClusterId]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);

    // Real-time WebSocket connection to backend ws://localhost:8000/ws/incidents
    const unsubscribe = subscribeToIncidents((realtimeData) => {
      setIsOffline(false);
      if (!realtimeData) return;

      // Case 1: Initial state or bulk array of incidents
      if (Array.isArray(realtimeData)) {
        setIncidents(realtimeData);
        return;
      }

      // Case 2: Individual incoming incident report or cluster broadcast
      const payloadObj = realtimeData as Record<string, unknown>;
      const newIncident: IncidentCluster | null =
        (payloadObj.incident as IncidentCluster | undefined) ||
        (typeof payloadObj.cluster_id === "string" && typeof payloadObj.priority_score === "number"
          ? (realtimeData as IncidentCluster)
          : null);

      if (Array.isArray(payloadObj.incidents)) {
        setIncidents(payloadObj.incidents as IncidentCluster[]);
      } else if (newIncident && newIncident.cluster_id) {
        setIncidents((prev) => {
          const exists = prev.some((inc) => inc.cluster_id === newIncident.cluster_id);
          if (exists) {
            return prev.map((inc) =>
              inc.cluster_id === newIncident.cluster_id ? { ...inc, ...newIncident } : inc
            );
          }
          return [newIncident, ...prev];
        });
      }

      if (newIncident && newIncident.cluster_id) {
        setSelectedClusterId((prevSelected) => prevSelected || newIncident.cluster_id);
      }
    });

    return () => {
      clearInterval(interval);
      unsubscribe();
    };
  }, [loadData]);

  const handleMapLocationSelect = (lat: number, lng: number) => {
    setSimulatorLat(lat);
    setSimulatorLng(lng);
    setIsSimulatorOpen(true);
  };

  const handleOpenDetails = (cluster: IncidentCluster) => {
    setInspectingCluster(cluster);
  };

  const handleDispatchOverride = (clusterId: string, action: string) => {
    if (action === "APPROVE_DISPATCH" || action === "OVERRIDE_DISPATCH") {
      setIncidents((prev) =>
        prev.map((item) =>
          item.cluster_id === clusterId
            ? { ...item, uncertainty_escalated: false }
            : item
        )
      );
      if (inspectingCluster && inspectingCluster.cluster_id === clusterId) {
        setInspectingCluster((prev) =>
          prev ? { ...prev, uncertainty_escalated: false } : null
        );
      }
    }
  };

  const criticalCount = incidents.filter((i) => i.priority_score > 75).length;
  const escalatedCount = incidents.filter((i) => i.uncertainty_escalated).length;

  return (
    <div className="flex flex-col h-screen w-screen bg-matrix-bg text-matrix-text overflow-hidden font-sans select-none">
      {/* Header */}
      <Header
        totalIncidents={incidents.length}
        criticalCount={criticalCount}
        escalatedCount={escalatedCount}
        isOffline={isOffline}
        onOpenSimulator={() => setIsSimulatorOpen(true)}
        onOpenThemeSettings={() => setIsThemeModalOpen(true)}
        onRefresh={loadData}
        isRefreshing={isRefreshing}
      />

      {/* Main Split-Pane Layout with Strict Height Map */}
      <div className="relative flex-1 w-full h-[calc(100vh-4rem)] overflow-hidden flex flex-col md:flex-row">
        {/* Left Map Viewport with strict physical height to prevent 0px Leaflet collapse */}
        <section className="flex-1 h-[55vh] md:h-full min-h-[550px] relative border-b md:border-b-0 md:border-r border-matrix-border">
          <TacticalMap
            incidents={incidents}
            routes={routes}
            selectedClusterId={selectedClusterId}
            onSelectCluster={(id) => {
              setSelectedClusterId(id);
              const found = incidents.find((i) => i.cluster_id === id);
              if (found) {
                setSimulatorLat(found.latitude);
                setSimulatorLng(found.longitude);
              }
            }}
            onLocationSelect={handleMapLocationSelect}
          />

          {/* Disaster Coordinates Overlay HUD */}
          <div className="absolute top-3 left-3 z-10 hidden sm:flex items-center space-x-2 px-2.5 py-1 rounded tactical-card border text-[11px] font-mono text-matrix-muted">
            <span className="w-1.5 h-1.5 rounded-full bg-matrix-accent animate-pulse" />
            <span>29.7604° N, 95.3698° W</span>
            <span>•</span>
            <span>HOUSTON FLOOD MATRIX</span>
          </div>
        </section>

        {/* Right Triage Queue Panel */}
        <aside className="w-full md:w-[420px] lg:w-[450px] h-[45vh] md:h-full flex flex-col shrink-0 tactical-card rounded-none border-l border-matrix-border">
          <TriageQueue
            incidents={incidents}
            selectedClusterId={selectedClusterId}
            onSelectCluster={(id) => {
              setSelectedClusterId(id);
              const found = incidents.find((i) => i.cluster_id === id);
              if (found) {
                setSimulatorLat(found.latitude);
                setSimulatorLng(found.longitude);
              }
            }}
            onOpenDetails={handleOpenDetails}
          />
        </aside>
      </div>

      {/* Cluster Detail Dossier Modal */}
      <ClusterDetailModal
        cluster={inspectingCluster}
        onClose={() => setInspectingCluster(null)}
        onDispatchOverride={handleDispatchOverride}
      />

      {/* Citizen Report Ingestion Simulator Drawer */}
      <CitizenSimulator
        isOpen={isSimulatorOpen}
        onClose={() => setIsSimulatorOpen(false)}
        selectedLat={simulatorLat}
        selectedLng={simulatorLng}
        onReportSubmitted={loadData}
      />

      {/* DSU Digital Twin Command Theme Settings Modal */}
      <ThemeSettingsModal
        isOpen={isThemeModalOpen}
        onClose={() => setIsThemeModalOpen(false)}
      />
    </div>
  );
}
