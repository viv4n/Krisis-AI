"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export type MatrixPalette = "cyber-neon" | "emerald-grid" | "monochrome";

interface ThemeContextType {
  palette: MatrixPalette;
  stealthMode: boolean;
  setPalette: (p: MatrixPalette) => void;
  setStealthMode: (s: boolean) => void;
  resetDefault: () => void;
}

const ThemeContext = createContext<ThemeContextType>({
  palette: "cyber-neon",
  stealthMode: false,
  setPalette: () => {},
  setStealthMode: () => {},
  resetDefault: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [palette, setPaletteState] = useState<MatrixPalette>("cyber-neon");
  const [stealthMode, setStealthModeState] = useState<boolean>(false);

  useEffect(() => {
    try {
      const savedPalette = localStorage.getItem("krisis-matrix-palette") as MatrixPalette | null;
      const savedStealth = localStorage.getItem("krisis-stealth-mode") === "true";

      const initialPalette = (savedPalette && ["cyber-neon", "emerald-grid", "monochrome"].includes(savedPalette))
        ? savedPalette
        : "cyber-neon";

      setPaletteState(initialPalette);
      setStealthModeState(savedStealth);

      document.documentElement.setAttribute("data-matrix", initialPalette);
      document.documentElement.setAttribute("data-stealth", savedStealth ? "true" : "false");
    } catch {
      // ignore storage errors
    }
  }, []);

  const setPalette = (newPalette: MatrixPalette) => {
    setPaletteState(newPalette);
    try {
      localStorage.setItem("krisis-matrix-palette", newPalette);
    } catch {}
    document.documentElement.setAttribute("data-matrix", newPalette);
  };

  const setStealthMode = (isStealth: boolean) => {
    setStealthModeState(isStealth);
    try {
      localStorage.setItem("krisis-stealth-mode", isStealth ? "true" : "false");
    } catch {}
    document.documentElement.setAttribute("data-stealth", isStealth ? "true" : "false");
  };

  const resetDefault = () => {
    setPalette("cyber-neon");
    setStealthMode(false);
  };

  return (
    <ThemeContext.Provider
      value={{
        palette,
        stealthMode,
        setPalette,
        setStealthMode,
        resetDefault,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useAppTheme() {
  return useContext(ThemeContext);
}
