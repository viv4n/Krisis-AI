"use client";

import React from "react";
import {
  Radio,
  Send,
  RotateCw,
  Sliders,
  ShieldAlert,
} from "lucide-react";
import { useAppTheme } from "@/components/ThemeProvider";

interface HeaderProps {
  totalIncidents: number;
  criticalCount: number;
  escalatedCount: number;
  isOffline: boolean;
  onOpenSimulator: () => void;
  onOpenThemeSettings: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export default function Header({
  totalIncidents,
  criticalCount,
  escalatedCount,
  isOffline,
  onOpenSimulator,
  onOpenThemeSettings,
  onRefresh,
  isRefreshing,
}: HeaderProps) {
  const { palette, stealthMode } = useAppTheme();

  return (
    <header className="h-16 w-full tactical-card rounded-none border-b border-matrix-border px-4 lg:px-6 flex items-center justify-between select-none z-30 transition-colors duration-200">
      {/* Brand & Identity */}
      <div className="flex items-center space-x-3">
        <div className="relative flex items-center justify-center w-9 h-9 rounded bg-matrix-text text-matrix-bg shadow-sm">
          <ShieldAlert className="w-5 h-5 text-matrix-accent" />
          <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-matrix-accent opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-matrix-accent"></span>
          </span>
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-sm font-mono font-black tracking-wider text-matrix-text uppercase">
              KRISIS AI
            </span>
            <span className="text-[10px] font-mono uppercase tracking-widest px-1.5 py-0.5 rounded bg-matrix-surface text-matrix-accent border border-matrix-border">
              {"// DAMAGE MAPPER"}
            </span>
          </div>
          <div className="text-[10px] text-matrix-muted flex items-center gap-1.5 font-mono">
            <span>DSU DIGITAL TWIN COMMAND</span>
            <span>•</span>
            <span className="text-matrix-text">HOUSTON BASIN</span>
          </div>
        </div>
      </div>

      {/* Center Tactical Status Metrics */}
      <div className="hidden md:flex items-center space-x-2">
        <div className="flex items-center space-x-1.5 px-3 py-1 rounded tactical-card border text-xs">
          <span className="text-matrix-muted uppercase font-mono text-[10px]">Clusters:</span>
          <span className="font-mono font-bold text-matrix-text">{totalIncidents}</span>
        </div>

        <div className="flex items-center space-x-1.5 px-3 py-1 rounded tactical-card border text-xs">
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "var(--matrix-high)" }} />
          <span className="text-matrix-muted uppercase font-mono text-[10px]">High Priority:</span>
          <span className="font-mono font-bold" style={{ color: "var(--matrix-high)" }}>{criticalCount}</span>
        </div>

        <div className="flex items-center space-x-1.5 px-3 py-1 rounded tactical-card border text-xs">
          <Radio className="w-3.5 h-3.5 text-amber-500" />
          <span className="text-matrix-muted uppercase font-mono text-[10px]">Escalated:</span>
          <span className="font-mono font-bold text-amber-500">{escalatedCount}</span>
        </div>
      </div>

      {/* Right Controls: Theme Settings Modal Trigger, Simulator */}
      <div className="flex items-center space-x-2.5">
        {/* Offline / Live Status Badge */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded text-[11px] font-mono border border-matrix-border bg-matrix-surface text-matrix-muted">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isOffline ? "bg-amber-500" : "bg-emerald-500 animate-pulse"
            }`}
          />
          <span>{isOffline ? "MOCK FALLBACK" : "LIVE BACKEND"}</span>
        </div>

        {/* Refresh Sync */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="p-2 rounded tactical-card hover:bg-matrix-surface text-matrix-text transition border border-matrix-border disabled:opacity-50"
          title="Query latest telemetry"
        >
          <RotateCw
            className={`w-4 h-4 ${isRefreshing ? "animate-spin text-matrix-accent" : ""}`}
          />
        </button>

        {/* CUSTOM THEME & MATRIX PALETTES MODAL TRIGGER */}
        <button
          onClick={onOpenThemeSettings}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded tactical-card hover:bg-matrix-surface border border-matrix-border text-xs font-mono font-semibold text-matrix-text transition-all"
        >
          <Sliders className="w-3.5 h-3.5 text-matrix-accent" />
          <span className="capitalize">{palette.replace("-", " ")}</span>
          {stealthMode && (
            <span className="text-[9px] font-bold px-1 py-0.2 rounded bg-amber-500/20 text-amber-400 border border-amber-500/40">
              STEALTH
            </span>
          )}
        </button>

        {/* Citizen Ingestion Simulator Trigger */}
        <button
          onClick={onOpenSimulator}
          className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded bg-matrix-accent hover:opacity-90 active:scale-95 text-white font-mono text-xs font-bold shadow-md shadow-matrix-glow transition-all"
        >
          <Send className="w-3.5 h-3.5" />
          <span>SIMULATE</span>
        </button>
      </div>
    </header>
  );
}
