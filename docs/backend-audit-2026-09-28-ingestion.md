# TrustRAG Ingestion Subsystem Audit — Silent Data Loss, AV Bypass, Chunk Provenance

- **Date:** 2026-09-28
- **Branch:** `ui-redesign` @ `4f99d89`
- **Scope:** `apps/api/app/ingestion/` (pipeline, parser, chunker, chunking_strategies, preprocessor, ocr, sparse_vector, page_images)
- **State:** **nothing in this report is fixed yet.** It is a findings report with reproduction evidence, so the work can be picked up independently.
- **Test baseline at audit time:** 664 backend passed, **79% coverage** (8260 statements, 1749 missed).

## Evidence legend

| Tag | Meaning |
|---|---|
| **REPRODUCED** | I ran the failing case and observed the wrong output. |
| **PROVEN-MECHANISM** | The mechanism was demonstrated directly; the specific natural trigger was not produced. |
| **CODE-EVIDENCE** | Read from the source only; not executed. |

Findings H1, H2 and M5 were independently re-verified by the author after the audit returned. Everything else is as the audit reported it, with its own evidence tag preserved.

---

## Summary

| ID | Severity | Finding | Evidence | Status |
|---|---|---|---|---|
| **H1** | **HIGH** | `<meta>` latches the HTML text extractor off — every HTML upload ingests as empty | REPRODUCED | **open** |
| **H2** | **HIGH** | ClamAV "malware detected" is swallowed by its own `except Exception` | REPRODUCED | **open** |
| **M1** | MEDIUM | DOCX decompression-bomb guard is ratio-only, with no absolute ceiling | REPRODUCED | open |
| **M2** | MEDIUM | `layout_aware` emits `character_offset` values that do not index the page text | REPRODUCED | open |
| **M3** | MEDIUM | `ProgressiveChunkingStrategy` has no step guard → 507x chunk blowup | REPRODUCED | open |
| **M4** | MEDIUM | `character_offset` points at stripped whitespace, not the chunk's first character | REPRODUCED | open |
| **M5** | MEDIUM | Ingestion semaphore keyed by `id(event_loop)` → documents wedge in `processing` forever | PROVEN-MECHANISM | **open** |
| **L1** | LOW | OCR `min_confidence` gate is skipped when RapidOCR returns no per-line score | CODE-EVIDENCE | open |
| **L2** | LOW | `parse_pdf` re-wraps its own `IngestionError`s, losing the limit message | CODE-EVIDENCE | open |

---

## H1 — `<meta>` permanently disables text extraction (silent data loss)

**`app/ingestion/parser.py:330-337`**

```python
def handle_starttag(self, tag, attrs):
    if tag in ("script", "style", "meta", "noscript"):
        self.ignore = True
    ...

def handle_endtag(self, tag):
    if tag in ("script", "style", "meta", "noscript"):
        self.ignore = False
```

`script` and `style` are properly closed, so latching on them is correct. But **`meta` and `noscript` are void / unclosed elements** — `handle_endtag` never fires for them. `self.ignore` is therefore set `True` at the first `<meta>` and stays `True` for the rest of the document. `handle_data` then discards every remaining character, including the whole `<body>`.

Real-world HTML essentially always contains `<meta charset>` in `<head>`, so this fires on practically every HTML upload. `html`/`htm` are in the `supported_formats` list in `config/models.yaml:176-177`.

### Reproduction

```python
>>> from app.ingestion.parser import parse_html
>>> parse_html(io.BytesIO(b'<html><head><title>T</title></head><body><p>Revenue grew 42 percent.</p></body></html>'))[0]['text']
'T \n Revenue grew 42 percent.'
>>> parse_html(io.BytesIO(b'<html><head><meta charset="utf-8"><title>T</title></head><body><p>Revenue grew 42 percent.</p></body></html>'))[0]['text']
''
```

End-to-end through the real parser + the configured chunker:

```python
>>> pages, f, u = parse_document('policy.html', io.BytesIO(html))
>>> len(get_chunking_strategy().chunk(pages, 512, 64))
pages=[{'page': 1, 'text': ''}]  chunks=0
```

### Impact

This is the worst failure mode in the report because **nothing reports it**. The client gets HTTP 201 and `ingestion_status: "completed"`, the document appears in the knowledge base, and it matches nothing. A customer uploading their policy page sees a success response and a document that cannot be retrieved.

### Fix

Track the ignored tags in a set rather than a single boolean, so an unclosed void element cannot latch the whole extractor:

