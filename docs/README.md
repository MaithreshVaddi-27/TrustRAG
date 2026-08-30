# TRUSTRAG Documentation Index

Welcome to the comprehensive technical documentation for the TRUSTRAG AI Reliability Workbench. This documentation directory is organized into specialized domains for architectural design, security controls, independent quality audits, evaluation methodology, and deployment operations.

---

## 📁 Documentation Structure

```
docs/
├── README.md                     # Master Documentation Directory Index (this file)
├── ROADMAP.md                    # Product vision, technical milestones, and phase tracking
├── architecture/
│   ├── architecture.md           # End-to-end system design, agent loop, and data flow
│   └── decision-log.md           # Architectural Decision Records (ADRs)
├── audits/
│   ├── final-audit-report.md     # Master quality audit sign-off matrix (35 findings FIXED / VERIFIED)
│   └── multi-tenant-isolation-audit.md # Multi-tenant isolation, cascade deletion & Qdrant health check
├── security/
│   ├── security-controls.md      # Authentication, IDOR isolation, rate limits, and defenses
│   └── threat-model.md           # STRIDE threat modeling and mitigations
├── evaluation/
│   └── methodology.md            # Benchmark evaluation dataset and custom reliability metrics
└── deployment/
    ├── DEPLOYMENT_GUIDE.md       # Master runbook: Cloudflare Pages, Google Cloud Run, Atlas, Qdrant
    └── README.md                 # Docker Compose, environment configuration, and scaling
```

---

## 📑 Core Documentation Sections

### 1. Architecture & Design
- [**System Architecture (`architecture/architecture.md`)**](architecture/architecture.md): Detailed breakdown of the LangGraph state machine, hybrid retrieval (dense + sparse BM25 with RRF), and claim decomposition pipeline.
- [**Decision Log (`architecture/decision-log.md`)**](architecture/decision-log.md): Architectural Decision Records (ADRs) covering technology choices, local embedding strategies, and storage layers.

### 2. Quality Audits & Verification
- [**Master Audit Report (`audits/final-audit-report.md`)**](audits/final-audit-report.md): Consolidated master verification report confirming 35 findings resolved, whitebox/blackbox matrices, and 0 remaining defects.
- [**Multi-Tenant Isolation Audit (`audits/multi-tenant-isolation-audit.md`)**](audits/multi-tenant-isolation-audit.md): Deep inspection of user data partitioning, anti-IDOR tests, Qdrant health checks, and cascade deletion.

### 3. Security & Compliance
- [**Security Controls (`security/security-controls.md`)**](security/security-controls.md): Specification of JWT tokens, bcrypt rounds, defensive HTTP response headers (`nosniff`, `DENY`), and prompt injection defenses.
- [**Threat Model (`security/threat-model.md`)**](security/threat-model.md): Detailed threat identification, attack trees, and defense-in-depth countermeasures.

### 4. Operations & Experiments
- [**Production Deployment Runbook (`deployment/DEPLOYMENT_GUIDE.md`)**](deployment/DEPLOYMENT_GUIDE.md): Complete step-by-step instructions for deploying to Cloudflare Pages, Google Cloud Run, MongoDB Atlas, and Qdrant Cloud.
- [**Local & VPS Deployment (`deployment/README.md`)**](deployment/README.md): Instructions for launching TRUSTRAG with Docker Compose, local MongoDB community edition, and Qdrant.
- [**Roadmap (`ROADMAP.md`)**](ROADMAP.md): Track completed development phases and upcoming roadmap initiatives.
