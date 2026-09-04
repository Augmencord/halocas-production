import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "#111827",
        panel: "#1f2937",
        border: "#374151",
        cyan: "#00FFFF",
        red: "#FF3B30",
        green: "#10B981",
        halocas: {
          bg: "#111827",
          panel: "#1f2937",
          border: "#374151",
          cyan: "#00FFFF",
          red: "#FF3B30",
          green: "#10B981",
          amber: "#F59E0B",
          dark: "#0B0F17",
          slate: "#1e293b",
          subtle: "#9CA3AF",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "sans-serif"],
      },
      boxShadow: {
        "cyan-glow": "0 0 20px rgba(0, 255, 255, 0.25)",
        "cyan-glow-lg": "0 0 35px rgba(0, 255, 255, 0.4)",
        "red-glow": "0 0 20px rgba(255, 59, 48, 0.35)",
        "green-glow": "0 0 20px rgba(16, 185, 129, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
