/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  detpMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f7ff",
          100: "#e0effe",
          200: "#bae0fd",
          300: "#7cc5fb",
          400: "#38a6f6",
          500: "#0e87ea",
          600: "#026bc8",
          700: "#0355a2",
          800: "#074885",
          900: "#0c3d6e",
          950: "#082749",
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
        mono: ["JetBrains Mono", "monospace"],
      }
    },
  },
  plugins: [],
}
