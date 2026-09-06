/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07100f",
        panel: "#0c1715",
        line: "#203a35",
        mint: "#69f0c3",
        cyan: "#55cfe0",
        amber: "#f6be5d",
        muted: "#8aa59f",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(105,240,195,.08), 0 24px 80px rgba(0,0,0,.32)",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "Cascadia Code", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
