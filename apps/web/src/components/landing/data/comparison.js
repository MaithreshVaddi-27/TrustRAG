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
 * The category filters.
 */
export const COMPARISON_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'safety', label: 'Safety' },
  { id: 'retrieval', label: 'Retrieval' },
  { id: 'developer', label: 'Integration' },
]

/**
 * The comparison rows.
 */
export const COMPARISON_ROWS = [
  {
    category: 'safety',
    title: 'Hallucination detection',
    subtitle: 'Verification of individual factual statements in the output',
    naive:
      'Blind single-pass generation with no post-generation verification. A wrong statement passes silently to the reader.',
    ours:
      'Prose is decomposed into atomic propositional claims, then each is audited in parallel against its cited chunks.',
    impact: 'A wrong statement has to survive a check before it is shown.',
  },
  {
    category: 'safety',
    title: 'Closed-loop self-healing',
    subtitle: 'Recovery when a response fails verification',
    naive:
      'Broken or unverified output is returned directly, or the request fails with a generic error.',
    ours:
      'A LangGraph state machine rewrites the query and expands candidate retrieval, up to two attempts.',
    impact: 'Transient retrieval failures are resolved without a human in the loop.',
  },
  {
    category: 'retrieval',
    title: 'Retrieval algorithm and precision',
    subtitle: 'How documents are matched and ranked',
    naive:
      'Dense vectors only, which routinely misses statutory codes, part numbers and exact acronyms.',
    ours:
      'Dense and BM25 sparse retrieval combined with reciprocal rank fusion.',
    impact: 'Semantic context and exact keyword matches are both retrieved.',
  },
  {
    category: 'retrieval',
    title: 'Evidence provenance and tamper guard',
    subtitle: 'Integrity checking of the underlying sources',
    naive:
      'Blind trust in stored chunks. Silently tampered documents and stale cached vectors are cited.',
    ours:
      'SHA-256 root checksum checks and ISO temporal document expiry enforcement.',
    impact: 'A citation can be checked against the exact bytes it came from.',
  },
  {
    category: 'retrieval',
    title: 'Contextual disambiguation cost',
    subtitle: 'Parent document hierarchy and section context',
    naive:
      'Isolated chunks with no context, or an LLM call per chunk to restore it.',
    ours:
      'Parent document metadata is prepended without an LLM call, at no token cost.',
    impact: 'An orphaned passage arrives with the context needed to read it.',
  },
  {
    category: 'developer',
    title: 'Agent tooling and protocol support',
    subtitle: 'How external agents connect to the pipeline',
    naive:
      'A bespoke API wrapper per integration, each one to maintain.',
    ours:
      'A Model Context Protocol JSON-RPC 2.0 server, ready for Claude and Cursor.',
    impact: 'No SDK to adopt, and no custom client to maintain.',
  },
  {
    category: 'developer',
    title: 'Tenant vector isolation',
    subtitle: 'The security boundary between knowledge bases',
    naive:
      'Soft logical filters, or one shared vector space with a cross-tenant leakage risk.',
    ours:
      'Hard physical collection partitioning in Qdrant with tenant-scoped MongoDB indexes.',
    impact: 'The boundary is enforced by the store, not by application code.',
  },
]
