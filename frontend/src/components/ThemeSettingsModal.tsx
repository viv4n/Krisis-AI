"use client";

import React, { useState } from "react";
import {
  X,
  Check,
  RotateCcw,
  Sliders,
  Shield,
  Zap,
} from "lucide-react";
import { useAppTheme, MatrixPalette } from "@/components/ThemeProvider";

interface ThemeSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface PaletteOption {
  id: MatrixPalette;
  title: string;
  subtitle: string;
  accentLabel: string;
  accentBg: string;
  accentBorder: string;
  accentColor: string;
  previewColors: string[];
}

const PALETTES: PaletteOption[] = [
  {
    id: "cyber-neon",
    title: "Cyber Neon",
    subtitle: "Dark synthwave void with neon rose/magenta telemetry",
    accentLabel: "Magenta / Rose",
    accentBg: "rgba(244, 63, 94, 0.12)",
    accentBorder: "#F43F5E",
    accentColor: "#F43F5E",
    previewColors: ["#F43F5E", "#FB923C", "#38BDF8"],
  },
  {
    id: "emerald-grid",
    title: "Emerald Grid",
    subtitle: "Dark tactical bio-matrix with vibrant mint/emerald telemetry",
    accentLabel: "Mint / Emerald",
    accentBg: "rgba(16, 185, 129, 0.12)",
    accentBorder: "#10B981",
    accentColor: "#10B981",
    previewColors: ["#10B981", "#34D399", "#059669"],
  },
  {
    id: "monochrome",
    title: "Monochrome Stealth",
    subtitle: "Pitch-black OLED backdrop with high-contrast amber/gold telemetry",
    accentLabel: "Amber / Gold",
    accentBg: "rgba(245, 158, 11, 0.12)",
    accentBorder: "#F59E0B",
    accentColor: "#F59E0B",
    previewColors: ["#F59E0B", "#D97706", "#78350F"],
  },
];

export default function ThemeSettingsModal({
  isOpen,
  onClose,
}: ThemeSettingsModalProps) {
  const { palette, stealthMode, setPalette, setStealthMode, resetDefault } = useAppTheme();
  const [selectedPalette, setSelectedPalette] = useState<MatrixPalette>(palette);
  const [stealthActive, setStealthActive] = useState<boolean>(stealthMode);

  // Sync state with context when opened
  React.useEffect(() => {
    setSelectedPalette(palette);
    setStealthActive(stealthMode);
  }, [palette, stealthMode, isOpen]);

  if (!isOpen) return null;

  const handleApply = () => {
    setPalette(selectedPalette);
    setStealthMode(stealthActive);
    onClose();
  };

  const handleReset = () => {
    resetDefault();
    setSelectedPalette("cyber-neon");
    setStealthActive(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-[#0B0F19] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden font-sans text-slate-100">
        {/* Header */}
        <div className="p-5 border-b border-slate-800/80 bg-[#10141E] flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-[#F43F5E]" />
              <h2 className="text-sm font-mono font-bold tracking-wider uppercase text-white">
                Display &amp; Theme Settings
              </h2>
            </div>
            <p className="text-[11px] font-mono text-slate-400 mt-0.5">
              DSU Digital Twin Command Customization
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {/* STEALTH MODE TOGGLE BUTTON */}
            <button
              onClick={() => setStealthActive(!stealthActive)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold transition-all ${
                stealthActive
                  ? "bg-slate-800 text-amber-400 border-amber-500/80 shadow-[0_0_12px_rgba(245,158,11,0.25)]"
                  : "bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700"
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              <span>STEALTH MODE</span>
              <span
                className={`w-2 h-2 rounded-full ml-1 ${
                  stealthActive ? "bg-amber-400 animate-pulse" : "bg-slate-600"
                }`}
              />
            </button>

            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-[#F43F5E]" />
              <span>VISUAL MATRIX PALETTES</span>
            </span>
            <span className="text-[10px] font-mono text-slate-500">
              Select Command Center Telemetry Profile
            </span>
          </div>

          {/* Three Selectable Palette Cards */}
          <div className="grid grid-cols-1 gap-3">
            {PALETTES.map((p) => {
              const isActive = selectedPalette === p.id;

              return (
                <div
                  key={p.id}
                  onClick={() => setSelectedPalette(p.id)}
                  className={`p-4 rounded-xl cursor-pointer transition-all duration-200 border relative ${
                    isActive
                      ? "shadow-lg scale-[1.01]"
                      : "bg-[#111827]/40 border-slate-800/80 hover:border-slate-700 hover:bg-[#111827]/80"
                  }`}
                  style={{
                    backgroundColor: isActive ? p.accentBg : undefined,
                    borderColor: isActive ? p.accentBorder : undefined,
                    boxShadow: isActive ? `0 0 20px -2px ${p.accentColor}33` : undefined,
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-sm font-bold text-white">
                          {p.title}
                        </span>
                        <span
                          className="text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-semibold"
                          style={{
                            color: p.accentColor,
                            borderColor: `${p.accentColor}44`,
                            backgroundColor: `${p.accentColor}15`,
                          }}
                        >
                          {p.accentLabel}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        {p.subtitle}
                      </p>
                    </div>

                    {/* Active checkmark */}
                    <div className="flex items-center space-x-2">
                      <div className="flex items-center -space-x-1">
                        {p.previewColors.map((color, idx) => (
                          <span
                            key={idx}
                            className="w-3 h-3 rounded-full border border-[#0B0F19]"
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>

                      <div
                        className={`w-6 h-6 rounded-full flex items-center justify-center border transition-all ${
                          isActive
                            ? "border-transparent text-white shadow-md"
                            : "border-slate-700 bg-slate-900 text-transparent"
                        }`}
                        style={{
                          backgroundColor: isActive ? p.accentColor : undefined,
                        }}
                      >
                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom Action Bar */}
        <div className="p-4 bg-[#10141E] border-t border-slate-800 flex items-center justify-between">
          <button
            onClick={handleReset}
            className="flex items-center space-x-1.5 px-3 py-2 text-xs font-mono text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset to Default</span>
          </button>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-mono text-slate-300 hover:text-white rounded hover:bg-slate-800 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleApply}
              className="px-5 py-2 rounded-lg bg-[#F43F5E] hover:bg-[#E11D48] active:scale-95 text-white text-xs font-mono font-bold shadow-lg shadow-[#F43F5E]/30 transition-all"
            >
              Apply &amp; Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

