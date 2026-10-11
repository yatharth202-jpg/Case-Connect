/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        deepNavy: '#040711',
        panelNavy: '#080E1E',
        cardBg: '#091124',
        cyberCyan: '#00F0FF',
        cyberViolet: '#8B5CF6',
        cyberEmerald: '#10B981',
        neonBlue: '#38BDF8',
        brand: {
          darkest: '#030712',
          dark: '#070b14',
          navy: '#060d1f',
          deep: '#0b132b',
          card: '#0c1322',
          surface: '#0d172e',
          border: '#1a2742',
          borderLight: '#1e293b',
          blue: '#2563eb',
          cyan: '#06b6d4',
          neonCyan: '#00d2ff',
          purple: '#8b5cf6',
          amber: '#f59e0b',
          crimson: '#e11d48',
          emerald: '#10b981',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        cyber: ['Rajdhani', 'sans-serif'],
        mono: ['Share Tech Mono', 'monospace'],
      },
      boxShadow: {
        'glow-cyan': '0 0 25px -4px rgba(0, 240, 255, 0.35)',
        'glow-violet': '0 0 25px -4px rgba(139, 92, 246, 0.4)',
        'glow-emerald': '0 0 25px -4px rgba(16, 185, 129, 0.35)',
      }
    },
  },
  plugins: [],
}
