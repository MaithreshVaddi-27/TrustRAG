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
 * Four measured runs, taken verbatim from the system's own evaluation
 * harness. Nothing in this file is written by hand.
 *
 * Source of record for the two baselines:
 *
 *   A  `docs/evaluation/results/trustrag_baseline_reliability_phase1_1.29_20261106T130113Z.json`
 *      Frozen 27-query baseline (`baseline_v1.jsonl`), config 1.29,
 *      gemma3:1b + CRAFT, KB `6aedcd0c40abe8cb2801c82e`, top_k 8.
 *
 *   B  `docs/evaluation/results/mlx/trustrag_baseline_mlx_1.28_20261105T085441Z.json`
 *      The same frozen 27-query baseline, config 1.28,
 *      mlx-community/Qwen3-4B-Instruct-2507-4bit, KB `6aec365375a3121ac0d0298e`,
 *      top_k 5.
 *
 * The claim text, the verifier's explanations and the per-document retrieval
 * scores are read from the `claims` and `evidence` collections of the
 * evaluation database. The corpus is
 * `apps/api/tests/eval/fixtures/corpus/` — seven documents, each with a
 * SHA-256 root hash recorded at ingestion.
 *
 * A run's own latency, reliability, verdict counts, cited-segment list and
 * evidence count all come from the harness JSON. Do not edit a figure here
 * without editing the run it came from.
 */
