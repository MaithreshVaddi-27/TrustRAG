# TRUSTRAG — Master Production Deployment Runbook

> **Target Architecture**:
> - **Frontend**: Cloudflare Pages (React 18 / Vite SPA)
> - **Backend API**: Google Cloud Run (FastAPI / Uvicorn Serverless Container)
> - **Primary Database**: MongoDB Atlas (M0 Free Tier or Dedicated Cluster)
> - **Vector Database**: Qdrant Cloud (Managed Hybrid Vector Engine)
> - **Foundation Models**: Google Gemini API (`gemini-3.5-flash-lite`)

---

## 🧭 Deployment Order: What to Deploy First?

Deploying in the wrong sequence will cause build and startup failures. Follow this strict order:

```mermaid
graph TD
    A["Step 1: Data Plane<br/>(MongoDB Atlas + Qdrant Cloud + Gemini)"] --> B["Step 2: Backend API<br/>(Google Cloud Run)"]
    B --> C["Step 3: Frontend SPA<br/>(Cloudflare Pages)"]
    C --> D["Step 4: End-to-End Verification<br/>(Health, Auth, Ingest, Agentic RAG)"]
```

### Why this order?
1. **Data Plane First**: The backend container connects to MongoDB and Qdrant during its FastAPI startup lifespan. If database credentials do not exist, the container will fail its health check and Cloud Run will abort deployment.
2. **Backend Second**: Google Cloud Run assigns a unique HTTPS URL (e.g. `https://trustrag-api-<hash>-<region>.a.run.app`) upon deployment.
3. **Frontend Third**: Vite injects `VITE_API_URL` at **build time**. You must know your Cloud Run backend URL *before* deploying to Cloudflare Pages so the frontend bundle compiles with the correct API target.
4. **Verification Last**: Once both are live, test user registration, document upload, and claim verification end-to-end.

---

## 🛠️ Step 1: Provision the Data Plane

### 1.1 MongoDB Atlas Setup
1. Log in to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Create a project named `TRUSTRAG` and deploy an **M0 Free Cluster** (Shared) in your preferred region.
3. **Configure Database Access**:
   - Go to **Security** → **Database Access** → **Add New Database User**.
   - Select **Password Authentication**.
   - Create user (e.g., `trustrag_admin`) with a strong password.
   - Assign Role: **Read and write to any database** (or `readWrite@trustrag_db`).
4. **Configure Network Access**:
   - Go to **Security** → **Network Access** → **Add IP Address**.
   - Click **Allow Access from Anywhere** (`0.0.0.0/0`).
   - *(Required because Google Cloud Run uses dynamic egress IP addresses unless routed through a VPC Connector with Cloud NAT).*
5. **Obtain Connection String**:
   - Go to **Database** → **Clusters** → **Connect** → **Drivers** → **Python**.
   - Copy connection URI. It has the structure:
     ```
     mongodb+srv://trustrag_admin:<PASSWORD>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
     ```

