# TRUSTRAG Line-by-Line Technical Review Pass

This document details the line-by-line inspection of core architectural components across TRUSTRAG to verify correctness, edge cases, error resilience, and security constraints.

---

## 1. LangGraph Agent Workflow (`app/agent/graph.py`)

| Line Range | Component | Inspection Notes & Verification | Risk Assessment |
|---|---|---|---|
| **L45–L85** | `retrieval_node` | Implements dense + sparse hybrid search with Reciprocal Rank Fusion (RRF). Respects `max_context_override` during re-retrieval recovery loops so context volume doubles safely. | Low / Verified |
| **L88–L135** | `generation_node` | Calls grounded generation prompt. Protects against missing segments by inspecting evidence list before invocation. Updates trace timeline. | Low / Verified |
| **L140–L190** | `verification_node` | Parses answer. When answer is `"ABSTAIN"`, sets `verdict_status = "FAIL"` on attempts < max attempts, enabling adaptive recovery rather than aborting prematurely. | Low / Verified |
| **L200–L250** | `diagnosis_node` | Classifies root cause into `RETRIEVAL_FAILURE` or `HALLUCINATION` based on contradiction rate vs coverage thresholds. | Low / Verified |
| **L260–L350** | `recovery_node` | Routes dynamically: if missing claims exist, targets them; if abstained/empty context, executes topical query expansion. Re-retrieval doubles top_k context. | Low / Verified |
| **L360–L430** | `should_recover_condition` | State transition conditional edge. Safely terminates when status is `PASS`, or when maximum attempts have been exhausted. | Low / Verified |

---

## 2. Claim Verification & NLI Batching (`app/verification/verifier.py`)

| Line Range | Component | Inspection Notes & Verification | Risk Assessment |
|---|---|---|---|
| **L25–L75** | `Pydantic Schemas` | Defines `ClaimDecomposition`, `NLIVerdict`, and `BatchNLIVerdict`. Enforces strict Literal typing `["SUPPORTED", "CONTRADICTED", "NEUTRAL"]`. | Low / Verified |
| **L80–L135** | `NLI & Batch Prompts` | Strict NLI definitions. Includes prompt injection defense rule instructing model to treat retrieved context segments as raw untrusted data. | Low / Verified |
| **L140–L175** | `decompose_answer_to_claims` | Breaks answer into independent atomic assertions. Returns fallback `[answer]` if decomposition fails. | Low / Verified |
| **L180–L215** | `verify_claim_nli` | Single-claim NLI verification fallback. Safe exception handler returns default `NEUTRAL` without leaking internal errors. | Low / Verified |
| **L220–L265** | `batch_verify_claims_nli` | Bundles all numbered claims into a single structured call. Eliminates 429 quota exhaustion; reduces API calls from N to 1. | Low / Verified |
| **L270–L320** | `execute_claim_verification` | Persists claim documents to MongoDB, resolving 1-based segment indices to persistent MongoDB `Evidence` ObjectIDs. | Low / Verified |

---

## 3. Ingestion, Preprocessing & Zoning (`app/ingestion/preprocessor.py`)

| Line Range | Component | Inspection Notes & Verification | Risk Assessment |
|---|---|---|---|
| **L20–L60** | `Contractions & Stopwords` | Normalizes English contractions (`can't` -> `can not`). Separates `CORE_STOPWORDS` from `QUERY_NOISE_STOPWORDS` for targeted search filtering. | Low / Verified |
| **L75–L135** | `Document Zoning` | `ZoneType` inherits from `enum.StrEnum`. Classifies chunks into `TITLE`, `HEADER`, `SUMMARY`, `BODY`, `METADATA`. Boosts Title/Header weights. | Low / Verified |
| **L140–L180** | `normalize_text` | Unicode NFKD normalization. Strips PDF bullet artifacts (`\uf0d8`, `\u2022`). Repairs broken line-break hyphenations (`docu-\nment` -> `document`). | Low / Verified |
| **L185–L370** | `PorterStemmer` | Canonical 5-step rule-based morphological root stemmer (Martin Porter, 1980). Pure Python with zero external dependencies. | Low / Verified |
| **L375–L410** | `extract_ngrams & lexical_analyze` | Combines stemmed unigrams with bigram compound tokens (`data_structur`, `invert_file`) for precise phrase matching in sparse vectors. | Low / Verified |

---

## 4. Security, Auth & Defense (`app/core/security.py` & `app/main.py`)

| Line Range | Component | Inspection Notes & Verification | Risk Assessment |
|---|---|---|---|
| **L23–L37** | `Password Hashing` | Uses standard `bcrypt.gensalt(rounds=12)` for strong work factor. Constant-time comparison via `bcrypt.checkpw`. | Low / Verified |
| **L39–L55** | `JWT Minting` | Signs JWT with HS256 using configured `JWT_SECRET`. Attaches UTC `exp`, `sub`, and `iat` claims. | Low / Verified |
| **L57–L70** | `JWT Decoding` | Imports `ExpiredSignatureError` and `JWTError` directly from `jose.exceptions`. Raises domain `AuthenticationError`. | Low / Verified |
| **L260–L275** | `Security Headers Middleware` | Injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, and `Permissions-Policy`. In production, attaches `HSTS`. | Low / Verified |

---

## 5. Storage & Database Consistency (`app/db/mongodb.py`)

| Line Range | Component | Inspection Notes & Verification | Risk Assessment |
|---|---|---|---|
| **L80–L145** | Connection Lifecycle | Connects via `AsyncIOMotorClient` with retry logic. Lifespan shutdown closes client cleanly. | Low / Verified |
| **L185–L260** | `create_indexes` | Creates required compound indexes on startup. Newly added compound index on `Collections.DOCUMENT_CHUNKS` prevents unindexed query degradation. | Low / Verified |
