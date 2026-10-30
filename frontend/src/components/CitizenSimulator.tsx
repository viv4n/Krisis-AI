import React, { useState } from "react";
import { SubmitReportPayload } from "@/types/api";
import { submitReport } from "@/lib/api";
import {
  X,
  Send,
  Camera,
  MapPin,
  MessageSquare,
  AlertCircle,
  CheckCircle,
} from "lucide-react";

interface CitizenSimulatorProps {
  isOpen: boolean;
  onClose: () => void;
  selectedLat: number;
  selectedLng: number;
  onReportSubmitted: () => void;
}

const HOUSTON_PRESETS = [
  {
    title: "Buffalo Bayou Surging",
    text: "URGENT: Buffalo Bayou overflowing over Memorial Parkway. Multiple cars stalled with families trapped!",
    hazard: "flood",
  },
  {
    title: "I-45 Overpass Wall Fracture",
    text: "Structural fracture on I-45 North overpass support column following flood surge. High collapse risk.",
    hazard: "structural_damage",
  },
  {
    title: "Submerged Clinic Access Road",
    text: "Main street leading into medical clinic completely submerged under 4ft water. Road impassable.",
    hazard: "blocked_road",
  },
];

const MOCK_IMAGES = [
  {
    name: "Bayou Flood Waters (Cam 1)",
    data: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='120' viewBox='0 0 200 120'><rect width='200' height='120' fill='%23131824'/><text x='15' y='65' fill='%23f8fafc' font-family='monospace' font-size='11'>[BAYOU_WATER_SURGE_01]</text></svg>",
  },
  {
    name: "Structural Fracture (Cam 2)",
    data: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='120' viewBox='0 0 200 120'><rect width='200' height='120' fill='%23131824'/><text x='15' y='65' fill='%23f43f5e' font-family='monospace' font-size='11'>[PIER_STRUCT_CRACK_02]</text></svg>",
  },
];

