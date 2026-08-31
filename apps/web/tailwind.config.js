/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // ── Color system (Zero purple / violet / pink) ─────────────────────
      colors: {
        // Primary — electric cyber azure / sky
        primary: {
          50:  '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
          950: '#041d30',
        },
        // Cyber cyan accents
        cyber: {
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
        },
        // Surface — obsidian & space dark
        surface: {
          50:  '#f8fafc',
          100: '#f1f5f9',
          700: '#1e293b',
          800: '#121826',
          850: '#0d1322',
          900: '#080c16',
          950: '#040711',
        },
        // Semantic states
        verified:     '#10b981', // SUPPORTED — emerald
        contradicted: '#ef4444', // CONTRADICTED — crimson
        unsupported:  '#f59e0b', // UNSUPPORTED — amber
        unknown:      '#64748b', // UNKNOWN — slate
        // Reliability bands
        trust: {
          high:   '#10b981',
          medium: '#f59e0b',
          low:    '#ef4444',
        },
      },
      // ── Typography ─────────────────────────────────────────────────────
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      // ── Animation & Micro-effects ──────────────────────────────────────
      animation: {
        'fade-in':     'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up':    'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-slow':  'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow':   'spin 4s linear infinite',
        'glow':        'glow 2s ease-in-out infinite alternate',
        'float':       'float 5s ease-in-out infinite',
        'scan':        'scan 3s ease-in-out infinite',
        'shimmer':     'shimmer 2.5s linear infinite',
        'radar-sweep': 'radarSweep 2.5s linear infinite',
        'halo-pulse':  'haloPulse 2s cubic-bezier(0, 0, 0.2, 1) infinite',
        'border-glow': 'borderGlow 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%':   { filter: 'drop-shadow(0 0 6px rgba(14, 165, 233, 0.4))' },
          '100%': { filter: 'drop-shadow(0 0 16px rgba(14, 165, 233, 0.8))' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-8px)' },
        },
        scan: {
          '0%':   { top: '0%' },
          '50%':  { top: '95%' },
          '100%': { top: '0%' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        radarSweep: {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        haloPulse: {
          '0%':   { transform: 'scale(0.95)', opacity: '0.8' },
          '50%':  { transform: 'scale(1.25)', opacity: '0' },
          '100%': { transform: 'scale(0.95)', opacity: '0' },
        },
        borderGlow: {
          '0%, 100%': { borderColor: 'rgba(14, 165, 233, 0.3)', boxShadow: '0 0 15px rgba(14, 165, 233, 0.15)' },
          '50%':      { borderColor: 'rgba(6, 182, 212, 0.7)', boxShadow: '0 0 25px rgba(6, 182, 212, 0.35)' },
        },
      },
      // ── Cyber Glow Box Shadows ──────────────────────────────────────────
      boxShadow: {
        'glow-primary': '0 0 25px -2px rgba(14, 165, 233, 0.45), 0 0 10px -1px rgba(14, 165, 233, 0.3)',
        'glow-cyan':    '0 0 25px -2px rgba(6, 182, 212, 0.45), 0 0 10px -1px rgba(6, 182, 212, 0.3)',
        'glow-emerald': '0 0 25px -2px rgba(16, 185, 129, 0.45), 0 0 10px -1px rgba(16, 185, 129, 0.3)',
        'glow-crimson': '0 0 25px -2px rgba(239, 68, 68, 0.45), 0 0 10px -1px rgba(239, 68, 68, 0.3)',
        'glow-amber':   '0 0 25px -2px rgba(245, 158, 11, 0.45), 0 0 10px -1px rgba(245, 158, 11, 0.3)',
      },
      // ── Glassmorphism ──────────────────────────────────────────────────
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
