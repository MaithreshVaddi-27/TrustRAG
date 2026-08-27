# SECURITY — TRUSTRAG

## Reporting Vulnerabilities

**Do not report security vulnerabilities via GitHub Issues.**

Email: [security@trustrag.example.com] (replace with actual contact)

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- (Optional) Suggested fix

You will receive a response within 48 hours.

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x (current) | ✅ |

---

## Security Controls Summary

See [docs/security/security-controls.md](docs/security/security-controls.md) for the full controls matrix.

Key controls:
- JWT authentication (all routes except `/health` and `/auth/*`)
- bcrypt password hashing
- IDOR prevention (ownership checked per resource)
- Prompt injection defense (UNTRUSTED DATA labeling in prompts)
- Rate limiting per IP
- No raw stack traces to clients
- Secret scrubbing in logs
- CI security scanning (pip-audit, npm audit, Bandit)

---

## Responsible Disclosure

We follow coordinated responsible disclosure. We ask that:
1. You give us reasonable time to fix before public disclosure
2. You do not exploit vulnerabilities in production
3. You do not access or modify user data without permission