export default function CitizenSimulator({
  isOpen,
  onClose,
  selectedLat,
  selectedLng,
  onReportSubmitted,
}: CitizenSimulatorProps) {
  const [lat, setLat] = useState<string>(selectedLat.toFixed(4));
  const [lng, setLng] = useState<string>(selectedLng.toFixed(4));
  const [text, setText] = useState<string>(
    "URGENT: Buffalo Bayou overflowing over Memorial Parkway. Multiple cars stalled with families trapped!"
  );
  const [source, setSource] = useState<"web" | "whatsapp" | "sms">("whatsapp");
  const [selectedImage, setSelectedImage] = useState<string>(
    MOCK_IMAGES[0].data
  );
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<{
    status: string;
    report_id: string;
    message: string;
    isFallback: boolean;
  } | null>(null);

  React.useEffect(() => {
    setLat(selectedLat.toFixed(4));
    setLng(selectedLng.toFixed(4));
  }, [selectedLat, selectedLng]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setResult(null);

    const payload: SubmitReportPayload = {
      latitude: parseFloat(lat) || 29.7604,
      longitude: parseFloat(lng) || -95.3698,
      text,
      source,
      image_base64: selectedImage,
    };

    try {
      const res = await submitReport(payload);
      setResult({
        status: res.response.status,
        report_id: res.response.report_id,
        message: res.response.message,
        isFallback: res.isFallback,
      });
      onReportSubmitted();
    } catch {
      setResult({
        status: "error",
        report_id: "ERR-001",
        message: "Failed to ingest report.",
        isFallback: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md tactical-card border-l border-matrix-border rounded-none shadow-2xl flex flex-col font-sans animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-4 border-b border-matrix-border flex items-center justify-between bg-matrix-surface">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded bg-matrix-accent text-white">
            <Send className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-matrix-text">
              Citizen Report Simulator
            </h3>
            <p className="text-[10px] font-mono text-matrix-muted">
              POST /api/v1/report
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-matrix-muted hover:text-matrix-text p-1 rounded hover:bg-matrix-card transition"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <label className="block text-[10px] font-mono uppercase text-matrix-muted mb-1.5">
            Disaster Scenario Presets (Houston Basin)
          </label>
          <div className="grid grid-cols-1 gap-1.5">
            {HOUSTON_PRESETS.map((tmpl, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setText(tmpl.text)}
                className="text-left text-xs p-2 rounded border border-matrix-border bg-matrix-card text-matrix-text hover:bg-matrix-surface transition truncate font-mono"
              >
                + {tmpl.title}
              </button>
            ))}
          </div>
        </div>

        {/* Source Channels */}
        <div>
          <label className="block text-[10px] font-mono uppercase text-matrix-muted mb-1">
            Origin Channel (Source)
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(["whatsapp", "web", "sms"] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSource(s)}
                className={`py-1.5 text-xs font-mono font-bold uppercase rounded border transition ${
                  source === s
                    ? "bg-matrix-accent text-white border-matrix-accent shadow-sm"
                    : "bg-matrix-card text-matrix-muted border-matrix-border hover:text-matrix-text"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Coordinates */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] font-mono uppercase text-matrix-muted flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-matrix-muted" />
              <span>Disaster Coordinates</span>
            </label>
            <span className="text-[10px] font-mono text-matrix-muted">
              (Click on map to drop pin)
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <span className="text-[9px] font-mono text-matrix-muted uppercase">Latitude</span>
              <input
                type="text"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                className="w-full bg-matrix-card border border-matrix-border rounded px-2.5 py-1.5 text-xs font-mono text-matrix-text focus:outline-none focus:border-matrix-accent"
                required
              />
            </div>
            <div>
              <span className="text-[9px] font-mono text-matrix-muted uppercase">Longitude</span>
              <input
                type="text"
                value={lng}
                onChange={(e) => setLng(e.target.value)}
                className="w-full bg-matrix-card border border-matrix-border rounded px-2.5 py-1.5 text-xs font-mono text-matrix-text focus:outline-none focus:border-matrix-accent"
                required
              />
            </div>
          </div>
        </div>

        {/* Description Text */}
        <div>
          <label className="block text-[10px] font-mono uppercase text-matrix-muted mb-1 flex items-center gap-1">
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Citizen Description</span>
          </label>
          <textarea
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="w-full bg-matrix-card border border-matrix-border rounded p-2.5 text-xs font-mono text-matrix-text focus:outline-none focus:border-matrix-accent resize-none"
            placeholder="Describe visible damage, bridge overflow, trapped citizens..."
            required
          />
          <span className="text-[10px] font-mono text-matrix-muted">
            Keywords &quot;urgent&quot;, &quot;trap&quot;, or &quot;help&quot; trigger uncertainty escalation.
          </span>
        </div>

        {/* Telemetry Photo */}
        <div>
          <label className="block text-[10px] font-mono uppercase text-matrix-muted mb-1 flex items-center gap-1">
            <Camera className="w-3.5 h-3.5" />
            <span>Telemetry Photo (image_base64)</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            {MOCK_IMAGES.map((img, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setSelectedImage(img.data)}
                className={`p-2 rounded border text-left text-xs font-mono transition ${
                  selectedImage === img.data
                    ? "border-matrix-accent bg-matrix-surface ring-1 ring-matrix-accent text-matrix-text"
                    : "border-matrix-border bg-matrix-card text-matrix-muted hover:text-matrix-text"
                }`}
              >
                <div className="font-semibold truncate">{img.name}</div>
                <div className="text-[9px] opacity-70 mt-0.5">Base64 attached</div>
              </button>
            ))}
          </div>
        </div>

        {result && (
          <div
            className={`p-3 rounded border font-mono text-xs ${
              result.status === "escalated"
                ? "border-red-500/50 bg-red-500/10 text-red-400"
                : "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
            }`}
          >
            <div className="flex items-center space-x-1.5 font-bold mb-1">
              {result.status === "escalated" ? (
                <AlertCircle className="w-4 h-4 text-red-400" />
              ) : (
                <CheckCircle className="w-4 h-4 text-emerald-400" />
              )}
              <span className="uppercase">
                INGESTION: {result.status} {result.isFallback ? "(FALLBACK MOCK)" : ""}
              </span>
            </div>
            <div className="text-[11px] opacity-90">{result.message}</div>
            <div className="mt-1 text-[10px] opacity-75 truncate">
              REPORT ID: {result.report_id}
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-2.5 px-4 rounded bg-matrix-accent hover:opacity-90 active:scale-98 text-white font-mono font-bold text-xs uppercase shadow-md shadow-matrix-glow transition flex items-center justify-center space-x-2 disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
          <span>{isSubmitting ? "TRANSMITTING TELEMETRY..." : "TRANSMIT CITIZEN REPORT"}</span>
        </button>
      </form>
    </div>
  );
}
