/**
 * TrustRAG — landing page content.
 *
 * Every string on the marketing page lives here so the components stay
 * presentational and the copy can be reviewed in one place.
 *
 * Split by section. Each module owns one export; `data/index.js` re-exports
 * them for the components that want a single import.
 *
 * Benchmark figures carry their provenance in the `note` field. TrustRAG's
 * own numbers are measured on the internal reliability fixture documented in
 * `docs/evaluation/`; competitor figures are published literature values.
 * Do not add a number without a source.
 */

/**
 * Navigation links for the landing header.
 *
 * Each id is the anchor of a section that exists on the page.
 */
export const NAV_LINKS = [
  { id: 'pipeline', label: 'Pipeline' },
  { id: 'simulation', label: 'Runs' },
  { id: 'capabilities', label: 'Capabilities' },
  { id: 'benchmarks', label: 'Benchmarks' },
  { id: 'compare', label: 'Comparison' },
]
