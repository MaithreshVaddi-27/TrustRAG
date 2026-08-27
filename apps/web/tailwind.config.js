/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // ── Color system ───────────────────────────────────────────────────
      colors: {
        // Primary — trust / reliability blue
        primary: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        // Surface — dark backgrounds
        surface: {
          50:  '#f8fafc',
          100: '#f1f5f9',
          800: '#1e293b',
          850: '#172033',
          900: '#0f172a',
          950: '#080c16',
        },
        // Semantic states
        verified:   '#22c55e',   // SUPPORTED — green
        contradicted: '#ef4444', // CONTRADICTED — red
        unsupported: '#f59e0b',  // UNSUPPORTED — amber
        unknown:    '#6b7280',   // UNKNOWN — grey
        // Reliability bands
        trust: {
          high:   '#22c55e',
          medium: '#f59e0b',
          low:    '#ef4444',
        },
      },
      // ── Typography ─────────────────────────────────────────────────────
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      // ── Animation ──────────────────────────────────────────────────────
      animation: {
        'fade-in':    'fadeIn 0.2s ease-out',
        'slide-up':   'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow':  'spin 3s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      // ── Glassmorphism ──────────────────────────────────────────────────
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
