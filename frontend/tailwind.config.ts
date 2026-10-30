import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        matrix: {
          bg: "var(--matrix-bg)",
          surface: "var(--matrix-surface)",
          card: "var(--matrix-card)",
          border: "var(--matrix-border)",
          text: "var(--matrix-text)",
          muted: "var(--matrix-muted)",
          accent: "var(--matrix-accent)",
          high: "var(--matrix-high)",
          med: "var(--matrix-med)",
          low: "var(--matrix-low)",
          glow: "var(--matrix-glow)",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
