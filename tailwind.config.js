/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        gold: {
          50:  '#FFFBF0',
          100: '#FEF3CC',
          200: '#FDE89A',
          300: '#FBD55A',
          400: '#F5BE1F',
          500: '#D4A017',
          600: '#A87B0E',
          700: '#7D5A09',
          800: '#523A05',
          900: '#2A1D02',
        }
      },
      fontFamily: {
        serif: ['Playfair Display', 'Georgia', 'serif'],
        sans: ['DM Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
