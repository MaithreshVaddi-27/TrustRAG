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
│   ├── audit-plan.md             # Quality audit methodology, rules, and scope matrix
│   ├── audit-findings.md         # Full findings register with P0–P3 severity scoring
│   ├── fix-plan.md               # Phased remediation plan for static, type, and security issues
│   ├── final-audit-report.md     # Final audit sign-off matrix (all findings FIXED / VERIFIED)
│   ├── post-audit-fix-log.md     # Chronological execution log of all fixes and root causes
│   ├── line-by-line-review.md    # Deep line-by-line inspection of critical agent & verification code
│   └── audit-v3.md               # Historical baseline security and architectural audit report
├── security/
│   ├── security-controls.md      # Authentication, IDOR isolation, rate limits, and defenses
│   └── threat-model.md           # STRIDE threat modeling and mitigations
├── evaluation/
│   └── methodology.md            # Benchmark evaluation dataset and custom reliability metrics
└── deployment/
    └── README.md                 # Docker Compose, environment configuration, and scaling
```

---

## 📑 Core Documentation Sections

### 1. Architecture & Design
- [**System Architecture (`architecture/architecture.md`)**](architecture/architecture.md): Detailed breakdown of the LangGraph state machine, hybrid retrieval (dense + sparse BM25 with RRF), and claim decomposition pipeline.
- [**Decision Log (`architecture/decision-log.md`)**](architecture/decision-log.md): Architectural Decision Records (ADRs) covering technology choices, local embedding strategies, and storage layers.

### 2. Quality Audits & Verification
- [**Audit Plan (`audits/audit-plan.md`)**](audits/audit-plan.md): Standards, tooling, and evaluation rules across UI/UX, FE, BE, DB, SEC, A11Y, PERF, TEST, and DEVOPS.
- [**Audit Findings (`audits/audit-findings.md`)**](audits/audit-findings.md): Matrix of 23 discovered items with evidence, impact, and verification criteria.
- [**Remediation Plan (`audits/fix-plan.md`)**](audits/fix-plan.md): Prioritized step-by-step fix procedures (P0 → P1 → P2 → P3).
- [**Final Audit Report (`audits/final-audit-report.md`)**](audits/final-audit-report.md): Post-fix verification report confirming zero remaining defects across all categories.
- [**Post-Audit Fix Log (`audits/post-audit-fix-log.md`)**](audits/post-audit-fix-log.md): Detailed chronological log of all code changes, root-cause analyses, and verification commands.
- [**Line-by-Line Review (`audits/line-by-line-review.md`)**](audits/line-by-line-review.md): Component-level code walkthrough across graph transitions, NLI verification, and text preprocessors.

### 3. Security & Compliance
- [**Security Controls (`security/security-controls.md`)**](security/security-controls.md): Specification of JWT tokens, bcrypt rounds, defensive HTTP response headers (`nosniff`, `DENY`), and prompt injection defenses.
- [**Threat Model (`security/threat-model.md`)**](security/threat-model.md): Detailed threat identification, attack trees, and defense-in-depth countermeasures.

### 4. Operations & Experiments
- [**Evaluation Methodology (`evaluation/methodology.md`)**](evaluation/methodology.md): Scoring models for verification coverage, contradiction rates, and reliability metrics.
- [**Deployment Guide (`deployment/README.md`)**](deployment/README.md): Instructions for launching TRUSTRAG with Docker Compose, local MongoDB community edition, and Qdrant.
- [**Roadmap (`ROADMAP.md`)**](ROADMAP.md): Track completed development phases and upcoming roadmap initiatives.
