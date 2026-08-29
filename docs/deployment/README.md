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
4. Verify the configured model ID (`gemini-2.5-flash` in `models.yaml`) is available for your API key

> **Model ID verification:** Run `python -c "from app.core.model_registry import get_llm; print(get_llm())"` after setting up credentials.

---

## Backend Deployment

### Render (free tier)

1. Connect your GitHub repository to [render.com](https://render.com)
2. Create a new **Web Service**
3. Root directory: `apps/api`
4. Build command: `pip install -e .`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add all environment variables in the Render dashboard
7. Set `APP_ENV=production`

### Railway

1. Connect repository at [railway.app](https://railway.app)
2. Select `apps/api` as root
3. Railway auto-detects Python and uses `pyproject.toml`
4. Add environment variables

### Docker (any VPS)

```bash
docker build -t trustrag-api ./apps/api
docker run -p 8000:8000 --env-file .env trustrag-api
```

---

## Frontend Deployment

### Netlify (recommended for free tier)

1. Connect repository at [netlify.com](https://netlify.com)
2. Base directory: `apps/web`
3. Build command: `npm run build`
4. Publish directory: `dist`
5. Add environment variable: `VITE_API_BASE_URL=https://your-backend-url.com`

### Vercel

1. Import repository at [vercel.com](https://vercel.com)
2. Framework: **Vite**
3. Root directory: `apps/web`
4. Add `VITE_API_BASE_URL` environment variable

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
