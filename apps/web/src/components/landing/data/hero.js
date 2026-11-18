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
 * The hero copy and its measurement footnote.
 */
export const HERO = {
  headline: ['Every claim,', 'checked against', 'its evidence.'],
  lede:
    'TrustRAG splits an answer into atomic claims, verifies each one against the cited corpus with natural-language inference, and re-runs the retrieval when confidence falls short — before a hallucination reaches the user.',
  note: {
    text: 'Retrieval recall@K of 0.963, measured on the current 33-probe ground truth (27 answerable + 6 unanswerable).',
    href: 'https://github.com/MaithreshVaddi-27/TrustRAG/blob/main/docs/evaluation/methodology.md',
    linkText: 'Read the methodology',
  },
}

/**
 * Two claims taken from two measured runs.
 *
 * The first is claim five of q012 in the frozen 27-query reliability baseline
 * (config 1.29, gemma3:1b + CRAFT). The second is the contradicted claim of
 * q011 in the same frozen baseline run under the MLX model (config 1.28).
 *
 * The document reference and the SHA-256 root hash are the real ones,
 * recorded at ingestion from
 * `apps/api/tests/eval/fixtures/corpus/`. The retrieval score is the real
 * score that segment carried in that run.
 */
export const HERO_RECORDS = [
  {
    index: 'q012 · claim 5 of 5',
    claim: 'Default request rate limit: 50 requests per second per tenant',
    citation: 'limits-2025.txt · chunk 0 · retrieval 0.670',
    hash: '9dccc0bfdbfa9f19…2a9b9ab5',
    status: 'supported',
    metric: { label: 'retrieval', value: '0.670' },
    sealed: true,
  },
  {
    index: 'mlx q011 · claim 1 of 1',
    claim: 'Default token lifetime is 14 days',
    citation: 'service-api.md · chunk 0 · retrieval 0.712',
    hash: '726570e5475034a4…61b6b5d',
    status: 'contradicted',
    metric: { label: 'retrieval', value: '0.712' },
    conflict:
      'The context states that the default token lifetime in 2025 is 14 days in the ‘limits-2025.txt’ segment, but the ‘service-api.md’ segment specifies a default token lifetime of 30 days. Since the claim asserts a default token lifetime of 14 days, and the service API specifies 30 days, the claim is contradicted by the most current and specific context.',
    sealed: true,
  },
]