### 1.2 Qdrant Cloud Setup
1. Log in to [Qdrant Cloud Console](https://cloud.qdrant.io/).
2. Click **Create Cluster** and select the **Free Tier (1 GB RAM / 0.5 vCPU)**.
3. Once provisioned, note:
   - **Cluster Endpoint URL**: e.g., `https://xyz-abc.us-east-1.gcp.cloud.qdrant.io:6333`
4. Go to **API Keys** and click **Create Key**. Copy the generated API key.

### 1.3 Google AI Studio (Gemini API)
1. Go to [Google AI Studio API Keys](https://aistudio.google.com/app/apikey).
2. Click **Create API Key** and copy your `GEMINI_API_KEY`.
3. Verify access to `gemini-3.5-flash-lite` (standard free quota available).

### 1.4 Generate JWT Secret
Run this in your local terminal to create a cryptographic 64-byte secret:
```bash
python3 -c "import secrets; print(secrets.token_hex(64))"
```

---

## 🚀 Step 2: Deploy Backend to Google Cloud Run

### 2.1 Prerequisites
Ensure the Google Cloud SDK (`gcloud`) is installed and authenticated:
```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

### 2.2 Direct Source Deployment
From the project root, execute:

```bash
gcloud run deploy trustrag-api \
  --source apps/api \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "\
APP_ENV=production,\
MONGODB_DATABASE=trustrag_db,\
MONGODB_URI=mongodb+srv://trustrag_admin:YOUR_PASSWORD@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority,\
JWT_SECRET=YOUR_64_CHAR_GENERATED_JWT_SECRET,\
GEMINI_API_KEY=YOUR_GEMINI_API_KEY,\
QDRANT_URL=https://xyz-abc.us-east-1.gcp.cloud.qdrant.io:6333,\
QDRANT_API_KEY=YOUR_QDRANT_API_KEY,\
CORS_ORIGINS=https://localhost:5173"
```

> **Why 2Gi Memory and 2 CPU?**
> Sentence Transformers runs locally inside the container to embed chunks without external API latency. 2Gi RAM guarantees smooth operation and model caching without Out-Of-Memory (OOM) pauses.

### 2.3 Verify Backend Deployment
Upon completion, Cloud Run outputs your Service URL:
```
Service URL: https://trustrag-api-91823719283-uc.a.run.app
```

Test the live health check endpoint:
```bash
curl -s https://trustrag-api-91823719283-uc.a.run.app/api/v1/health | jq
```

Expected JSON response:
```json
{
  "status": "ok",
  "app": "TRUSTRAG",
  "version": "0.1.0",
  "environment": "production",
  "services": {
    "mongodb": "ok",
    "qdrant": "ok"
  },
  "supported_formats": ["pdf", "txt", "md", "docx", "csv", "json", "html", "htm"]
}
```

---

## ⚡ Step 3: Deploy Frontend to Cloudflare Pages

### Option A: Git Integration via Cloudflare Dashboard (Recommended)

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**.
2. Select your repository: `TrustRAG-latest`.
3. Configure Build Settings:
   - **Project name**: `trustrag`
   - **Production branch**: `main`
   - **Framework preset**: `Vite`
   - **Root directory**: `apps/web`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
4. Expand **Environment variables (production)**:
   - Add variable:
     - **Variable name**: `VITE_API_URL`
     - **Value**: `https://trustrag-api-91823719283-uc.a.run.app` *(Your Cloud Run Service URL from Step 2)*
5. Click **Save and Deploy**.

### Option B: Deploy via Wrangler CLI

If deploying directly from your local terminal:
```bash
cd apps/web
npm install

# Build with Cloud Run URL injected
VITE_API_URL="https://trustrag-api-91823719283-uc.a.run.app" npm run build

# Deploy to Cloudflare Pages
npx wrangler pages deploy dist --project-name trustrag
```

### Verification
Cloudflare will provide your live deployment URL:
```
https://trustrag.pages.dev
```

---

## 🔗 Step 4: Link CORS & Verify Production

### 4.1 Update Cloud Run CORS Origins
The backend automatically accepts `allow_origin_regex=r"^https:\/\/([a-zA-Z0-9_\-]+\.)*pages\.dev$"` out of the box.

If you attach a custom domain (e.g., `https://trustrag.yourdomain.com`), update Cloud Run:
```bash
gcloud run services update trustrag-api \
  --region us-central1 \
  --update-env-vars "CORS_ORIGINS=https://trustrag.pages.dev,https://trustrag.yourdomain.com"
```

---

## 🧪 Step 5: End-to-End Smoke Test Run

Perform a complete workflow verification on your live Cloudflare Pages URL:

1. **Access Web App**: Open `https://trustrag.pages.dev`.
2. **Account Registration**:
   - Navigate to `/register` and create an account.
   - Verify immediate redirect to `/login` and successful JWT token session creation.
3. **Check System Diagnostics**:
   - Go to `/settings`.
   - Verify green status pills for **MongoDB (Connected)** and **Qdrant (Connected)**.
   - Confirm active models show `gemini-3.5-flash-lite` and `all-MiniLM-L6-v2`.
4. **Knowledge Base Creation & Ingestion**:
   - Navigate to `/knowledge-bases`.
   - Click **New Knowledge Base** → name it `Compliance & Security`.
   - Upload any sample document (`.pdf`, `.docx`, `.csv`, `.json`, `.html`, or `.txt`).
   - Verify status transitions from `pending` → `completed`.
5. **Run Agentic Analysis in Playground**:
   - Go to `/playground`.
   - Select your Knowledge Base and ask a question grounded in your uploaded document.
   - Observe live SSE execution trace stream events.
   - Verify atomic claim decomposition and NLI verdict (`TRUSTED`).
6. **Export Verification Dossier**:
   - In Playground, click **Export Audit (JSON-LD)**.
   - Confirm that schema.org compliance JSON-LD with claim triples downloads cleanly.

---

## 🛡️ Production Best Practices & Gotchas

| Issue / Topic | Description & Solution |
| :--- | :--- |
| **Cloud Run Cold Starts** | The `apps/api/Dockerfile` automatically pre-downloads `all-MiniLM-L6-v2` during Docker build, eliminating runtime Hugging Face downloads. Set `--min-instances 1` if you require 0ms cold starts. |
| **MongoDB Atlas Free Tier Sleep** | M0 clusters auto-pause on inactivity. TRUSTRAG's `mongodb.py` includes a 2.5-minute exponential backoff retry loop that waits for Atlas to wake up without crashing the container. |
| **Cloudflare Pages SPA 404s** | [`apps/web/public/_redirects`](apps/web/public/_redirects) routes `/* /index.html 200`. Direct page refreshes on `/playground`, `/evidence`, etc., will never throw 404 errors. |
| **Qdrant Authentication** | In `APP_ENV=production`, `QDRANT_API_KEY` is strictly required by Pydantic validator. Ensure your Qdrant Cloud key is set. |
| **Secrets Management** | For enhanced enterprise security on Google Cloud, use Google Secret Manager: `gcloud secrets create trustrag-jwt-secret --data-file=-` and reference via `--set-secrets`. |
