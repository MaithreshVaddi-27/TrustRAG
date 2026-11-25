/**
 * TrustRAG — chart theme.
 *
 * The SVG charts need concrete colour strings, so they cannot read CSS
 * custom properties directly. These values mirror
 * `src/styles/tokens/color.css`; `npm run check:tokens` fails on drift.
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
  silver: '#cdcbca', // silver-300 — Chrome Silver
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
