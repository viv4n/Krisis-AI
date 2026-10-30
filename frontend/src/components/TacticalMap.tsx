"use client";

import React from "react";
import dynamic from "next/dynamic";
import { IncidentCluster, RoutePassability } from "@/types/api";

const MapBase = dynamic(() => import("./MapBase"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[550px] flex flex-col items-center justify-center bg-[#090B10] text-[#94A3B8] font-mono text-xs">
      <div className="w-6 h-6 border-2 border-[#F43F5E] border-t-transparent rounded-full animate-spin mb-2"></div>
      INITIALIZING CARTO DARK CARTOGRAPHIC MATRIX...
    </div>
  ),
});

export interface TacticalMapProps {
  incidents: IncidentCluster[];
  routes: RoutePassability[];
  selectedClusterId: string | null;
  onSelectCluster: (clusterId: string) => void;
  onLocationSelect?: (lat: number, lng: number) => void;
}

export default function TacticalMap(props: TacticalMapProps) {
  return (
    <div className="w-full h-full min-h-[550px]">
      <MapBase {...props} />
    </div>
  );
}
