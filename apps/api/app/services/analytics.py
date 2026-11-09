"""
TRUSTRAG — Analysis service: analytics & dossier export.

Aggregated analytics dashboard data and full compliance/audit dossier export.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "export_analysis_dossier",
]


async def export_analysis_dossier(
    analysis_id_str: str,
    user_id_str: str,
    export_format: str = "jsonld",
) -> dict[str, Any]:
    """
    Export full compliance and audit package for an analysis run.

    Includes answer, verified claim assertions (with triples), retrieved evidence
    with SHA-256 provenance hashes, and reliability diagnosis.
    """
    from app.services.analysis_service import (
        get_analysis,
        get_analysis_claims,
        get_analysis_evidence,
    )

    analysis = await get_analysis(analysis_id_str, user_id_str)
    claims = await get_analysis_claims(analysis_id_str, user_id_str)
    evidence = await get_analysis_evidence(analysis_id_str, user_id_str)

    created_at_str = (
        analysis.created_at.isoformat()
        if hasattr(analysis.created_at, "isoformat")
        else str(analysis.created_at)
    )

    if export_format.lower() == "jsonld":
        return {
            "@context": {
                "@vocab": "https://schema.org/",
                "trustrag": "https://trustrag.dev/ontology/",
                "Claim": "trustrag:Claim",
                "Evidence": "trustrag:Evidence",
                "reliabilityScore": "trustrag:reliabilityScore",
                "integrityStatus": "trustrag:integrityStatus",
                "contentHash": "trustrag:contentHash",
            },
            "@type": "Report",
            "@id": f"urn:trustrag:analysis:{analysis.id}",
            "name": f"TRUSTRAG Verification Audit — {analysis.id}",
            "dateCreated": created_at_str,
            "about": {"@type": "Question", "text": analysis.query},
            "text": analysis.answer,
            "reliability": {
                "score": analysis.reliability.score,
                "status": analysis.reliability.status,
            },
            "diagnosis": {
                "type": analysis.diagnosis.type,
                "failures": analysis.diagnosis.failures,
            },
            "claims": [
                {
                    "@type": "Claim",
                    "text": c.text,
                    "subject": c.subject,
                    "predicate": c.predicate,
                    "object": c.object,
                    "verdict": c.state,
                    "explanation": c.explanation,
                    "evidenceIds": c.evidence_ids,
                }
                for c in claims
            ],
            "evidence": [
                {
                    "@type": "DigitalDocument",
                    "text": e.text,
                    "filename": e.filename,
                    "documentId": e.document_id,
                    "integrityStatus": e.integrity_status,
                    "retrievalScore": e.retrieval_score,
                    "rerankScore": e.rerank_score,
                }
                for e in evidence
            ],
        }

    return {
        "analysis": analysis.model_dump(),
        "claims": [c.model_dump() for c in claims],
        "evidence": [e.model_dump() for e in evidence],
    }
