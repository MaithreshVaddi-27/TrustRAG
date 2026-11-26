# Deployment runbook

This runbook covers the deployment rollback drill for TrustRAG. It is a
procedure, not a record of a completed drill: no staging rollback was executed
during the November 2026 audit.

## Preconditions

- A release is deployed as an immutable image tag (for example `trustrag-api:1.2.3`).
- The previous known-good tag is recorded in the deployment log.
- Database migrations are expand-only or have a tested contract-down path.
- The model cache volume is independent of the image, so rolling back code does
  not roll back the ONNX weights.

## Rollback procedure

1. Freeze writes: stop the job worker / analysis intake, or enable maintenance
   mode. Do not roll back while an analysis is mid-pipeline.
2. Record the failing release tag, the request IDs (`X-Request-ID`) and the
   first error timestamp. Logs are structured; correlate on `request_id`.
3. Redeploy the previous image tag. Do not rebuild: use the exact digest that
   was previously verified.
4. Probe readiness before restoring traffic:

   ```bash
   curl -fsS http://localhost:8000/api/v1/health
   curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/api/v1/health/ready
   ```

   `/health/ready` must return 200. A 503 means MongoDB or Qdrant is degraded;
   do not proceed.

5. Re-enable intake and replay one known query against a known document. The
   expected result is a completed analysis with a `VERIFIED` evidence item and
   a `SUPPORTED` claim.
6. Confirm the rollback in the deployment log with the old tag, the new tag,
   the operator and the verification result.

## Drill cadence

Run this procedure against staging before each public release and once per
quarter on production. A rollback that has never been executed is not a
rollback plan.
