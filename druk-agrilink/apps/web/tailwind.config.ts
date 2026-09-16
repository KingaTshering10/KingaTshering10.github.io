import type { Config } from "tailwindcss";

// Warm, earthy palette suited to an agricultural cooperative — no crypto glow.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        field: {
          50: "#f4f8ef",
          100: "#e5efd8",
          500: "#5c8a3a",
          600: "#4a7230",
          700: "#3a5a26",
          800: "#2e4720",
        },
        earth: { 50: "#faf6f0", 100: "#f1e8da", 500: "#a5723c", 700: "#7c5222" },
        maize: { 100: "#fdf3d7", 500: "#e0a526", 700: "#a87a15" },
      },
    },
  },
  plugins: [],
};
export default config;
