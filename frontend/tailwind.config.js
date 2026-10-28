/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0fdfa",
          100: "#ccfbf1",
          200: "#99f6e4",
          300: "#5eead4",
          400: "#2dd4bf",
          500: "#14b8a6",
          600: "#0d9488",
          700: "#0f766e",
          800: "#115e59",
          900: "#134e4a",
          950: "#042f2e",
        },
        semantic: {
          include: "#10b981",
          exclude: "#f43f5e",
          maybe: "#f59e0b",
          conflict: "#8b5cf6",
          stale: "#94a3b8",
        },
        pico: {
          p: "#3b82f6",
          i: "#10b981",
          c: "#f59e0b",
          o: "#ec4899",
        }
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      }
    },
  },
  plugins: [],
}
