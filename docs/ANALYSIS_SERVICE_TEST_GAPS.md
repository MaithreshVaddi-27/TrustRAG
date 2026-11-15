# Service-Layer Test Gaps

> **Rewritten.** The original version of this document mapped
> `app/services/analysis_service.py` — a ~1,090-line module at 54 % coverage
> when it was written (2026-09-28). That module has since been split into
> focused sub-modules, and `analysis_service.py` is now a **114-line
> backward-compatible re-export shim at 100 % coverage**. The gaps it
> described no longer exist.
>
> This document now maps the gaps that are actually open, measured against
> the current suite.

**Scope:** `apps/api/app/services/**` — the service layer between the API
routers and the persistence/RAG layers.

**How it was measured**

```bash
cd apps/api
python -m pytest -q --cov=app.services --cov-report=term-missing
```

**Overall project coverage:** 80.4 % (gate: 78 %).

---

## 1. Current coverage snapshot

| Module | Statements | Missed | Coverage | Role |
|---|---|---|---|---|
| `app/services/analysis_service.py` | 11 | 0 | **100 %** | Re-export shim — the old monolith's public surface |
| `app/services/analytics.py` | 12 | 1 | 92 % | Analysis dossier export |
| `app/services/search_service.py` | 64 | 4 | 94 % | Search / re-ranking helpers |
| `app/services/pipeline.py` | 271 | 41 | 85 % | create_analysis, run_analysis_pipeline, reads, trace, SSE, serialization |
| `app/services/kb_service.py` | 204 | 58 | 72 % | Knowledge-base CRUD, document ingest, snapshots, rollback |
| `app/services/auth_service.py` | 83 | 26 | 69 % | Registration, login, lockout, token issuance |
| `app/services/claims_evidence.py` | 107 | 40 | **63 %** | User-level claim / evidence / conflict reads |
| `app/services/sse.py` | 24 | 14 | **42 %** | In-process SSE pub/sub |

---

## 2. The gaps worth closing

Ordered by risk, not by line count.

### 2.1 `sse.py` — 42 % (lines 27–32, 39, 44–50)

The in-process publish/subscribe used by the live trace stream. This is the
one that bites: the frontend opens an SSE connection, and a defect here shows
up as a stalled "Pipeline running…" spinner rather than an error.

**Uncovered behaviours**

| Behaviour | Why it matters |
|---|---|
| Subscriber added / removed (`subscribe`, `unsubscribe`) | A subscriber that is never removed leaks a queue and a socket; one that is never added silently drops every event |
| `publish` with **no** subscribers | Must be a no-op, not an exception — this is the path a completed analysis takes after the client disconnected |
| `publish` to a **full** queue (slow client) | Must drop the oldest event rather than block the publisher, or a stalled browser tab stalls the analysis pipeline |
| `publish` with a subscriber whose queue is closed | Must not raise into the publishing task |

**Suggested tests**

1. `publish` with no subscribers returns cleanly and does not raise.
2. A subscriber receives the event it was given, in order.
3. `unsubscribe` stops delivery.
4. Publishing to a full queue drops the **oldest** event and keeps the newest.
5. Publishing after a subscriber's queue is closed does not raise.
6. Two subscribers each receive a copy of the same event.

### 2.2 `claims_evidence.py` — 63 % (lines 54, 125–158, 169, 182–193, 205, 243)

The user-level vault reads behind the **Evidence**, **Claims** and
**Conflicts** pages — the three screens a user spends the most time in.

**Uncovered behaviours**

| Behaviour | Why it matters |
|---|---|
| Cross-tenant isolation on the user-level lists | A leak here exposes one user's evidence to another. The per-analysis reads are covered; the **user-level** lists are the gap |
| Empty result | An empty vault must answer `[]`, not `null` and not a 500 |
| Cursor / pagination boundary | The vault truncates at 1000 analyses per user; the boundary itself must be pinned |
| Ordering | The pages assume newest-first; a silent order change is invisible until a user complains |
| A claim whose `analysis_id` points at a deleted analysis | Must be skipped, not crash the whole page |

**Suggested tests**

1. User A's claims/evidence/conflicts never appear for user B (mirrors `tests/test_cross_tenant_scoping.py`, at the vault level rather than the per-analysis level).
2. An empty vault answers `[]`.
3. The truncation boundary returns exactly the documented number of items, with the newest retained.
4. The list is ordered newest-first.
5. An orphaned claim (its analysis was deleted) is skipped without error.
6. A malformed document in the collection is skipped rather than failing the whole read.

### 2.3 `auth_service.py` — 69 % (lines 59–60, 93–96, 100–111, 140, 153–155, 158–159, 162, 194–196)

Registration, login, the lockout window and token issuance.

**Uncovered behaviours**

| Behaviour | Why it matters |
|---|---|
| Duplicate registration | Must fail with a conflict, not a 500 from a unique-index violation |
| Lockout counter increment and reset | A counter that never resets locks a legitimate user out permanently; one that never increments is no protection at all |
| The exact lockout window (5 attempts / 900 s) | The number is a security control — it must be pinned by a test |
| Token expiry arithmetic | A token that expires a second early or late is a real defect |

**Suggested tests**

1. Registering an existing email answers 409 with a stable error code.
2. Five failed logins lock the account; the sixth attempt is rejected even with the correct password.
3. A successful login resets the failure counter.
4. The lockout expires after the configured window (use a frozen clock).
5. A token issued at `t` expires at `t + ttl`, not before.

### 2.4 `kb_service.py` — 72 % (lines 49, 88–89, 93, 122–124, 127, 196–225, 233–246, 263, 356, 389–428, 452, 518–519, 524)

Knowledge-base CRUD, document ingestion, snapshots and rollback. Lines
**389–428** (snapshot / rollback) are the largest uncovered block and the most
destructive operations in the service — a wrong rollback silently discards
ingested documents.

**Suggested tests**

1. Deleting a knowledge base removes its documents and its vector collection.
2. A snapshot captures the corpus at a point in time; a rollback restores it.
3. Rolling back to an unknown snapshot id answers 404 with a stable error code.
4. Rollback is refused while an analysis is running against the knowledge base.
5. The embedding-space pin is set on first ingest and never changes for a
   knowledge base (a changed pin makes existing vectors unqueryable).

---

## 3. Why these matter beyond coverage

The three lowest-covered modules are the three that sit on a path where a
defect is **silent** rather than loud:

- a leaked vault row shows plausible data to the wrong user;
- a stalled SSE queue shows a spinner that never resolves;
- a lockout counter that does not reset locks out a legitimate user.

A line-coverage number does not capture that. This document exists so the
gaps are *named* rather than left to a percentage.

---

## 4. Related

- [`docs/backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md`](backend/BACKEND_CHANGELOG_AND_RECOMMENDATIONS.md) — the living engineering log, including the changes made against the audit findings.
- `apps/api/tests/test_cross_tenant_scoping.py` — the per-analysis tenant-isolation suite that the vault-level tests should mirror.
- `apps/api/tests/test_rate_limiting.py`, `apps/api/tests/test_auth.py` — the existing auth-path coverage this document extends.
