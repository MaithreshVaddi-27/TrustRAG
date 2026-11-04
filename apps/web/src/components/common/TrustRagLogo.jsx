import { memo } from 'react'
import { motion } from 'motion/react'
import { clsx } from 'clsx'

/**
 * TrustRagLogo — Premium, art-directed brand mark for TrustRAG.
 *
 * Design Architecture:
 * 1. Shield of Trust: High-integrity perimeter representing factuality & anti-hallucination.
 * 2. Dual-Stream Convergence: Left wing (Sparse BM25) and Right wing (Dense Vector) converging
 *    into ground truth via Reciprocal Rank Fusion.
 * 3. Architectural "T" Monogram: Razor-sharp central anchor representing Trust & Entailment.
 * 4. Calibrated Truth Core: Central illuminated diamond node symbolizing verified entailment.
 *
 * Available in standalone emblem, framed squircle badge, or complete wordmark lockup.
 */
export const TrustRagEmblem = memo(function TrustRagEmblem({
  size = 32,
  className = '',
  framed = true,
  glow = true,
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={clsx('shrink-0 select-none', className)}
      aria-label="TrustRAG Emblem"
    >
      <defs>
        {/* Obsidian Glass Foundation */}
        <linearGradient id="trObsidianBase" x1="2" y1="2" x2="30" y2="30" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0b1728" />
          <stop offset="45%" stopColor="#050b14" />
          <stop offset="100%" stopColor="#02050a" />
        </linearGradient>

        {/* Specular Edge Precision Highlight */}
        <linearGradient id="trBorderHighlight" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.75" />
          <stop offset="50%" stopColor="#06b6d4" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#0284c7" stopOpacity="0.1" />
        </linearGradient>

        {/* Sparse Retrieval Stream (Cyan) */}
        <linearGradient id="trStreamLeft" x1="6" y1="8" x2="16" y2="25" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="60%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#0284c7" />
        </linearGradient>

        {/* Dense Semantic Stream (Sky / Primary) */}
        <linearGradient id="trStreamRight" x1="26" y1="8" x2="16" y2="25" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="60%" stopColor="#0284c7" />
          <stop offset="100%" stopColor="#1d4ed8" />
        </linearGradient>

        {/* Central Monogram 'T' Core */}
        <linearGradient id="trPillarGrad" x1="16" y1="6" x2="16" y2="21" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="60%" stopColor="#e0f2fe" />
          <stop offset="100%" stopColor="#38bdf8" />
        </linearGradient>

        {/* Specular Inner Glare */}
        <linearGradient id="trInnerGleam" x1="16" y1="6" x2="16" y2="12" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>

        {/* Ambient Calibrated Glow Filter */}
        <filter id="trGlow" x="-25%" y="-25%" width="150%" height="150%">
          <feDropShadow dx="0" dy="1" stdDeviation="1.5" floodColor="#06b6d4" floodOpacity="0.45" />
        </filter>
      </defs>

      {/* Framed Squircle Container */}
      {framed && (
        <>
          <rect
            x="1.5"
            y="1.5"
            width="29"
            height="29"
            rx="8"
            fill="url(#trObsidianBase)"
          />
          <rect
            x="1.5"
            y="1.5"
            width="29"
            height="29"
            rx="8"
            stroke="url(#trBorderHighlight)"
            strokeWidth="1.2"
          />
        </>
      )}

      {/* Ambient Core Light Radial */}
      {glow && (
        <circle
          cx="16"
          cy="15"
          r="6.5"
          fill="#06b6d4"
          fillOpacity="0.12"
          className="animate-pulse"
        />
      )}

      {/* Left Shield Wing: Sparse BM25 Keyword Stream */}
      <path
        d="M 6.5 13.5 C 6.5 18.2 10 22.8 15 25.2 L 15 22.2 C 11.2 20.2 8.8 16.8 8.8 13.5 Z"
        fill="url(#trStreamLeft)"
      />

      {/* Right Shield Wing: Dense ONNX Semantic Stream */}
      <path
        d="M 25.5 13.5 C 25.5 18.2 22 22.8 17 25.2 L 17 22.2 C 20.8 20.2 23.2 16.8 23.2 13.5 Z"
        fill="url(#trStreamRight)"
      />

      {/* Precision Trust "T" Monogram & Horizontal Crossbeam */}
      <g filter="url(#trGlow)">
        {/* Top Crossbar */}
        <path
          d="M 7.5 8 C 7.5 7.4 8 7 8.6 7 L 23.4 7 C 24 7 24.5 7.4 24.5 8 L 24.5 10 C 24.5 10.6 24 11 23.4 11 L 18 11 L 18 19.5 C 18 20.3 17.2 21 16.4 21 L 15.6 21 C 14.8 21 14 20.3 14 19.5 L 14 11 L 8.6 11 C 8 11 7.5 10.6 7.5 10 Z"
          fill="url(#trPillarGrad)"
        />

        {/* Top Glare Edge */}
        <line
          x1="9"
          y1="8"
          x2="23"
          y2="8"
          stroke="url(#trInnerGleam)"
          strokeWidth="0.8"
          strokeLinecap="round"
        />
      </g>

      {/* Calibrated Entailment Truth Core: Central Diamond Node */}
      <polygon
        points="16,21.5 18.2,23.8 16,26.1 13.8,23.8"
        fill="#22d3ee"
      />
      <circle cx="16" cy="23.8" r="0.75" fill="#ffffff" />
    </svg>
  )
})

/**
 * TrustRagLogo — Full brand lockup with emblem + typography.
 */
export const TrustRagLogo = memo(function TrustRagLogo({
  size = 'md', // 'sm' | 'md' | 'lg' | 'xl'
  showSubtitle = true,
  className = '',
  emblemOnly = false,
}) {
  const pixelSizes = {
    sm: 24,
    md: 32,
    lg: 40,
    xl: 56,
  }

  const px = pixelSizes[size] || 32

  return (
    <div className={clsx('flex items-center gap-2.5 select-none', className)}>
      <motion.div
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.96 }}
        className="shrink-0 cursor-pointer"
      >
        <TrustRagEmblem size={px} framed={true} glow={true} />
      </motion.div>

      {!emblemOnly && (
        <div className="flex flex-col leading-none">
          <div className="flex items-center">
            <span className={clsx(
              'font-extrabold tracking-tight text-white flex items-center',
              size === 'sm' && 'text-xs',
              size === 'md' && 'text-sm sm:text-base',
              size === 'lg' && 'text-lg sm:text-xl',
              size === 'xl' && 'text-2xl',
            )}>
              TRUST<span className="text-cyan-400">RAG</span>
            </span>
          </div>

          {showSubtitle && (
            <span className={clsx(
              'font-mono text-slate-500 uppercase tracking-widest mt-0.5',
              size === 'sm' && 'text-[8px]',
              size === 'md' && 'text-[9px] sm:text-[10px]',
              size === 'lg' && 'text-[10px] sm:text-[11px]',
              size === 'xl' && 'text-xs',
            )}>
              Reliability Workbench
            </span>
          )}
        </div>
      )}
    </div>
  )
})
