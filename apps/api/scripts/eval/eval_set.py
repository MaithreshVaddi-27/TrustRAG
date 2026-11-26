"""
TRUSTRAG — Ground-truth evaluation set.

The first evaluation corpus was a single document with five probes. That is
too small to claim anything about accuracy: it cannot tell a real improvement
from noise, it has no *unanswerable* probe (so "abstains" is not measurable as
a correct outcome, only as a loss), and it exercises one domain only.

This module defines a corpus of four documents across four domains and a
probe set that covers both halves of the product's promise:

- **answerable probes** — the answer IS in the corpus, and the expected
  substring must appear in the final answer;
- **unanswerable probes** — the answer is NOT in the corpus, and the run MUST
  abstain. A system that answers these is the dangerous failure mode; a system
  that abstains on the answerable ones is merely useless.

Both halves are scored, so an "accuracy improvement" cannot be bought by
weakening verification: every answerable probe that stops being answered costs
a point, and every unanswerable probe that starts being answered costs a point.
"""

from __future__ import annotations

__all__ = ["CORPUS", "PROBES", "answerable_probes", "unanswerable_probes"]

RETRIEVAL_POLICY = """TrustRAG Retrieval Policy

The hybrid retrieval policy combines dense semantic search with sparse
lexical search. Dense retrieval uses BGE-small embeddings computed locally
through ONNX Runtime. Sparse retrieval uses BM25 style term weights with
server side inverse document frequency applied by Qdrant.

Reciprocal rank fusion merges the two ranked lists. The fusion constant is
sixty. Only the top twenty fused candidates are considered for reranking.

The reranker is a cross encoder based on MS Marco MiniLM. It scores each
query and segment pair jointly and sorts the candidates by relevance.

Temporal filtering excludes segments whose parent document is not effective
at the reference time. A document may declare an effective from date and an
effective until date. Segments outside that window are dropped before the
context is assembled.

Abstention is a first class outcome. When the evidence does not support a
grounded response the pipeline must abstain rather than guess. The verdict
engine computes an evidence coverage ratio and a contradiction rate from the
verified claims. Answers below the abstain threshold are withheld.
"""

SECURITY_POLICY = """TrustRAG Security Policy

Bearer tokens expire after 30 minutes. Refresh tokens remain valid for
7 days. Revocation takes effect immediately on the next request.

Multi-factor authentication is required for administrator accounts. Sessions
are invalidated after three consecutive failed login attempts. Passwords must
be at least 12 characters long.

API keys are rotated every 90 days. Service tokens for machine to machine
calls are issued with a one hour lifetime and can be scoped to a single
knowledge base.

The lockout window lasts 15 minutes. Authentication failures are written to
the audit log with the source address and the attempted account name.
"""

RETENTION_POLICY = """TrustRAG Data Retention Policy

User documents are retained for 24 months after the last recorded activity.
Audit logs are retained for 7 years to satisfy the compliance review.

Backups expire after 35 days. Deleted records are purged from the primary
store within 30 days and from backups within 90 days.

The default retention period for analytics events is 13 months. Knowledge
base snapshots are kept for 180 days unless a rollback is in progress.

A legal hold suspends every deletion rule for the affected records until the
hold is released by an administrator.
"""

API_LIMITS = """TrustRAG API Limits

The default rate limit is 60 requests per minute per client. The maximum
page size is 200 items.

Uploading a document is limited to 25 megabytes. Concurrent analyses per
account are limited to 4. A 429 response means the client exceeded its
quota.

The default request timeout is 120 seconds. The maximum query length is
2000 characters. Uploads are accepted in PDF, TXT and MD formats.
"""

CORPUS: tuple[tuple[str, str], ...] = (
    ("retrieval-policy.txt", RETRIEVAL_POLICY),
    ("security-policy.txt", SECURITY_POLICY),
    ("retention-policy.txt", RETENTION_POLICY),
    ("api-limits.txt", API_LIMITS),
)

# Each probe: (query, expected answer substring or None).
# None means the answer is NOT in the corpus — the run must abstain.
PROBES: tuple[tuple[str, str | None], ...] = (
    # ── retrieval policy ──────────────────────────────────────────────────
    ("What is the reciprocal rank fusion constant?", "sixty"),
    ("How many fused candidates are considered before reranking?", "twenty"),
    ("Which embedding model does dense retrieval use?", "BGE-small"),
    ("What does the temporal filter drop?", "dropped"),
    ("Which cross encoder does the reranker use?", "MS Marco MiniLM"),
    ("What happens when the evidence does not support an answer?", "abstain"),
    # ── security policy ───────────────────────────────────────────────────
    ("How long are bearer tokens valid?", "30 minutes"),
    ("How long are refresh tokens valid?", "7 days"),
    ("When does token revocation take effect?", "immediately"),
    ("Is multi-factor authentication required for administrator accounts?", "required"),
    ("How many failed login attempts invalidate a session?", "three"),
    ("What is the minimum password length?", "12 characters"),
    ("How often are API keys rotated?", "90 days"),
    ("How long is the lockout window?", "15 minutes"),
    # ── retention policy ───────────────────────────────────────────────────
    ("How long are user documents retained?", "24 months"),
    ("How long are audit logs retained?", "7 years"),
    ("After how many days do backups expire?", "35 days"),
    ("How long does a deleted record stay in the primary store?", "30 days"),
    ("What is the default retention period for analytics events?", "13 months"),
    ("How long are knowledge base snapshots kept?", "180 days"),
    # ── api limits ────────────────────────────────────────────────────────
    ("What is the default rate limit?", "60 requests per minute"),
    ("What is the maximum page size?", "200 items"),
    ("What is the maximum document upload size?", "25 megabytes"),
    ("How many concurrent analyses are allowed per account?", "4"),
    ("What does a 429 response mean?", "exceeded its quota"),
    ("What is the default request timeout?", "120 seconds"),
    ("Which file formats are accepted for upload?", "PDF"),
    # ── unanswerable — the corpus says nothing about these ──────────────────
    ("What is the maximum number of retries per analysis?", None),
    ("Which GPU model accelerates the embedding service?", None),
    ("What is the wifi password of the office network?", None),
    ("How many languages does the admin console support?", None),
    ("What is the average latency of the embedding model?", None),
    ("Which database cluster stores the audit logs?", None),
)


def answerable_probes() -> tuple[tuple[str, str], ...]:
    """Probes whose answer is in the corpus."""
    return tuple((q, a) for q, a in PROBES if a is not None)


def unanswerable_probes() -> tuple[tuple[str], ...]:
    """Probes whose answer is NOT in the corpus — the run must abstain."""
    return tuple(q for q, a in PROBES if a is None)
