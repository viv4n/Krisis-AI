import React from "react";
import { IncidentCluster } from "@/types/api";
import {
  AlertTriangle,
  Clock,
  MapPin,
  ChevronRight,
} from "lucide-react";

interface TriageQueueProps {
  incidents: IncidentCluster[];
  selectedClusterId: string | null;
  onSelectCluster: (clusterId: string) => void;
  onOpenDetails: (cluster: IncidentCluster) => void;
}

export default function TriageQueue({
  incidents,
  selectedClusterId,
  onSelectCluster,
  onOpenDetails,
}: TriageQueueProps) {
  const sortedIncidents = [...incidents].sort(
    (a, b) => b.priority_score - a.priority_score
  );

  const escalatedClusters = sortedIncidents.filter(
    (inc) => inc.uncertainty_escalated
  );
  const hasEscalated = escalatedClusters.length > 0;

  return (
    <div className="flex flex-col h-full overflow-hidden select-none">
      {/* Top Alert Banner for Human Review if Uncertainty Escalated */}
      {hasEscalated && (
        <div className="m-3 p-3 rounded border border-red-500/50 bg-red-500/10 transition-all duration-200">
          <div className="flex items-start space-x-2.5">
            <div className="p-1 rounded bg-red-600 text-white shrink-0 mt-0.5">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold text-red-400 tracking-tight font-mono">
                HUMAN REVIEW REQUIRED - UNCERTAINTY ESCALATION TRIGGERED
              </div>
              <p className="text-[11px] text-matrix-muted mt-0.5 leading-snug">
                {escalatedClusters.length} cluster(s) with conflicting citizen reports. Tactical override required.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Queue Header */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-matrix-border bg-matrix-surface">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-matrix-accent animate-pulse" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-matrix-text">
            Triage Priority Queue
          </h2>
        </div>
        <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-matrix-card text-matrix-muted border border-matrix-border">
          {sortedIncidents.length} NODES
        </span>
      </div>

      {/* Incidents List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sortedIncidents.map((incident) => {
          const isSelected = incident.cluster_id === selectedClusterId;
          const priority = incident.priority_score;
          const isHigh = priority > 75;
          const isMed = priority >= 40 && priority <= 75;

          const colorToken = isHigh
            ? "var(--matrix-high)"
            : isMed
            ? "var(--matrix-med)"
            : "var(--matrix-low)";

          return (
            <div
              key={incident.cluster_id}
              onClick={() => onSelectCluster(incident.cluster_id)}
              className={`tactical-card p-3.5 cursor-pointer relative transition-all duration-150 ${
                isSelected
                  ? "ring-2 ring-matrix-accent border-matrix-accent shadow-lg shadow-matrix-glow"
                  : "hover:border-matrix-accent hover:-translate-y-0.5"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2.5">
                  <div
                    className="font-mono font-bold text-xs px-2 py-0.5 rounded border"
                    style={{
                      borderColor: colorToken,
                      color: colorToken,
                      backgroundColor: "var(--matrix-bg)",
                    }}
                  >
                    {priority.toFixed(1)}
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-matrix-text capitalize flex items-center gap-1.5 font-mono">
                      <span>{incident.hazard_type.replace("_", " ")}</span>
                      {incident.uncertainty_escalated && (
                        <span className="text-[9px] font-bold font-mono px-1.5 py-0.2 rounded bg-red-600 text-white uppercase">
                          Escalated
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] font-mono text-matrix-muted truncate max-w-[170px]">
                      ID: {incident.cluster_id}
                    </div>
                  </div>
                </div>

                <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-matrix-surface text-matrix-muted border border-matrix-border">
                  {incident.report_count} reports
                </span>
              </div>

              {/* Coordinates & Timestamp */}
              <div className="mt-2.5 pt-2 flex items-center justify-between text-[11px] font-mono text-matrix-muted border-t border-matrix-border">
                <div className="flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 text-matrix-muted" />
                  <span>
                    {incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}
                  </span>
                </div>
                <div className="flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-matrix-muted" />
                  <span>
                    {new Date(incident.last_reported_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>

              {/* Action Link */}
              <div className="mt-2 pt-1 flex items-center justify-between">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenDetails(incident);
                  }}
                  className="text-[11px] font-mono font-medium text-matrix-accent hover:underline flex items-center gap-1"
                >
                  <span>Review Consensus &amp; Dispatch</span>
                  <ChevronRight className="w-3 h-3" />
                </button>
                <span className="text-[10px] font-mono text-matrix-muted">50m consensus</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
