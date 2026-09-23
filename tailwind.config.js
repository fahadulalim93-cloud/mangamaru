/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#000",
        surface: "#0a0a0a",
        "surface-2": "#141414",
        border: "#1f1f1f",
        accent: "#FF6B35",
        "accent-soft": "rgba(255, 107, 53, 0.15)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Poppins", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