```python
self._ignored: set[str] = set()

def handle_starttag(self, tag, attrs):
    if tag in ("script", "style"):
        self._ignored.add(tag)
    elif tag in ("meta", "noscript"):
        pass  # void/unclosed — has no content to skip

def handle_endtag(self, tag):
    self._ignored.discard(tag)

def handle_data(self, data):
    if not self._ignored:
        super().handle_data(data)
```

Regression test must cover a `<meta>` in `<head>` (whole body lost) and a `<meta>` mid-body (everything after it lost).

---

## H2 — the ClamAV malware verdict is swallowed by its own handler (AV bypass)

**`app/ingestion/parser.py:418-426`**

```python
try:
    cd = pyclamd.ClamdNetworkSocket()
    if cd.ping():
        stream.seek(0)
        result = cd.scan_stream(stream.read())
        if result:
            raise IngestionError("Malware detected by AV engine", detail=str(result))
except Exception:                                   # <-- catches its own IngestionError
    logger.debug("ClamAV daemon unavailable, skipping AV scan")
```

The `raise IngestionError` is lexically **inside** the `try`, so the blanket `except Exception` discards the positive detection and logs the misleading message "ClamAV daemon unavailable". `parse_document` then proceeds to index a file ClamAV positively identified.

### Reproduction

```python
>>> mod = types.ModuleType('pyclamd')
>>> class C:
...     def ping(self): return True
...     def scan_stream(self, d): return {'stream': 'Eicar-Test-Signature FOUND'}
>>> sys.modules['pyclamd'] = mod
>>> scan_for_malware(io.BytesIO(b'file with no eicar literal string'))
[debug] ClamAV daemon unavailable, skipping AV scan
>>> # returned normally — the FOUND verdict was discarded
```

### Impact

The malware scanner only ever does anything when `pyclamd` **is not** installed. When it is installed and working, a positive detection is discarded. `tests/test_upgrade_phases.py:354` only exercises the EICAR-string branch, so the ClamAV branch has no test.

### Fix

Narrow the `except` to the connection failure it is meant to catch, and let `IngestionError` propagate:

```python
try:
    cd = pyclamd.ClamdNetworkSocket()
    if cd.ping():
        stream.seek(0)
        result = cd.scan_stream(stream.read())
except Exception:            # daemon unreachable / socket error only
    logger.debug("ClamAV daemon unavailable, skipping AV scan")
    return
if result:
    raise IngestionError("Malware detected by AV engine", detail=str(result))
```

`stream.seek(0)` must stay outside the `try` or be re-applied, since the `finally` that restores position currently guards it.

---

## M1 — DOCX decompression-bomb guard has no absolute ceiling

**`app/ingestion/parser.py:253-257`**

`check_decompression_bomb` only compares `decompressed / compressed` against 100 for `.docx` (`parser.py:50`). There is **no absolute limit** on `total_uncompressed`, and the expanded XML is then materialised as a live `ElementTree`.

Mildly-repetitive prose compresses ~43x, far under the cap, so a small upload expands into hundreds of MB of XML and roughly 3x that in RSS.

### Reproduction

```
zip=0.32MB  xml=13.6MB  ratio=42.9x  -> parsed 12,408,888 chars | RSS 118MB -> 158MB (delta  40MB)
zip=2.11MB  xml=91.1MB  ratio=43.2x  -> parsed 83,088,888 chars | RSS 397MB -> 676MB (delta 278MB)
```

**278MB RSS from a 2.11MB upload = 132x amplification**, and no exception was raised. Extrapolated to the 20MB `max_file_size_mb` ceiling that is roughly 2.6GB RSS, in an `asyncio.to_thread` worker — so it takes down the whole API process, not just one request.

### Fix

Add an absolute byte ceiling alongside the ratio check, and read the member in bounded chunks rather than materialising it whole.

---

## M2 — `layout_aware` chunk offsets do not index the page text

**`app/ingestion/chunking_strategies.py:271-288` and `:307`**

`chunk_text` sets `character_offset` relative to the string it was given. `LayoutAwareChunkingStrategy` feeds it a *sub-block* — and for tables, a space-joined string that appears nowhere in the page — then rewrites `chunk_index` and `page` but never rebases `character_offset`. `SemanticChunkingStrategy` does rebase, at `chunking_strategies.py:128`.

### Reproduction

With `chunking_strategy: layout_aware` in `config/models.yaml`:

```
== layout_aware
  off=0    text='short intro'                      page@off='short intro'                        MATCH=True
  off=0    text='alpha bravo charlie delta echo…'  page@off='short intro\nalpha bravo charlie…'   MATCH=False
  off=44   text='hotel india juliet kilo lima…'   page@off='oxtrot golf hotel india juliet…'    MATCH=False
  off=129  text='= 3 | w = 4'                      page@off='| y = 2 | z'                        MATCH=False
```

