"""
TRUSTRAG — Claim verification pipeline package.

Sub-modules (each a single responsibility):

- ``pipeline.infra`` — shared helpers (_structured_verifier, _chunk_identity, etc.)
- ``pipeline.decomposition`` — decompose_answer_to_claims
- ``pipeline.nli`` — verify_claim_nli, batch_verify_claims_nli, fused_decompose_verify
- ``pipeline.retrieval`` — retrieve_evidence_for_claim, _persist_claim_evidence
- ``pipeline.metrics`` — get_nli_metrics, _record_batch_total_failure
- ``pipeline.orchestrator`` — execute_claim_verification
"""

from __future__ import annotations

__all__ = []
