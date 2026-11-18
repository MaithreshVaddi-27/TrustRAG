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
 * The closing statement.
 */
export const CTA = {
  headline: 'Put a claim checker in front of your answers.',
  lede:
    'Deploy a knowledge base, audit what the model claims, and recover the answers that do not hold up — before a reader finds the gap.',
}
