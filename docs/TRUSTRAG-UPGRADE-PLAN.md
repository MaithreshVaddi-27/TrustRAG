# TRUSTRAG — Simple Production Upgrade Plan

## Goal

Upgrade the current TRUSTRAG into a **production-quality RAG** with:

- better retrieval quality
- better document handling
- OCR support
- reliable answers
- strong citations/provenance
- fast inference
- security
- tests and evaluation
- clean maintainable code

**Rule:** Implement one phase at a time. Test it. Then move to the next phase.

---

# Current Pipeline

```text
Document
  ↓
Parser
  ↓
Chunking
  ↓
Dense + Sparse Retrieval
  ↓
RRF
  ↓
Reranker
  ↓
Gemini
  ↓
Claim Verification
  ↓
Recovery / Abstention
```

---

# Phase 0 — Baseline

### Goal
Know how good the current system actually is.

### Do

- Inspect the whole repository.
- Run existing tests.
- Create a small fixed evaluation dataset.
- Record current:
  - Recall@K
  - MRR / nDCG
  - claim support
  - contradiction rate
  - citation correctness
  - abstention
  - P50/P95 latency

### Output

```text
baseline_results
```

**Difficulty:** Easy–Medium

---

# Phase 1 — Production Ingestion + OCR

### Current

```text
PDF → Parser → Text
```

### Target

```text
Document
   ↓
Detect text/image page
   ↓
Native extraction OR OCR
   ↓
Clean text + metadata
```

### Do

- Keep native extraction for normal PDFs.
- Use OCR only for scanned/image pages.
- Support mixed PDFs.
- Preserve:
  - page number
  - source
  - section
  - OCR used
  - OCR confidence if available
- Keep original page/image provenance.

### Important

Do **not** OCR every page. It increases latency and can introduce errors.

**Difficulty:** Medium–Hard

---

# Phase 2 — Better Chunking

### Current

```text
Fixed character chunks
```

### Target

```text
Document
 ↓
Title / Section / Paragraph / Table
 ↓
Structure-aware chunks
```

### Do

- Preserve document structure.
- Keep page/section metadata.
- Avoid splitting tables, headings and important paragraphs unnecessarily.
- Benchmark old vs new chunking.

**Difficulty:** Medium

---

# Phase 3 — Improve Retrieval

### Target

```text
                ┌→ Dense ──┐
Query ──────────┤          ├→ RRF → Reranker → Top Evidence
                └→ Sparse ─┘
```

### Do

- Keep hybrid retrieval.
- Keep RRF initially.
- Separate dense and sparse preprocessing.
- Verify sparse retrieval implementation.
- Benchmark:
  - Dense
  - Sparse
  - Hybrid
  - Hybrid + RRF
  - Hybrid + Reranker
- Optimize Top-K and final-K for quality + speed.

**Difficulty:** Medium

---

# Phase 4 — Better Query Handling

### Target

```text
Question
   ↓
Query Router
   ├─ Simple → normal retrieval
   ├─ Temporal → temporal retrieval
   ├─ Comparison → retrieve A + B
   └─ Complex → decomposition
```

### Do

- Detect query type.
- Keep simple queries cheap.
- Add query rewriting only when needed.
- Add temporal/version filtering properly.

**Difficulty:** Medium

---

# Phase 5 — Multi-Hop RAG

### Current

```text
Question → Retrieve → Answer
```

### Target

```text
Complex Question
      ↓
Sub-questions
      ↓
Parallel Retrieval
      ↓
Evidence Combination
      ↓
Answer
```

### Do

- Add decomposition for complex questions.
- Retrieve evidence for each sub-question.
- Support comparison questions.
- Avoid unnecessary decomposition.

**Difficulty:** Hard

> Implement only after basic retrieval is strong.

---

# Phase 6 — Stronger Verification

### Current

```text
Answer → Claims → Verify
```

### Target

```text
Answer
 ↓
Atomic Claims
 ↓
Claim-specific Evidence Retrieval
 ↓
Entailment / Contradiction
 ↓
Temporal + Provenance Checks
 ↓
Claim Verdict
```

### Do

Each claim should know:

```text
SUPPORTED
CONTRADICTED
NEUTRAL
```

and its:

```text
source
page
evidence
```

Do not rely only on an LLM judge where other evidence checks are possible.

**Difficulty:** Hard

---

# Phase 7 — Trust + Provenance

### Target

```text
Document
 ↓
Version
 ↓
Page
 ↓
Chunk
 ↓
Evidence
 ↓
Claim
 ↓
Answer
```

### Do

- Keep document/chunk hashes.
- Track document versions.
- Track source/page metadata.
- Detect changed/corrupted evidence.
- Make citations traceable.

For OCR:

```text
Answer → OCR chunk → page → original image/page
```

**Difficulty:** Medium

---

# Phase 8 — Adaptive Recovery

### Current

```text
Failure → Rewrite → Retrieve again
```

### Target

