/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#F8FFF8',
          100: '#F0FDF4',
          200: '#DCFCE7',
          300: '#BBF7D0',
          400: '#86EFAC',
          500: '#4ADE80',
          600: '#34A853',
          700: '#15803D',
          800: '#166534',
          900: '#14532D',
        },
        accent: {
          orange: '#FF9800',
          blue: '#2196F3',
          purple: '#9C27B0',
        }
      },
      fontFamily: {
        sans: ['Poppins', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}