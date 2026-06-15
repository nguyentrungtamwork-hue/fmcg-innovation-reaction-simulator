/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          600: "#2f5bea",
          700: "#2447c0",
          800: "#1d3a99",
        },
      },
    },
  },
  plugins: [],
};
