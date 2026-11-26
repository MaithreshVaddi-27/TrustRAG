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
 * The benchmark sets.
 */
export const BENCHMARK_TABS = [
  { id: 'accuracy', label: 'Grounding' },
  { id: 'speed', label: 'Latency' },
  { id: 'coverage', label: 'Coverage' },
]

/**
 * The measured tables.
 *
 * Every figure below is read from one run of the evaluation harness:
 *
 *   docs/evaluation/results/trustrag_baseline_reliability_phase1_1.29_20261106T130113Z.json
 *
 * That run is the frozen 27-query baseline (`baseline_v1.jsonl`), config
 * 1.29, gemma3:1b + CRAFT, against the isolated fixture KB
 * `6aedcd0c40abe8cb2801c82e`, at top_k 8. There are no competitor figures
 * here: every number is ours, and the caption says so.
 */
const SOURCE =
  'Frozen 27-query reliability baseline (baseline_v1.jsonl) · config 1.29 · gemma3:1b + CRAFT · top_k 8 · KB 6aedcd0c40abe8cb2801c82e.'

const METHODOLOGY = {
  href: 'https://github.com/MaithreshVaddi-27/TrustRAG/blob/main/docs/evaluation/methodology.md',
  linkText: 'Read the methodology',
}

export const BENCHMARKS = {
  accuracy: {
    id: 'accuracy',
    title: 'Retrieval quality against the frozen fixture',
    desc:
      'How well the retriever placed the gold evidence for each of the 27 queries, and how much of the retrieved corpus actually carried a usable claim.',
    note: `${SOURCE} Raw run JSON: docs/evaluation/results/trustrag_baseline_reliability_phase1_1.29_20261106T130113Z.json.`,
    link: METHODOLOGY,
    lowerIsBetter: false,
    metrics: [
      {
        label: 'Recall@8',
        value: 88.9,
        suffix: '%',
        width: '88.9%',
        lead: true,
        note: '24 of 27 queries',
      },
      {
        label: 'Hit rate@8',
        value: 88.9,
        suffix: '%',
        width: '88.9%',
        note: '24 of 27 queries',
      },
      {
        label: 'MRR@8',
        value: 88.9,
        suffix: '%',
        width: '88.9%',
        note: 'Same set',
      },
      {
        label: 'nDCG@8',
        value: 88.9,
        suffix: '%',
        width: '88.9%',
        note: 'Same set',
      },
      {
        label: 'Snippet recall',
        value: 85.2,
        suffix: '%',
        width: '85.2%',
        note: 'Within the gold span',
      },
      {
        label: 'Evidence coverage',
        value: 74.1,
        suffix: '%',
        width: '74.1%',
        note: 'Mean across 27 queries',
      },
      {
        label: 'Citation correctness',
        value: 100,
        suffix: '%',
        width: '100%',
        note: '15 citations checked',
      },
    ],
  },
  speed: {
    id: 'speed',
    title: 'End-to-end latency per query',
    desc:
      'The whole loop: retrieval, generation, claim decomposition, the NLI audit, and any recovery it triggered. Longer bars are slower.',
    note: `${SOURCE} Latency is wall-clock per query, measured by the harness across all 27 queries.`,
    link: METHODOLOGY,
    lowerIsBetter: true,
    metrics: [
      {
        label: 'Fastest query',
        value: 2581,
        suffix: ' ms',
        width: '13.7%',
        note: 'minimum',
      },
      {
        label: 'Median query',
        value: 5145,
        suffix: ' ms',
        width: '27.4%',
        lead: true,
        note: 'p50',
      },
      {
        label: '95th percentile',
        value: 15903,
        suffix: ' ms',
        width: '84.6%',
        note: 'p95',
      },
      {
        label: 'Slowest query',
        value: 18809,
        suffix: ' ms',
        width: '100%',
        note: 'maximum',
      },
    ],
  },
  coverage: {
    id: 'coverage',
    title: 'Outcome match by query class',
    desc:
      'The share of queries whose outcome matched the one the dataset expected — answered where an answer existed, withheld where the evidence did not support one.',
    note: `${SOURCE} Each class is scored against the expected outcome recorded in the dataset, not against a human judgement.`,
    link: METHODOLOGY,
    lowerIsBetter: false,
    metrics: [
      {
        label: 'All classes',
        value: 85.2,
        suffix: '%',
        width: '85.2%',
        lead: true,
        note: '23 of 27 queries',
      },
      {
        label: 'Temporal',
        value: 100,
        suffix: '%',
        width: '100%',
        note: '3 of 3 queries',
      },
      {
        label: 'Conflicting',
        value: 100,
        suffix: '%',
        width: '100%',
        note: '3 of 3 queries',
      },
      {
        label: 'Missing evidence',
        value: 100,
        suffix: '%',
        width: '100%',
        note: '2 of 2 queries',
      },
      {
        label: 'Adversarial',
        value: 80,
        suffix: '%',
        width: '80%',
        note: '4 of 5 queries',
      },
      {
        label: 'Factual',
        value: 78.6,
        suffix: '%',
        width: '78.6%',
        note: '11 of 14 queries',
      },
    ],
  },
}
