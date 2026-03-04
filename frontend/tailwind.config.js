/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        'verdict-high-risk': '#EF4444',
        'verdict-suspicious': '#F97316',
        'verdict-uncertain': '#EAB308',
        'verdict-authentic': '#22C55E',
        'satya-dark': '#0F172A',
        'satya-card': '#1E293B',
        'satya-border': '#334155',
        'satya-muted': '#94A3B8',
      },
    },
  },
  plugins: [],
}
