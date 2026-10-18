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
        ink: '#07090D',
        'ink-panel': 'rgba(13, 17, 23, 0.55)',
        'ink-deep': '#0A0D13',
        'ink-2': '#0D1117',
        text: '#ECE8DF',
        muted: '#8B93A1',
        accent: '#F2A33A',      /* Restrained Warm Amber / Saffron */
        data: '#3FB6A8',        /* Surgical Telemetry Teal */
        alert: '#E5484D',       /* High-Risk Crimson */
        // Backward-compatible semantic mappings (de-cyanified)
        deepNavy: '#07090D',
        panelNavy: '#0D1117',
        cardBg: '#0E131A',
        cyberCyan: '#3FB6A8',   /* Replaced harsh neon with surgical teal */
        cyberViolet: '#F2A33A', /* Replaced purple with amber */
        cyberEmerald: '#3FB6A8',
        neonBlue: '#3FB6A8',
        brand: {
          darkest: '#05070A',
          dark: '#07090D',
          navy: '#0A0D13',
          deep: '#0D1117',
          card: '#0E131A',
          surface: '#121722',
          border: 'rgba(255, 255, 255, 0.08)',
          borderLight: 'rgba(255, 255, 255, 0.12)',
          blue: '#3FB6A8',
          cyan: '#3FB6A8',
          neonCyan: '#3FB6A8',
          purple: '#F2A33A',
          amber: '#F2A33A',
          crimson: '#E5484D',
          emerald: '#3FB6A8',
        }
      },
      fontFamily: {
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
        sans: ['"Inter Tight"', 'Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace'],
        cyber: ['"Inter Tight"', 'sans-serif'],
      },
      boxShadow: {
        'glow-accent': '0 0 25px -4px rgba(242, 163, 58, 0.35)',
        'glow-data': '0 0 25px -4px rgba(63, 182, 168, 0.35)',
        'glow-alert': '0 0 25px -4px rgba(229, 72, 77, 0.35)',
      }
    },
  },
  plugins: [],
}
