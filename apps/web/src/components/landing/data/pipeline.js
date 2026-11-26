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

import {
  Brain,
  Lock,
  RefreshCw,
  ScanText,
  ShieldCheck,
  Terminal,
} from 'lucide-react'

/**
 * The six stages of the closed loop.
 *
 * The first three run before the answer exists; the last three run after it
 * does. The verifier is natural-language inference against the cited
 * segments — `app/rag/verification/pipeline/nli.py`, served by the local
 * `ollama/gemma3:1b` model configured in `apps/api/config/models.yaml`.
 */
export const PIPELINE_STAGES = [
  {
    id: 'ingest',
    icon: Terminal,
    name: 'Ingest',
    desc: 'Documents are parsed, chunked, hashed to a SHA-256 root, and dated with their effective window.',
  },
  {
    id: 'retrieve',
    icon: RefreshCw,
    name: 'Hybrid RRF',
    desc: 'Dense vectors and BM25 are fused by reciprocal rank. Both branches must succeed or the retrieval fails.',
  },
  {
    id: 'decompose',
    icon: ScanText,
    name: 'Decompose',
    desc: 'The response is split into atomic propositional claims before any citation is aligned.',
  },
  {
    id: 'verify',
    icon: ShieldCheck,
    name: 'NLI audit',
    desc: 'Each claim is checked against its cited segment by natural-language inference, and the reasoning is stored.',
  },
  {
    id: 'heal',
    icon: Brain,
    name: 'Self-heal',
    desc: 'Below the reliability threshold the graph rewrites the query and re-retrieves, for at most two attempts.',
  },
  {
    id: 'ground',
    icon: Lock,
    name: 'Ground',
    desc: 'The answer is emitted with its provenance, or withheld and replaced with a refusal.',
  },
]

/**
 * What the pipeline can produce.
 */
export const PIPELINE_OUTPUT = [
  { label: 'Supported claims', value: 'grounded' },
  { label: 'Below threshold', value: 'recovered' },
  { label: 'Unrecoverable', value: 'withheld', tone: 'alarm' },
]