Two chunks also collide on `offset=0`. Separately, `" ".join(table_rows)` at line 307 glues markdown rows together, fabricating rows like `| val 3 | | val 4 |`.

### Impact

These offsets are persisted to Mongo (`pipeline.py:162`) and the Qdrant payload (`pipeline.py:243`), and surfaced as the Phase-7 provenance chain (`retriever.py:309`, `graph.py:459`). So the provenance feature — the product's core differentiator — points at the wrong span for every `layout_aware` chunk after the first.

---

## M3 — `ProgressiveChunkingStrategy` has no step guard

**`app/ingestion/chunking_strategies.py:196`**

```python
start += max(1, effective_chunk_size - chunk_overlap)
```

`chunk_text` explicitly guards `chunk_overlap >= chunk_size` (`chunker.py:41-48`, logging "forcing minimum step to avoid infinite loop"), and both the semantic and layout strategies delegate to it. `ProgressiveChunkingStrategy` implements its own loop using `max(1, …)` instead, so a misconfigured overlap degrades the step to **1 character**. There is no validation on `chunk_size`/`chunk_overlap` in `app/core/config.py:741-746`; both come straight from `models.yaml`.

### Reproduction

100KB page, `chunk_size=512, chunk_overlap=512`:

```
progressive    -> chunks=99490  elapsed=0.48s
sliding_window -> chunks=196    elapsed=0.01s
```

**507x amplification**, 0.48s just to build the list — before 99,490 embedding calls, each of which becomes a Mongo record and a Qdrant point.

### Fix

Reuse the guarded step from `chunker.py` instead of open-coding it, and add a config-level validation that rejects `chunk_overlap >= chunk_size` at startup rather than at chunk time.

---

## M4 — `character_offset` points at stripped whitespace

**`app/ingestion/chunker.py:89` and `:98`**

```python
chunk_content = text[start:end].strip()
...
"character_offset": start,
```

The docstring and the whole Phase-7 provenance chain promise `character_offset` is the start character index of the chunk in the page. `.strip()` removes leading whitespace, so the recorded offset is short of the real first character by `len(slice) - len(slice.lstrip())`. `SemanticChunkingStrategy:128` propagates the same skew into the rebased page offset.

### Reproduction

26k-char random word page, 5 `(chunk_size, chunk_overlap)` configs — **353 offset mismatches**:

```
chunk text   : 'ggbhgadb hcbfj ba ibfj bd cefjfhbb hhhebcbfe '
real index   : 161
stored offset: 160   -> off by one
```

This is **not** text loss: all 10 interior coverage gaps in that run were whitespace, and the last chunk ends exactly at `len(text)`. The severity is wrong offsets, not truncation.

---

## M5 — ingestion semaphore keyed by `id(event_loop)` wedges documents

**`app/ingestion/pipeline.py:29-38` and `:325`**

```python
_INGESTION_SEMAPHORES: dict[int, asyncio.Semaphore] = {}

def _get_ingestion_semaphore() -> asyncio.Semaphore:
    loop_id = id(asyncio.get_running_loop())
    ...
```

This is **the same bug already fixed in `app/core/concurrency.py`** — the earlier fix was incomplete, and this copy was missed. Two independent defects:

1. `asyncio.Semaphore` binds to the loop that first *contends* on it. Once bound to loop A, a second event loop in the same process receiving the same object raises `RuntimeError: ... is bound to a different event loop`.
2. `id(loop)` is only unique among **live** objects, so a garbage-collected loop's id can be handed to a brand-new loop along with the dead loop's semaphore. Nothing ever evicts entries, so the dict also grows one entry per distinct loop.

### The damaging part

`async with _get_ingestion_semaphore():` sits at `pipeline.py:325`, **outside** `_index_parsed_chunks`'s `try/except`. So the `RuntimeError` fires *before* the handler that writes `ingestion_status: "failed"` can run. The document is already at `ingestion_status: "processing"` (written at `pipeline.py:64-67`) and stays there indefinitely — a permanently wedged document with no error surfaced to the client and no retry.

### Reproduction

The `RuntimeError` path is **PROVEN-MECHANISM** (a semaphore bound to loop A, injected into the cache for a new loop B, raises as expected). Unbounded cache growth was also observed — two sequential loops leave two entries, and there is no eviction. The natural `id()` collision did not fire in the run; the loop ids happened not to be reused. Note that `tests/test_concurrency_loops.py` exists, so multiple-event-loop execution is an established pattern in this codebase.

### Fix

