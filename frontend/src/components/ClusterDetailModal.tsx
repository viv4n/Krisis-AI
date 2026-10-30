import React, { useState } from "react";
import { IncidentCluster } from "@/types/api";
import {
  X,
  AlertTriangle,
  Clock,
  Layers,
  CheckCircle2,
  ShieldCheck,
  Cpu,
} from "lucide-react";

interface ClusterDetailModalProps {
  cluster: IncidentCluster | null;
  onClose: () => void;
  onDispatchOverride?: (clusterId: string, action: string) => void;
}

export default function ClusterDetailModal({
  cluster,
  onClose,
  onDispatchOverride,
}: ClusterDetailModalProps) {
  const [dispatchStatus, setDispatchStatus] = useState<string | null>(null);

  if (!cluster) return null;

  const handleAction = (action: string) => {
    setDispatchStatus(`Tactical action [${action}] transmitted to local units.`);
    if (onDispatchOverride) {
      onDispatchOverride(cluster.cluster_id, action);
    }
    setTimeout(() => {
      setDispatchStatus(null);
    }, 4000);
  };

  const isHigh = cluster.priority_score > 75;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg tactical-card p-0 shadow-2xl overflow-hidden font-sans border border-matrix-border transition-all duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-matrix-border bg-matrix-surface">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded bg-matrix-accent text-white">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] font-mono text-matrix-muted uppercase tracking-wider">
                Consensus Cluster Dossier
              </div>
              <div className="text-sm font-bold text-matrix-text truncate max-w-xs font-mono">
                {cluster.cluster_id}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-matrix-muted hover:text-matrix-text hover:bg-matrix-card transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Alerts */}
        {cluster.uncertainty_escalated && (
          <div className="bg-red-500/15 border-b border-red-500/30 px-4 py-2 flex items-center space-x-2 text-xs text-red-400 font-medium">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Human Review Required: Conflicting citizen telemetry flagged.</span>
          </div>
        )}

        {dispatchStatus && (
          <div className="bg-emerald-500/15 border-b border-emerald-500/30 px-4 py-2 flex items-center space-x-2 text-xs text-emerald-400 font-medium">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{dispatchStatus}</span>
          </div>
        )}

        {/* Content Body */}
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded border border-matrix-border bg-matrix-surface">
              <span className="text-[10px] text-matrix-muted uppercase font-mono">
                Hazard Classification
              </span>
              <div className="text-sm font-bold text-matrix-text capitalize mt-0.5">
                {cluster.hazard_type.replace("_", " ")}
              </div>
            </div>

            <div className="p-3 rounded border border-matrix-border bg-matrix-surface">
              <span className="text-[10px] text-matrix-muted uppercase font-mono">
                Priority Score
              </span>
              <div
                className="text-sm font-bold font-mono mt-0.5"
                style={{ color: isHigh ? "var(--matrix-high)" : "var(--matrix-med)" }}
              >
                {cluster.priority_score.toFixed(1)} / 100.0
              </div>
            </div>
          </div>

          {/* Spatial Consensus Banner */}
          <div className="p-3.5 rounded border border-matrix-border bg-matrix-surface">
            <div className="flex items-center space-x-2 text-matrix-text text-xs font-semibold">
              <Cpu className="w-4 h-4 text-matrix-accent" />
              <span>50m Spatial Consensus Engine</span>
            </div>
            <p className="mt-1 text-xs text-matrix-muted leading-relaxed">
              <strong className="text-matrix-text font-mono">
                {cluster.report_count} reports merged
              </strong>{" "}
              via spatial consensus. Reconciled to geographic centroid:
            </p>
            <div className="mt-2 text-xs font-mono text-matrix-accent bg-matrix-bg p-2 rounded border border-matrix-border">
              LAT {cluster.latitude.toFixed(6)} | LNG {cluster.longitude.toFixed(6)}
            </div>
          </div>

          {/* Timestamps */}
          <div className="p-3 rounded border border-matrix-border bg-matrix-surface space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between text-matrix-muted">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                First Ingestion:
              </span>
              <span className="font-medium text-matrix-text">
                {new Date(cluster.first_reported_at).toLocaleString()}
              </span>
            </div>
            <div className="flex items-center justify-between text-matrix-muted">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                Latest Ingestion:
              </span>
              <span className="font-medium text-matrix-text">
                {new Date(cluster.last_reported_at).toLocaleString()}
              </span>
            </div>
          </div>

          {/* Response Actions */}
          <div className="pt-2 grid grid-cols-2 gap-3">
            <button
              onClick={() => handleAction("APPROVE_DISPATCH")}
              className="py-2.5 px-3 rounded bg-matrix-accent hover:opacity-90 text-white font-mono text-xs font-bold transition flex items-center justify-center space-x-1.5 shadow-md shadow-matrix-glow"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Approve Dispatch</span>
            </button>

            <button
              onClick={() => handleAction("OVERRIDE_DISPATCH")}
              className="py-2.5 px-3 rounded border border-matrix-border bg-matrix-surface text-matrix-text hover:bg-matrix-card font-mono text-xs font-bold transition flex items-center justify-center space-x-1.5"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Override Dispatch</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
