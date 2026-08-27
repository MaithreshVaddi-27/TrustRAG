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
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
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

# Create model cache directory (sentence-transformers will write here)
RUN mkdir -p /app/.model_cache && chown trustrag:trustrag /app/.model_cache

# Drop to non-root
USER trustrag

# Health check — Docker will mark container unhealthy if this fails
# Use wget since it's available in python:slim and avoids curl dependency issues
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD wget -qO- http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

# Use exec form to correctly propagate signals
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "warning"]
