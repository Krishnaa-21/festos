/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        fest: {
          bg: "#0B0F19",
          card: "#111827",
          border: "#1F2937",
          accent: "#6366F1",
          gold: "#F59E0B",
          danger: "#EF4444",
          success: "#10B981"
        }
      }
    },
  },
  plugins: [],
}
