/** @type {import('tailwindcss').Config} */

/**
 * TrustRAG — Obsidian Black × Chrome Silver × Laser Crimson.
 *
 * The palette is deliberately near-monochrome. Chrome Silver carries the
 * interface and the single accent; Laser Crimson is an alarm and appears
 * only where a claim has failed, a verification seal is stamped, or focus
 * lands.
 *
 * This file is the build-layer mirror of `src/styles/tokens/`. Raw values
 * live in the token stylesheets; change them there and here together.
 */

/** Chrome Silver — the neutral ramp and the single accent. */
const silver = {
  50: '#f7f7f6',
  100: '#e9e9e7',
  200: '#d8d7d5',
  300: '#cdcbcA', // Chrome Silver
  400: '#a3a2a0',
  500: '#8a8987',
  600: '#5a5957',
  700: '#3d3d3c',
  800: '#26262a',
  900: '#16161a',
  950: '#0c0c0d',
}

/** Graphite — structure, dividers, inactive strokes. */
const graphite = {
  300: '#5a5957',
  400: '#4a4a49',
  500: '#3a3a3c',
  600: '#2e2e33',
  700: '#232327',
  800: '#1a1a1d',
  900: '#141416',
}

/** Obsidian — the substrate. */
const obsidian = {
  800: '#141416',
  850: '#101012',
  900: '#0c0c0d',
  950: '#080808', // Obsidian Black
}

/** Laser Crimson — the alarm. Never decorative. */
const crimson = {
  300: '#f26a68',
  400: '#f04a48', // focus ring
  500: '#d41514', // Laser Crimson
  600: '#a81010',
  700: '#7a0c0c',
  950: '#1a0707',
}

