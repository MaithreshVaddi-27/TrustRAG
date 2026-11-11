/**
 * TrustRAG — chart theme.
 *
 * Recharts needs concrete colours, so it cannot read the CSS custom
 * properties directly. These values mirror
 * `src/styles/tokens/color.css` — keep them in step.
 *
 * The rule that matters: a chart has ONE accent. The series that matters
 * gets Chrome Silver; everything else sits in quiet steps of the same
 * neutral ramp. Contradicted is the only series that may carry crimson,
 * because a contradicted claim is the only thing in this product that is
 * genuinely an alarm.
 */

export const CHART = {
  /* The neutral ramp */
  silverBright: '#f7f7f6', // silver-050
  silver: '#cdcbcA', // silver-300 — Chrome Silver
  silverMuted: '#a3a2a0', // silver-400
  silverDim: '#8a8987', // silver-500
  silverFaint: '#3a3a3c', // graphite-500

  /* The alarm */
  crimson: '#d41514', // crimson-500 — Laser Crimson
  crimsonLight: '#f04a48', // crimson-400

  /* Chrome */
  grid: 'rgba(205, 203, 202, 0.07)',
  rule: 'rgba(205, 203, 202, 0.16)',
  axis: '#8a8987',
  surface: '#141416',
  surfaceRaised: '#0c0c0d',
  text: '#e9e9e7',
  textMuted: '#8a8987',
}

/** Verdict series colours, in the order the charts present them. */
export const VERDICT_COLORS = {
  supported: CHART.silver,
  neutral: CHART.silverDim,
  contradicted: CHART.crimson,
}

/** The tooltip surface, matching the design system's panels. */
export const tooltipStyle = {
  backgroundColor: CHART.surface,
  border: `1px solid ${CHART.rule}`,
  borderRadius: 10,
  fontSize: 12,
  color: CHART.text,
  padding: '8px 12px',
  boxShadow: 'none',
}

export const tooltipLabelStyle = {
  color: CHART.textMuted,
  fontSize: 11,
  fontFamily: 'var(--typeface-mono)',
}

/** Shared axis props so every chart in the product is drawn the same way. */
export const axisProps = {
  stroke: CHART.axis,
  fontSize: 11,
  tickLine: false,
  axisLine: false,
}
