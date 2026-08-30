# TRUSTRAG — Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables](#environment-variables)
3. [Local Development](#local-development)
4. [MongoDB Atlas Setup](#mongodb-atlas-setup)
5. [Qdrant Cloud Setup](#qdrant-cloud-setup)
6. [Gemini API Setup](#gemini-api-setup)
7. [Backend Deployment](#backend-deployment)
8. [Frontend Deployment](#frontend-deployment)
9. [CORS Configuration](#cors-configuration)
10. [Health Checks](#health-checks)
11. [Indexing & Re-indexing](#indexing--re-indexing)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose (for local dev)
- Git

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google AI Studio API key |
| `MONGODB_URI` | Yes | MongoDB Atlas connection string |
| `MONGODB_DATABASE` | Yes | Database name (default: `trustrag_db`) |
| `QDRANT_URL` | Yes | Qdrant URL (local: `http://localhost:6333`) |
| `QDRANT_API_KEY` | Prod only | Qdrant Cloud API key |
| `JWT_SECRET` | Yes | Min 32-char random secret |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins |
| `APP_ENV` | Yes | `development` \| `staging` \| `production` |
| `LOG_LEVEL` | No | `INFO` (default) |

Generate a strong JWT secret:
```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

---

## Local Development

### Option 1: Docker Compose (recommended)

```bash
# 1. Set up environment
cp .env.example .env
# Fill in GEMINI_API_KEY and MONGODB_URI in .env
# QDRANT_URL will be overridden to http://qdrant:6333 by docker-compose

# 2. Start services
docker compose up

# 3. Verify
curl http://localhost:8000/api/v1/health
# Frontend: http://localhost:5173
```

### Option 2: Manual

```bash
# Backend
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd apps/web
npm install
npm run dev
```

> **First run note:** sentence-transformers will download `all-MiniLM-L6-v2` (~90MB) on first startup. Subsequent starts use the cache.

---

## MongoDB Atlas Setup

1. Create a free account at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a **free M0 cluster** (512MB storage — sufficient for MVP)
3. Create a database user with read/write access
4. Whitelist your IP address (or `0.0.0.0/0` for development — not recommended for production)
5. Get the connection string: `Clusters → Connect → Connect your application → Python`
6. Set `MONGODB_URI` in `.env`

> **Free tier note:** M0 clusters have a 500 connections limit and no dedicated RAM. Sufficient for MVP.

---

## Qdrant Cloud Setup

For production, use Qdrant Cloud free tier:

1. Create account at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a free cluster (1GB storage)
3. Get the cluster URL and API key
4. Set `QDRANT_URL` and `QDRANT_API_KEY` in `.env`

For local development, use the Docker Compose Qdrant service:
```
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=   # empty = no auth
```

---

## Gemini API Setup

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create an API key (free tier available)
3. Set `GEMINI_API_KEY` in `.env`
4. Verify the configured model ID (`gemini-3.5-flash-lite` in `config/models.yaml`) is available for your API key

> **Model ID verification:** Run `python -c "from app.core.model_registry import get_llm; print(get_llm())"` after setting up credentials.

---

## Backend Deployment

### Google Cloud Run (Recommended for Production)

Google Cloud Run provides fully managed serverless container execution with automatic scaling, zero idle cost, and native container support.

1. **Install and authenticate Google Cloud SDK**:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_GCP_PROJECT_ID
   ```

2. **Deploy directly from the repository**:
   ```bash
   gcloud run deploy trustrag-api \
     --source apps/api \
     --region us-central1 \
     --platform managed \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2 \
     --timeout 300 \
     --set-env-vars "APP_ENV=production,MONGODB_DATABASE=trustrag_db" \
     --set-secrets "MONGODB_URI=trustrag-mongodb-uri:latest,JWT_SECRET=trustrag-jwt-secret:latest,GEMINI_API_KEY=trustrag-gemini-key:latest,QDRANT_URL=trustrag-qdrant-url:latest,QDRANT_API_KEY=trustrag-qdrant-key:latest"
   ```
   *(Or pass environment variables via `--set-env-vars` if Secret Manager is not yet configured).*

3. **Cloud Run Container Specifications**:
   - **Port**: Google Cloud Run automatically provides `$PORT` (default `8080`). The Dockerfile dynamically binds to `${PORT:-8000}`.
   - **Memory**: Minimum **1.5GiB - 2GiB** recommended so Sentence Transformers can load and cache dense embedding weights (`all-MiniLM-L6-v2`) in memory.
   - **Execution Environment**: Second Generation (`--execution-environment gen2`).

4. **Obtain your Backend URL**:
   After deployment, Cloud Run provides a secure HTTPS URL:
   ```
   https://trustrag-api-<hash>-<region>.a.run.app
   ```
   Verify health:
   ```bash
   curl https://trustrag-api-<hash>-<region>.a.run.app/api/v1/health
   ```

### Docker (any VPS / Virtual Machine)

```bash
docker build -t trustrag-api ./apps/api
docker run -p 8000:8000 --env-file .env trustrag-api
```

---

## Frontend Deployment

### Cloudflare Pages (Recommended for Production)

Cloudflare Pages provides global CDN edge delivery with zero-config preview deployments and custom domains.

#### Method A: Git Integration (Recommended)
1. Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com/) and navigate to **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**.
2. Select your `TrustRAG` repository.
3. Configure the build parameters:
   - **Project name**: `trustrag`
   - **Production branch**: `main`
   - **Framework preset**: `Vite`
   - **Root directory**: `apps/web`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
4. Under **Environment variables**, set:
   - `VITE_API_URL`: `https://trustrag-api-<hash>-<region>.a.run.app` (your Cloud Run backend URL).
5. Click **Save and Deploy**.

#### Method B: Direct Upload via Wrangler CLI
```bash
cd apps/web
npm install
VITE_API_URL="https://trustrag-api-<hash>-<region>.a.run.app" npm run build
npx wrangler pages deploy dist --project-name trustrag
```

#### SPA Routing & Security Headers
The repository automatically includes:
- `apps/web/public/_redirects`: Routes all SPA paths (`/playground`, `/knowledge-bases`, `/evidence`, `/claims`, etc.) to `/index.html 200` without 404s.
- `apps/web/public/_headers`: Enforces `X-Frame-Options: DENY`, `nosniff`, and cache rules on immutable static bundles.

### Vercel / Netlify (Alternative)

- Root directory: `apps/web`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_URL=https://your-cloud-run-url.a.run.app`

---

## CORS Configuration

Set `CORS_ORIGINS` to match your frontend URL:

```env
# Development
CORS_ORIGINS=http://localhost:5173

# Production
CORS_ORIGINS=https://trustrag.netlify.app

# Multiple origins
CORS_ORIGINS=https://trustrag.netlify.app,https://trustrag.vercel.app
```

---

## Health Checks

```bash
# Application health + service status + active model config
GET /api/v1/health

# Expected response
{
  "status": "ok",
  "timestamp": "2026-08-27T10:00:00Z",
  "app": "TRUSTRAG",
  "version": "0.1.0",
  "services": {
    "mongodb": "ok"
  },
  "models": {
    "config_version": "1.0",
    "llm_model": "gemini-2.5-flash",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    ...
  }
}
```

---

## Indexing & Re-indexing

MongoDB indexes are created automatically on startup (idempotent).

When you change the embedding model in `models.yaml`:
1. Increment `embedding.version`
2. All existing Qdrant collections become stale
3. Re-ingest documents: delete the old Qdrant collection and re-upload documents
4. The system will detect embedding version mismatches and warn

---

## Troubleshooting

### API returns 503 on startup

Check MongoDB connectivity:
```bash
curl http://localhost:8000/api/v1/health
# Look for "mongodb": "degraded"
```

Verify `MONGODB_URI` is correct and Atlas IP whitelist includes your server IP.

### Embedding model slow on first request

`sentence-transformers/all-MiniLM-L6-v2` downloads on first use (~90MB). Subsequent requests use the cache. Mount a persistent volume for `.model_cache` in Docker.

### Gemini API errors

- Verify `GEMINI_API_KEY` is set
- Verify `gemini-2.5-flash` model is available in your region/plan at [AI Studio](https://aistudio.google.com)
- Check rate limits (Gemini free tier: 15 RPM, 1M tokens/day)

### CORS errors in browser

Ensure `CORS_ORIGINS` in `.env` exactly matches your frontend origin (including protocol and port).