```text
Failure
  ↓
Diagnose
  ├─ Retrieval failure → rewrite
  ├─ Low coverage → expand/decompose
  ├─ Conflict → retrieve more + compare
  └─ Unsupported claim → claim retrieval
```

### Rules

- Maximum 2–3 recovery attempts.
- Always use a latency/token budget.
- Abstain if evidence remains insufficient.

**Difficulty:** Hard

---

# Phase 9 — Security

### Test

Documents may contain:

```text
Ignore previous instructions...
Reveal system prompt...
Call this tool...
```

Treat all document content as **untrusted data**.

Test:

- prompt injection
- malicious documents
- conflicting documents
- outdated documents
- corrupted chunks
- OCR errors
- poisoned content

**Difficulty:** Medium–Hard

---

# Phase 10 — Speed + Production Engineering

### Do

Add:

```text
Caching
Parallel retrieval
Batch embeddings
Connection reuse
Timeouts
Retries with backoff
Bounded retries
Structured logging
Health checks
```

Track:

```text
retrieval latency
reranker latency
LLM latency
verification latency
total latency
token usage
```

Do not optimize blindly. Compare **before vs after**.

**Difficulty:** Medium

---

# Phase 11 — Data / Index Lifecycle

### Support

```text
Upload
Update
Delete
Version
Re-index
```

When a document changes:

```text
Old version
 ↓
Invalidate old index data
 ↓
Process new version
 ↓
Index new version
```

Prevent stale evidence from being returned accidentally.

**Difficulty:** Medium–Hard

---

# Phase 12 — Final Evaluation

Run controlled experiments.

### Retrieval

```text
Dense
vs Sparse
vs Hybrid
vs Hybrid + Reranker
```

### Trust

```text
Normal RAG
vs Verified RAG
vs TRUSTRAG
```

### OCR

```text
Native extraction
vs OCR
vs OCR + verification
```

### Recovery

```text
Without recovery
vs With recovery
```

Measure:

```text
Recall@K
MRR
nDCG
Evidence Coverage
Claim Support
Contradiction Rate
Citation Correctness
Abstention
Recovery Success
P50/P95 Latency
Token/Cost
```

**Difficulty:** Medium–Hard

---

# Phase 13 — Final Cleanup + Deployment

### Do

- remove dead code
- remove unnecessary dependencies
- type checking
- linting/formatting
- unit tests
- integration tests
- end-to-end tests
- Docker
- environment-based configuration
- health/readiness checks
- structured logs
- deployment documentation

### Production checklist

```text
✓ Reliable ingestion
✓ OCR fallback
✓ Good chunking
✓ Hybrid retrieval
✓ Reranking
✓ Grounded generation
✓ Claim verification
✓ Provenance
✓ Temporal handling
✓ Security
✓ Bounded recovery
✓ Tests
✓ Evaluation
✓ Observability
✓ Fast enough
✓ Deployment ready
```

**Difficulty:** Medium

---

# Priority Order

```text
P0  Baseline
 ↓
P1  Ingestion + OCR
 ↓
P2  Chunking
 ↓
P3  Retrieval
 ↓
P4  Query Handling
 ↓
P5  Multi-Hop
 ↓
P6  Verification
 ↓
P7  Provenance
 ↓
P8  Recovery
 ↓
P9  Security
 ↓
P10 Speed + Production
 ↓
P11 Index Lifecycle
 ↓
P12 Evaluation
 ↓
P13 Deployment
```

---

# What NOT to Add Yet

Do not add these just because they sound advanced:

```text
GraphRAG
Many agents
Multiple vector DBs
Many LLMs
Multiple rerankers
Complex orchestration
Large models
Microservices everywhere
```

Add them only if evaluation shows a real problem that they solve.

---

# OpenCode / Claude Code Workflow

Use **one phase per prompt**.

## Standard prompt

```text
Read TRUSTRAG-UPGRADE-PLAN.md.

Implement ONLY Phase X.

First inspect the existing repository and understand the current implementation.

Rules:
- Do not rewrite unrelated code.
- Do not start another phase.
- Do not add unnecessary dependencies.
- Preserve existing working functionality.
- Prioritize quality and speed.
- Keep the implementation simple and production-ready.
- Add tests for the changes.
- Use existing architecture where possible.
- Do not invent functionality.

After implementation:
1. Run tests.
2. Run lint/type checks if available.
3. Run the relevant evaluation.
4. Compare with the previous baseline.
5. Check latency if relevant.
6. Review the diff for unnecessary changes.

Report:
- What changed
- Files changed
- Dependencies added
- Tests run
- Evaluation results
- Performance impact
- Known issues
- Hard parts / limitations

STOP after Phase X.
```

---

# Important Rule

For every change ask:

```text
Does this improve:

Quality?
Speed?
Reliability?
Security?
Maintainability?
```

If not, **do not add it**.

The goal is not the most complicated RAG.

The goal is:

```text
        HIGH QUALITY
             +
        LOW LATENCY
             +
        TRUSTWORTHY
             +
        PRODUCTION-READY
```