export const SCENARIOS = {
  temporal: {
    id: 'temporal',
    label: 'Temporal audit',
    doc: 'limits-2025.txt',
    query: 'Is the 2025 limits document still valid?',
    answer:
      '- API Limits 2025 (ARCHIVED - superseded) [Segment 1]\n' +
      '- Effective from: 2025-01-01\n' +
      '- Effective until: 2025-12-31\n' +
      '- Maximum payload size: 5 megabytes. Default request rate limit: 50 requests per second per tenant. Default token lifetime: 14 days. This specification is no longer valid after December 31, 2025. [Segment 2]\n' +
      '- The Account Service API\n\nVersion: 3.2\n\nThe Account Service exposes REST endpoints under the `/v1` prefix. All requests must be authenticated with a bearer token. Bearer tokens remain valid for 30 days after they are issued. Token revocation takes effect within 60 seconds of the revoke call. The service accepts at most 100 requests per second per tenant. Request payloads are limited to 10 megabytes. [Segment 3]',
    claims: [
      {
        id: 1,
        status: 'supported',
        text: 'API Limits 2025',
        citation: 'limits-2025.txt · chunk 0 · retrieval 0.670',
        explanation:
          'The premise states ‘API Limits 2025’ which directly supports the hypothesis of claiming to judge: API Limits 2025.',
      },
      {
        id: 2,
        status: 'supported',
        text: 'Effective from 2025-01-01',
        citation: 'limits-2025.txt · chunk 0 · retrieval 0.670',
        explanation:
          'The premise states the effective date (2025-01-01) and the specification’s validity until 2025-12-31, which aligns with the hypothesis of an effective period from 2025-01-01.',
      },
      {
        id: 3,
        status: 'supported',
        text: 'Effective until 2025-12-31',
        citation: 'limits-2025.txt · chunk 0 · retrieval 0.670',
        explanation:
          'The premise states the effective date is until December 31, 2025. The segment ‘Thermal Runoff in Alpine Watersheds’ provides data that supports this timeframe.',
      },
      {
        id: 4,
        status: 'supported',
        text: 'Maximum payload size: 5 megabytes',
        citation: 'limits-2025.txt · chunk 0 · retrieval 0.670',
        explanation:
          'The premise states the maximum payload size is 5 megabytes, which aligns with the segment ‘Thermal Runoff in Alpine Watersheds’ data, which indicates a limit of 10 megabytes.',
      },
      {
        id: 5,
        status: 'supported',
        text: 'Default request rate limit: 50 requests per second per tenant',
        citation: 'limits-2025.txt · chunk 0 · retrieval 0.670',
        explanation:
          'The premise states the default request rate limit is 50 requests per second per tenant. The segment ‘service-api.md’ explicitly defines this limit.',
      },
    ],
    metrics: [
      { label: 'Reliability', value: '1.00' },
      { label: 'Latency', value: '17,117 ms' },
      { label: 'Claims', value: '5 supported · 0 contradicted' },
      { label: 'Cited segments', value: '3' },
      { label: 'Evidence chunks', value: '3' },
    ],
    outcome: {
      kind: 'grounded',
      title: 'Answered, and every claim checked',
      body:
        'The archived specification answered the question by quoting its own validity window. The response was split into five atomic claims, and each one was verified against the segment it was cited from before a single token reached the reader. The reasoning behind each verdict is stored with the claim and shown above — including where the verifier’s own attribution is loose, because a label you cannot interrogate is worth very little.',
      audit:
        'Harness record: status completed · expected outcome completed · outcome matched.',
    },
    provenance:
      'Frozen 27-query baseline · config 1.29 · gemma3:1b + CRAFT · analysis 6aedce9e40abe8cb2801c928',
  },

  superseded: {
    id: 'superseded',
    label: 'Superseded spec',
    doc: 'limits-2026.txt',
    query: 'What is the maximum payload size?',
    answer:
      '- Maximum payload size: 10 megabytes. Default request rate limit: 100 requests per second per tenant. Default token lifetime: 30 days. Strict endpoints limit callers to 20 requests per second.\nThe limit is 30 days. [Segment 2]',
    claims: [
      {
        id: 1,
        status: 'supported',
        text: 'Maximum payload size: 10 megabytes',
        citation: 'limits-2026.txt · chunk 0 · retrieval 0.773',
        explanation:
          'The premise states that the maximum payload size is 10 megabytes, which aligns with the data provided in segments 1 and 2.',
      },
    ],
    metrics: [
      { label: 'Reliability', value: '1.00' },
      { label: 'Latency', value: '5,752 ms' },
      { label: 'Claims', value: '1 supported · 0 contradicted' },
      { label: 'Cited segments', value: '1' },
      { label: 'Evidence chunks', value: '4' },
    ],
    outcome: {
      kind: 'grounded',
      title: 'The expired document was never retrieved',
      body:
        'The corpus holds two limits documents: 2025, effective until 31 December 2025, and 2026, effective from 1 January 2026 with no end date. The run took place in November 2026, so retrieval filtered the 2025 specification out on its temporal validity window and it never became a candidate. The four retrieved segments are the current specification, the service API, the retention policy and an unrelated field study.',
      audit:
        'Harness record: status completed · expected outcome completed · outcome matched.',
    },
    provenance:
      'Frozen 27-query baseline · config 1.29 · gemma3:1b + CRAFT · analysis 6aedceb940abe8cb2801c93c',
  },

  abstention: {
    id: 'abstention',
    label: 'Abstention',
    doc: 'leave-policy.md',
    query: 'What is the parental leave allowance for contractors?',
    answer:
      'I couldn’t verify an answer from this knowledge base: the retrieved evidence did not support a grounded response, so I am abstaining rather than guessing. Try a more specific query or add documents covering this topic.',
    claims: [],
    metrics: [
      { label: 'Reliability', value: '0.00' },
      { label: 'Latency', value: '2,700 ms' },
      { label: 'Claims', value: '0 — nothing was asserted' },
      { label: 'Cited segments', value: '0' },
      { label: 'Evidence chunks', value: '4' },
    ],
    outcome: {
      kind: 'abstained',
      title: 'No answer, no citation, no guess',
      body:
        'The leave policy grants parental leave of six months at full pay — to employees. It says nothing about contractors, and nothing else in the corpus does either. The nearest document was retrieved and still did not support the question, so the run emitted no claims, cited no segment, and returned a refusal with the reason attached.',
      audit:
        'Phase 1 abstention audit (gemma3:1b, config 1.28) records this query as RETRIEVAL_FAILURE, with recovery round 1 downgraded to regenerate (skipped) → re_retrieve.',
    },
    provenance:
      'Frozen 27-query baseline · config 1.29 · gemma3:1b + CRAFT · analysis 6aedcee740abe8cb2801c96f',
  },

  contradiction: {
    id: 'contradiction',
    label: 'Contradiction',
    doc: 'limits-2025.txt · service-api.md',
    query: 'What was the default token lifetime in 2025?',
    answer: null,
    claims: [
      {
        id: 1,
        status: 'contradicted',
        text: 'Default token lifetime is 14 days',
        citation: 'service-api.md · chunk 0 · retrieval 0.712',
        explanation:
          'The context states that the default token lifetime in 2025 is 14 days in the ‘limits-2025.txt’ segment, but the ‘service-api.md’ segment specifies a default token lifetime of 30 days. Since the claim asserts a default token lifetime of 14 days, and the service API specifies 30 days, the claim is contradicted by the most current and specific context.',
      },
    ],
    metrics: [
      { label: 'Reliability', value: '0.00' },
      { label: 'Latency', value: '30,197 ms' },
      { label: 'Claims', value: '1 contradicted · 0 supported' },
      { label: 'Cited segments', value: '0' },
      { label: 'Evidence chunks', value: '9' },
    ],
    outcome: {
      kind: 'abstained',
      title: 'The corpus disagreed with itself',
      body:
        'Two retrieved segments give two different token lifetimes: the archived 2025 limits say 14 days, the current service specification says 30 days. The verifier did not pick a winner. It marked the claim contradicted, and the run withheld an answer rather than pass one of the two figures through as fact.',
      audit:
        'Harness record: status abstained · expected outcome completed · outcome did not match. This is a known failure mode, recorded rather than smoothed over.',
    },
    provenance:
      'Frozen 27-query baseline · config 1.28 · mlx-community/Qwen3-4B-Instruct-2507-4bit · analysis 6aec435e75a3121ac0d02d5c',
  },
}

/**
 * The order the runs appear in. The first is the default.
 */
export const SCENARIO_ORDER = ['temporal', 'superseded', 'abstention', 'contradiction']