Identical to the fix already applied in `core/concurrency.py` — key by the loop **object** in a `weakref.WeakKeyDictionary`:

```python
_INGESTION_SEMAPHORES: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    weakref.WeakKeyDictionary()
)
```

Separately, move the semaphore acquisition inside the `try` so any future failure writes a terminal status instead of stranding the document.

---

## L1 — OCR confidence gate skipped when no per-line score is present

**`app/ingestion/ocr.py:95` and `:106-114`**

```python
score = float(entry[2]) if len(entry) > 2 else None
...
confidence = sum(scores) / len(scores) if scores else None
if confidence is not None and confidence < min_confidence:
```

The module docstring states "garbage must never become evidence" and the function docstring says text below `min_confidence` is dropped. When `lines` is non-empty but no entry carried a score, `confidence is None` and the guard short-circuits — the text is returned as full evidence despite having no confidence signal. `used=True` is recorded, so it is at least auditable.

**CODE-EVIDENCE** — triggering it requires RapidOCR to return 2-tuples instead of 3-tuples, which could not be produced without the optional `rapidocr_onnxruntime` dependency installed.

Fix: treat `confidence is None` as a failure when `lines` is non-empty.

---

## L2 — `parse_pdf` re-wraps its own `IngestionError`s

**`app/ingestion/parser.py:170-178` / `:180-184` / `:237-238`**

The size- and page-limit guards raise `IngestionError("PDF exceeds size limit")` *inside* the `try`, whose `except Exception` re-raises `IngestionError("Failed to parse PDF document")`. The distinct operator-facing message is destroyed; only `detail=str(exc)` survives. **Diagnostic only, not a crash.**

**CODE-EVIDENCE** — same double-wrap shape as the `parse_docx` traceback seen in M1's run.

---

## Categories that are clean

Worth recording, so a future audit does not re-spend effort here.

| Category | Result |
|---|---|
| **Path traversal** | Clean. `page_images.py` validates `kb_id`/`doc_id` against `[A-Za-z0-9_-]+` on both write (`:48`) and read (`:65-73`), with a `relative_to(base)` containment check. Filenames are reduced to `Path(raw_filename[:255]).name` and extension-allowlist-checked at `knowledge_bases.py:214-221` and `:344-354` before reaching the parser. |
| **Injection** | Clean. No `subprocess`, `os.system`, `eval` or `pickle` anywhere in the subsystem. |
| **Resource leaks** | Clean. `zipfile.ZipFile` and `fitz.open` are both context managers. No temp files, no `shutil.unpack_archive`, no zip-slip surface. `scan_for_malware` correctly restores stream position in `finally`. |
| **Unbounded whole-file reads** | Not reachable. `parse_csv`/`parse_json`/`parse_html`/`parse_txt_or_md` do `stream.read()` with no local cap, but both entry points enforce `max_file_size_mb` (20MB) before `parse_document` is called. |
| **Blocking I/O in async** | Clean in this subsystem. `parse_document` and the chunker are correctly dispatched via `asyncio.to_thread` at `knowledge_bases.py:155-162`; `trim_memory` is offloaded at `pipeline.py:313-315`. The real risk is the memory blowup in M1/M3 occurring in that worker thread. |
| **Other bare `except: pass`** | All intentional fail-open paths: `pipeline.py:105` (page-image save), `parser.py:427` (ImportError probe), `sparse_vector.py:59` (BM25 defaults, logged). |

## One deliberate trade-off, recorded not reported

`chunking_strategies.py:85-89` and `preprocessor.py:309` both test `isupper()` / `[A-Z0-9...]` on text that `normalize_text` has already lowercased, so the all-caps heading branch and the `HEADER` zone are effectively unreachable. Consequently `ZONE_WEIGHT_BOOSTS` title (2.0x) and header (1.5x) rarely apply, and sparse BM25 scoring diverges from the design.

This is **not** a bug: `chunking_strategies.py:83-84` carries an explicit comment acknowledging it, and it is a deliberate lexical-normalisation decision. Flagging it would be arguing with a recorded decision.

---

## Suggested order of work

1. **H1** — silent data loss on every HTML upload, one-line-class fix, needs a regression test.
2. **H2** — security control that only works when uninstalled; narrow the `except`.
3. **M5** — reuse the existing `WeakKeyDictionary` pattern from `core/concurrency.py`, and move the acquire inside the `try`.
4. **M4 + M2** — together: they are the same provenance defect seen from two directions, and the Phase-7 chain depends on both being right.
5. **M3** — reuse the guarded step, plus startup validation of the chunk settings.
6. **M1** — absolute ceiling on decompression, then bounded reads.
7. **L1, L2** — small and independent.
