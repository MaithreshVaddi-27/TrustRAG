# ─────────────────────────────────────────────────────────────────────────────
# TRUSTRAG API — Multi-stage Dockerfile
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 (builder): install dependencies in a venv
# Stage 2 (runtime): copy only the venv + source, no build tools
#
# Security:
#   - Runs as non-root user (trustrag)
#   - No dev tools in the runtime image
#   - Secrets injected via environment at runtime — never baked into image
# ─────────────────────────────────────────────────────────────────────────────

# ── Builder ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed only for building native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create isolated venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency spec and install
COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir ".[dev]"


# ── Runtime ───────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system dependencies (minimal)
# ca-certificates is included so TLS handshakes to MongoDB Atlas / Gemini use
# an up-to-date root store, not whatever shipped with the base image layer.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1001 trustrag && \
    useradd --uid 1001 --gid 1001 --no-create-home trustrag

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY --chown=trustrag:trustrag app/ ./app/
COPY --chown=trustrag:trustrag config/ ./config/

ARG HF_TOKEN=""
ENV HF_TOKEN=${HF_TOKEN}

# Create model cache directory and pre-cache embedding weights for instant container startup
RUN mkdir -p /app/.model_cache && \
    python -c "import os; from sentence_transformers import SentenceTransformer; token = os.environ.get('HF_TOKEN') or None; SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L3-v2', cache_folder='/app/.model_cache', token=token)" && \
    chown -R trustrag:trustrag /app/.model_cache

# Drop to non-root
USER trustrag

# Health check — Docker will mark container unhealthy if this fails
# Use wget since it's available in python:slim and avoids curl dependency issues
# start_period is generous because startup now retries the MongoDB Atlas
# connection with backoff (up to ~2.5 min) to ride out M0 cluster auto-resume
# instead of crashing on the first slow handshake — see app/db/mongodb.py.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD sh -c 'wget -qO- "http://localhost:${PORT:-8000}/api/v1/health" || exit 1'

# Use exec in shell form so $PORT provided by Cloud Run is dynamically respected
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level warning"]
