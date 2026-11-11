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
        // Slate readability remap (P1-25/S-1): default 500 (#64748b) and
        // 600 (#475569) fail AA on dark surfaces. Lighter values keep body
        // copy readable; scale order is intentionally sacrificed for contrast.
        slate: {
          500: '#7c8ba1',
          600: '#94a3b8',
        },
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
        // Gold luxury accent
        gold: {
          300: '#e5d5a8',
          400: '#d8c9a3',
          500: '#c9ab6e',
        },
      },
      // ── Typography ─────────────────────────────────────────────────────
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'system-ui', 'sans-serif'],
        display: ['Iowan Old Style', 'Palatino Linotype', 'URW Palladio L', 'Georgia', 'Times New Roman', 'serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      fontSize: {
        'display': ['clamp(2.5rem, 5vw, 4.5rem)', { lineHeight: '1.05', letterSpacing: '-0.025em', fontWeight: '800' }],
        'display-sm': ['clamp(1.75rem, 3.5vw, 3rem)', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '800' }],
        'heading-1': ['clamp(1.875rem, 3vw, 2.5rem)', { lineHeight: '1.2', letterSpacing: '-0.015em', fontWeight: '700' }],
        'heading-2': ['clamp(1.5rem, 2.5vw, 2rem)', { lineHeight: '1.25', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-3': ['clamp(1.125rem, 1.5rem, 1.5rem)', { lineHeight: '1.3', letterSpacing: '-0.005em', fontWeight: '600' }],
        'body-lg': ['1.125rem', { lineHeight: '1.65', letterSpacing: '0' }],
        'body': ['1rem', { lineHeight: '1.65', letterSpacing: '0' }],
        'body-sm': ['0.875rem', { lineHeight: '1.55', letterSpacing: '0' }],
        'caption': ['0.75rem', { lineHeight: '1.5', letterSpacing: '0.01em', fontWeight: '500' }],
        'mono-xs': ['0.6875rem', { lineHeight: '1.5', letterSpacing: '0.02em', fontFamily: 'var(--font-mono)' }],
        'mono-sm': ['0.75rem', { lineHeight: '1.5', letterSpacing: '0.015em', fontFamily: 'var(--font-mono)' }],
        'mono-base': ['0.875rem', { lineHeight: '1.55', letterSpacing: '0.01em', fontFamily: 'var(--font-mono)' }],
      },
      // ── Animation & Micro-effects ──────────────────────────────────────
      animation: {
        'fade-in':     'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up':    'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-down':  'slideDown 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-left':  'slideLeft 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-right': 'slideRight 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in':    'scaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-slow':  'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow':   'spin 4s linear infinite',
        'glow':        'glow 2s ease-in-out infinite alternate',
        'float':       'float 5s ease-in-out infinite',
        'scan':        'scan 3s ease-in-out infinite',
        'shimmer':     'shimmer 2.5s linear infinite',
        'radar-sweep': 'radarSweep 2.5s linear infinite',
        'halo-pulse':  'haloPulse 2s cubic-bezier(0, 0, 0.2, 1) infinite',
        'border-glow': 'borderGlow 3s ease-in-out infinite',
        'rotate-beam': 'rotateBeam 4s linear infinite',
        'shine':       'shine 3s ease-in-out infinite',
        'scanline-move': 'scanlineMove 8s linear infinite',
        'stagger-in':  'staggerIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both',
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
        slideDown: {
          '0%':   { opacity: '0', transform: 'translateY(-12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideLeft: {
          '0%':   { opacity: '0', transform: 'translateX(-12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        slideRight: {
          '0%':   { opacity: '0', transform: 'translateX(12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        scaleIn: {
          '0%':   { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
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
        rotateBeam: {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        shine: {
          '0%':   { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        scanlineMove: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        staggerIn: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      // ── Cyber Glow Box Shadows ──────────────────────────────────────────
      boxShadow: {
        'glow-primary': '0 0 25px -2px rgba(14, 165, 233, 0.45), 0 0 10px -1px rgba(14, 165, 233, 0.3)',
        'glow-cyan':    '0 0 25px -2px rgba(6, 182, 212, 0.45), 0 0 10px -1px rgba(6, 182, 212, 0.3)',
        'glow-emerald': '0 0 25px -2px rgba(16, 185, 129, 0.45), 0 0 10px -1px rgba(16, 185, 129, 0.3)',
        'glow-crimson': '0 0 25px -2px rgba(239, 68, 68, 0.45), 0 0 10px -1px rgba(239, 68, 68, 0.3)',
        'glow-amber':   '0 0 25px -2px rgba(245, 158, 11, 0.45), 0 0 10px -1px rgba(245, 158, 11, 0.3)',
        'glow-gold':    '0 0 25px -2px rgba(201, 171, 110, 0.45), 0 0 10px -1px rgba(201, 171, 110, 0.3)',
        'card': '0 10px 40px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
        'nav': '0 8px 32px -8px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        'lift': '0 20px 50px -12px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(56, 189, 248, 0.12)',
      },
      // ── Glassmorphism ──────────────────────────────────────────────────
      backdropBlur: {
        xs: '2px',
      },
      backgroundImage: {
        'cyber-grid': 'linear-gradient(rgba(14, 165, 233, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(14, 165, 233, 0.03) 1px, transparent 1px)',
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      spacing: {
        'section': '2rem',
        'chapter': '3rem',
        '18': '4.5rem',
        '22': '5.5rem',
      },
      borderRadius: {
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      zIndex: {
        'base': '0',
        'raised': '10',
        'sticky': '20',
        'nav': '40',
        'sidebar': '50',
        'overlay': '100',
        'toast': '200',
        'modal': '300',
        'tooltip': '400',
      },
      transitionDuration: {
        'instant': '80ms',
        'fast': '150ms',
        'base': '200ms',
        'slow': '300ms',
        'route': '200ms',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [],
}