export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ── The new system ──────────────────────────────────────────────
        silver,
        graphite,
        obsidian,
        crimson,

        // ── Mapped families ─────────────────────────────────────────────
        // The product was cyan-on-slate. Those families now resolve into
        // the silver ramp so the whole interface shares one neutral voice.
        primary: silver,
        cyan: silver,
        cyber: graphite,

        // Surface is the substrate: Obsidian.
        surface: {
          50: silver[50],
          100: silver[100],
          700: graphite[700],
          800: obsidian[800],
          850: obsidian[850],
          900: obsidian[900],
          950: obsidian[950],
        },

        // Slate is the interface text ramp. The 500/600 inversion is
        // deliberate and preserved from the original config: Tailwind's
        // default 600 (#475569) fails AA on obsidian surfaces, so the scale
        // order is sacrificed for contrast.
        slate: {
          50: silver[50],
          100: silver[100],
          200: silver[200],
          300: silver[300],
          400: silver[400],
          500: silver[500],
          600: silver[400],
          700: silver[700],
          800: silver[800],
          900: silver[900],
          950: silver[950],
        },

        // ── Verdict states ──────────────────────────────────────────────
        // Monochrome family plus one alarm. A failed claim is the only
        // thing that gets colour.
        verified: silver[200],
        contradicted: crimson[400],
        unsupported: silver[400],
        unknown: silver[600],

        trust: {
          high: silver[200],
          medium: silver[400],
          low: crimson[400],
        },

        // The champagne accent is retired — it is now a step in silver.
        gold: {
          300: silver[200],
          400: silver[300],
          500: silver[400],
        },
      },

      // ── Typography ─────────────────────────────────────────────────────
      fontFamily: {
        sans: [
          'system-ui',
          '-apple-system',
          'SF Pro Text',
          'Helvetica Neue',
          'Segoe UI',
          'Roboto',
          'Arial',
          'sans-serif',
        ],
        // Didot / Bodoni 72 — a Didone, the luxury editorial voice. System
        // faces only, so the product stays air-gapped.
        display: [
          'Didot',
          'Bodoni 72',
          'Bodoni 72 Oldstyle',
          'Playfair Display',
          'Times New Roman',
          'serif',
        ],
        mono: [
          'ui-monospace',
          'SF Mono',
          'SFMono-Regular',
          'JetBrains Mono',
          'Menlo',
          'Consolas',
          'monospace',
        ],
      },

      fontSize: {
        display: [
          'clamp(2.75rem, 6vw, 5.25rem)',
          { lineHeight: '1.02', letterSpacing: '-0.03em', fontWeight: '400' },
        ],
        'display-sm': [
          'clamp(2rem, 4vw, 3.25rem)',
          { lineHeight: '1.06', letterSpacing: '-0.025em', fontWeight: '400' },
        ],
        'heading-1': [
          'clamp(1.75rem, 3vw, 2.5rem)',
          { lineHeight: '1.14', letterSpacing: '-0.02em', fontWeight: '400' },
        ],
        'heading-2': [
          'clamp(1.375rem, 2vw, 1.875rem)',
          { lineHeight: '1.2', letterSpacing: '-0.015em', fontWeight: '400' },
        ],
        'heading-3': [
          '1.25rem',
          { lineHeight: '1.3', letterSpacing: '-0.01em', fontWeight: '500' },
        ],
        'body-lg': ['1.125rem', { lineHeight: '1.62', letterSpacing: '0' }],
        body: ['1rem', { lineHeight: '1.65', letterSpacing: '0' }],
        'body-sm': ['0.875rem', { lineHeight: '1.6', letterSpacing: '0' }],
        caption: ['0.8125rem', { lineHeight: '1.45', letterSpacing: '0.005em', fontWeight: '500' }],
        'mono-xs': [
          '0.75rem',
          { lineHeight: '1.45', letterSpacing: '0.01em', fontFamily: 'var(--typeface-mono)' },
        ],
        'mono-sm': [
          '0.8125rem',
          { lineHeight: '1.45', letterSpacing: '0.01em', fontFamily: 'var(--typeface-mono)' },
        ],
        'mono-base': [
          '0.875rem',
          { lineHeight: '1.55', letterSpacing: '0.01em', fontFamily: 'var(--typeface-mono)' },
        ],
      },

      // ── Animation & micro-effects ──────────────────────────────────────
      // Only motion that explains something survives. The decorative loops
      // (shimmer, radar sweep, halo pulse, rotating beam) are gone.
      animation: {
        'fade-in': 'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-down': 'slideDown 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-left': 'slideLeft 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-right': 'slideRight 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 4s linear infinite',
        float: 'float 5s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideLeft: {
          '0%': { opacity: '0', transform: 'translateX(-12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        slideRight: {
          '0%': { opacity: '0', transform: 'translateX(12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
      },

      // ── Elevation ──────────────────────────────────────────────────────
      // Depth on a dark theme comes from surface steps and hairlines, not
      // from shadows. The neutral shadows below are what remains.
      boxShadow: {
        none: 'none',
        sm: '0 1px 2px rgba(0, 0, 0, 0.4)',
        md: '0 4px 12px rgba(0, 0, 0, 0.5)',
        lg: '0 12px 32px rgba(0, 0, 0, 0.6)',
        xl: '0 24px 64px rgba(0, 0, 0, 0.7)',
        '2xl': '0 32px 80px rgba(0, 0, 0, 0.75)',
        inner: 'inset 0 2px 4px rgba(0, 0, 0, 0.4)',
        // The hairline-inset shadows the glass surfaces used to rely on.
        card: '0 1px 0 rgba(205, 203, 202, 0.04) inset',
        nav: '0 1px 0 rgba(205, 203, 202, 0.05) inset',
        lift: '0 32px 64px -32px rgba(0, 0, 0, 0.9)',
        // Retired: coloured glows. Kept as keys so existing class names
        // resolve, but they no longer emit colour.
        'glow-primary': 'none',
        'glow-cyan': 'none',
        'glow-emerald': 'none',
        'glow-crimson': 'none',
        'glow-amber': 'none',
        'glow-gold': 'none',
      },

      backdropBlur: {
        xs: '2px',
      },

      backgroundImage: {
        'cyber-grid':
          'linear-gradient(rgba(205, 203, 202, 0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(205, 203, 202, 0.018) 1px, transparent 1px)',
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
      backgroundSize: {
        grid: '40px 40px',
      },

      spacing: {
        section: '2rem',
        chapter: '3rem',
        18: '4.5rem',
        22: '5.5rem',
      },

      borderRadius: {
        '2xl': '1.5rem',
        '3xl': '2rem',
      },

      zIndex: {
        base: '0',
        raised: '10',
        sticky: '20',
        nav: '40',
        sidebar: '50',
        overlay: '100',
        toast: '200',
        modal: '300',
        tooltip: '400',
      },

      transitionDuration: {
        instant: '80ms',
        fast: '150ms',
        base: '220ms',
        slow: '320ms',
        route: '220ms',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [],
}
