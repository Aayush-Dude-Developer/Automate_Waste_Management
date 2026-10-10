/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        restaurant: {
          primary: '#059669', // Emerald 600
          secondary: '#d97706', // Amber 600
          dark: '#1e293b', // Slate 800
          light: '#f8fafc', // Slate 50
        }
      }
    },
  },
  plugins: [],
}
