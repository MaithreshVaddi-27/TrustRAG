# TRUSTRAG Documentation Index

Welcome to the comprehensive technical documentation for the TRUSTRAG AI Reliability Workbench. This documentation directory is organized into specialized domains for architectural design, security controls, independent quality audits, evaluation methodology, and deployment operations.

---

## 📁 Documentation Structure

```
docs/
├── README.md                     # Master Documentation Directory Index (this file)
├── ROADMAP.md                    # Product vision, technical milestones, and phase tracking
├── audit/                        # Comprehensive SOTA multi-perspective production audit suite
│   ├── comprehensive_audit_report.md  # Master systems, security, AI/ML, and QA audit
│   ├── security_audit.md              # Deep DevSecOps, anti-IDOR, and cryptographic integrity audit
│   ├── ai_ml_performance_audit.md     # 384d MRL, zero GPU RAM, and hybrid RRF benchmark
│   ├── qa_testing_report.md           # 86/86 Automated whitebox & blackbox test verification
│   └── areas_for_improvement_and_refactoring.md # Technical debt & modernization blueprint
├── architecture/
│   ├── architecture.md           # End-to-end system design, MCP tools, LangGraph loop, and data flow
│   └── decision-log.md           # Architectural Decision Records (ADRs D-01 through D-17)
├── audits/
│   ├── final-audit-report.md     # Master quality audit sign-off matrix (35 findings FIXED / VERIFIED)
│   └── multi-tenant-isolation-audit.md # Multi-tenant isolation, cascade deletion & Qdrant health check
├── security/
│   ├── security-controls.md      # Authentication, IDOR isolation, rate limits, SSRF, and defenses
│   └── threat-model.md           # STRIDE threat modeling and mitigations
├── evaluation/
│   └── methodology.md            # Benchmark evaluation dataset and custom reliability metrics
└── deployment/
    ├── DEPLOYMENT_GUIDE.md       # Master runbook: Cloudflare Pages, Google Cloud Run (Port 8080), Atlas, Qdrant
    └── README.md                 # Docker Compose, environment configuration, and scaling
```

---

## 📑 Core Documentation Sections

### 1. Architecture & Design
- [**System Architecture (`architecture/architecture.md`)**](architecture/architecture.md): Detailed breakdown of the LangGraph state machine, Model Context Protocol (MCP) server/tools, hybrid retrieval (dense + sparse BM25 with RRF), and claim decomposition pipeline.
- [**Decision Log (`architecture/decision-log.md`)**](architecture/decision-log.md): Architectural Decision Records (ADRs) covering technology choices, Port 8080 default, MCP grounding, and storage layers.

### 2. SOTA Production Audit Suite
- [**Comprehensive Master Audit (`audit/comprehensive_audit_report.md`)**](audit/comprehensive_audit_report.md): Synthesis across Systems, Security, AI/ML, and QA with 0 open issues.
- [**Deep Security & DevSecOps (`audit/security_audit.md`)**](audit/security_audit.md): Physical collection isolation, anti-IDOR defense, SSRF URL sanitization, and cryptographic SHA-256 provenance.
- [**AI/ML Performance & Latency (`audit/ai_ml_performance_audit.md`)**](audit/ai_ml_performance_audit.md): Matryoshka 384d MRL embeddings, hybrid RRF search, and zero local GPU RAM operation.
- [**Quality Assurance Testing Report (`audit/qa_testing_report.md`)**](audit/qa_testing_report.md): 86/86 automated tests across whitebox and blackbox test suites.
- [**Modernization & Refactoring Blueprint (`audit/areas_for_improvement_and_refactoring.md`)**](audit/areas_for_improvement_and_refactoring.md): Qdrant on-disk INT8 quantization, LRU embedding caching, and container pruning.

### 3. Security & Compliance
- [**Security Controls (`security/security-controls.md`)**](security/security-controls.md): Specification of JWT tokens, bcrypt rounds, defensive HTTP response headers (`nosniff`, `DENY`), SSRF guards, and prompt injection defenses.
- [**Threat Model (`security/threat-model.md`)**](security/threat-model.md): Detailed threat identification, attack trees, and defense-in-depth countermeasures.

### 4. Operations & Experiments
- [**Production Deployment Runbook (`deployment/DEPLOYMENT_GUIDE.md`)**](deployment/DEPLOYMENT_GUIDE.md): Complete step-by-step instructions for deploying to Cloudflare Pages, Google Cloud Run (Port 8080), MongoDB Atlas, and Qdrant Cloud.
- [**Local & VPS Deployment (`deployment/README.md`)**](deployment/README.md): Instructions for launching TRUSTRAG with Docker Compose, local MongoDB community edition, and Qdrant.
- [**Roadmap (`ROADMAP.md`)**](ROADMAP.md): Track completed development phases and upcoming roadmap initiatives.
