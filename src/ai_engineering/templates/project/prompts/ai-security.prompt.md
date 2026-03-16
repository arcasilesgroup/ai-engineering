---
description: "Unified security scanning: SAST, DAST, dependency audit, SBOM generation. Modes: static | dynamic | deps | sbom."
mode: "agent"
---


# Security

## Purpose

Unified security assessment covering static analysis (SAST), dynamic analysis (DAST), dependency auditing, and SBOM generation. Each mode produces a structured report with severity-classified findings, OWASP Top 10 2025 mapping, and actionable remediation. The goal is to catch vulnerabilities before they reach production -- not to generate noise.

## Trigger

- Command: `/ai:verify security` or `/ai:security [static|dynamic|deps|sbom]`
- Context: security review, pre-release security gate, dependency audit, compliance reporting.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"security"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

## When NOT to Use

- **Code quality metrics** (coverage, complexity) -- use `quality`.
- **Architecture drift or coupling** -- use `architecture`.
- **Performance bottlenecks** -- use `perf`.
- **Governance contract compliance** -- use `governance`.
- **Risk acceptance recording** -- use `risk`.
- **Writing or fixing code** -- this skill reports. Delegate fixes to `ai:build`.

## Modes

### static -- SAST Review

Detect source code vulnerabilities without execution. Covers OWASP A01-A03, A05, A07, A09, A10.

#### Procedure

1. **Detect stacks** -- read install-manifest for active stacks (Python, .NET, TypeScript, Rust).
2. **Run secret detection** -- `gitleaks detect --source . --no-git` (full) or `gitleaks protect --staged` (pre-commit). Any finding is severity critical.
3. **Run semgrep** -- `semgrep scan --config auto --json`. Parse JSON for rule IDs, severity, CWE.
4. **Optional Snyk SAST** -- if `SNYK_TOKEN` set, run `snyk code test --json`. Merge and deduplicate by CWE + location.
5. **Manual code analysis** -- review what tools miss:
   - Every endpoint enforces authentication (A01).
   - Parameterized queries only -- no string concatenation in SQL/ORM (A03).
   - Secrets from environment or vault, never hardcoded (A02).
   - HTTP security headers: HSTS, CSP, X-Frame-Options (A05).
   - No user-controlled URLs passed to HTTP clients (A10).
   - Sensitive data excluded from logs (A09).
6. **Classify findings** -- assign severity and OWASP category per the severity table.
7. **Report** -- produce scan output contract.

#### What to Look For

| Pattern | OWASP | Why |
|---------|-------|-----|
| Hardcoded secrets, API keys, tokens | A02 | Direct credential exposure |
| SQL string concatenation, f-string queries | A03 | SQL injection |
| `eval()`, `exec()`, `subprocess` with user input | A03 | Command injection |
| Missing `[Authorize]` / auth middleware | A01 | Broken access control |
| Weak hashing (MD5, SHA1 for passwords) | A02 | Cryptographic failure |
| `HttpClient` with user-controlled URL | A10 | SSRF |
| Debug mode in production config | A05 | Security misconfiguration |

#### Example Finding

`semgrep` flags `cursor.execute(f"SELECT * FROM users WHERE id={user_id}")` in `app/db.py:87`.
Severity: **Critical**. Category: A03 Injection.
Remediation: `cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))`.

### dynamic -- DAST Review

Test running applications and infrastructure for runtime vulnerabilities. Covers A04, A05, A06, A08.

#### Procedure

1. **Check prerequisites** -- verify target URL or container image exists. If none, suggest `static` mode.
2. **Container scanning** -- `trivy image <image> --severity HIGH,CRITICAL --format json`. Parse for CVEs.
3. **Web application scanning** -- `nuclei -u <target> -severity high,critical -json` and/or `zap-cli quick-scan <target>`.
4. **IaC scanning** -- if Terraform/K8s manifests exist, `trivy config . --severity HIGH,CRITICAL --format json`.
5. **Classify** -- container CVEs map to A06, misconfigurations to A05.
6. **Report** -- produce scan output contract.

#### Example Finding

`trivy` detects CVE-2024-3094 (CVSS 10.0) in `xz-utils` inside the production image.
Severity: **Blocker**. Category: A06 Vulnerable Components.
Remediation: Rebuild with patched base. Pin image digest. Add image scanning to CI.

### deps -- Dependency Audit

Scan dependency manifests for known vulnerabilities. Covers A06.

#### Procedure

1. **Detect lock files** -- `uv.lock` / `requirements.txt`, `package-lock.json`, `*.csproj`, `Cargo.lock`.
2. **Run audit tools** -- Python: `pip-audit --strict --desc`. Node: `npm audit --json`. .NET: `dotnet list package --vulnerable`. Rust: `cargo audit --json`.
3. **Optional Snyk SCA** -- if `SNYK_TOKEN` set, run `snyk test --json`. Merge and deduplicate by CVE.
4. **Assess exploitability** -- determine if vulnerable code paths are reachable. Mark unreachable as reduced severity with justification.
5. **Report** -- produce scan output contract with upgrade paths.

#### Severity Signals

| Signal | Severity | Action |
|--------|----------|--------|
| Critical CVE with known exploit | Blocker | Upgrade immediately, block release |
| High CVE in direct dependency | Critical | Upgrade in current sprint |
| High CVE in transitive dependency | Major | Upgrade or pin safe version |
| Medium CVE, no known exploit | Minor | Track, upgrade at maintenance |
| Unmaintained dependency (>2 years) | Major | Evaluate alternatives |

### sbom -- Software Bill of Materials

Generate machine-readable component inventory. Supports compliance and supply chain security (A08).

#### Procedure

1. **Detect stacks** -- same as deps mode.
2. **Generate SBOM** -- `cdxgen -o sbom.json --spec-version 1.5` (multi-stack) or `cyclonedx-py` (Python-only). Format: CycloneDX JSON.
3. **Validate** -- verify output contains: all direct deps with versions, transitive deps to depth 2, license info, package URLs (purl).
4. **Flag license risks** -- copyleft (GPL, AGPL) in dependencies conflicting with project license. Mark as major.
5. **Report** -- produce scan output contract. Attach SBOM path.

## Severity Classification

| Severity | Definition | Gate Impact | Examples |
|----------|-----------|-------------|----------|
| **Blocker** | Actively exploitable, breach imminent | Blocks release. Zero tolerance. | Exposed secret, RCE, critical CVE with public exploit |
| **Critical** | High-impact, exploit feasible | Blocks release. Zero tolerance. | SQL injection, broken auth on public endpoint |
| **Major** | Significant risk, requires conditions | Must resolve before next release. | XSS in auth-only page, medium CVE, missing headers |
| **Minor** | Low risk, defense-in-depth | Resolve during maintenance. | Verbose errors, informational CVE, missing rate limiting |
| **Info** | Best-practice deviation | Address opportunistically. | Suboptimal cipher order, outdated unaffected dep |

Score: start at 100. Deduct per finding: blocker -30, critical -20, major -10, minor -3, info -1. Floor at 0.

## OWASP Top 10 2025 Mapping

Reference `standards/framework/security/owasp-top10-2025.md` for full control descriptions.

| # | Category | Primary Mode | Tools |
|---|----------|-------------|-------|
| A01 | Broken Access Control | static | semgrep |
| A02 | Cryptographic Failures | static | gitleaks, semgrep |
| A03 | Injection | static | semgrep |
| A04 | Insecure Design | static | Manual analysis |
| A05 | Security Misconfiguration | static + dynamic | semgrep, trivy, nuclei |
| A06 | Vulnerable Components | deps + dynamic | pip-audit, npm audit, cargo audit, trivy |
| A07 | Auth Failures | static | semgrep, gitleaks |
| A08 | Integrity Failures | sbom | cdxgen, cyclonedx-py |
| A09 | Logging Failures | static | semgrep, manual analysis |
| A10 | SSRF | static | semgrep |

## Remediation Patterns

### Secrets in Source Code
Remove immediately. Rotate the credential -- assume compromised. Store in environment variables or vault. Verify with `gitleaks protect --staged`.

### SQL Injection
Replace string concatenation with parameterized queries. Python: `cursor.execute("... WHERE id=%s", (val,))`. .NET: `SqlParameter` or EF LINQ. Node: Knex/Prisma query builder.

### Missing Authentication
Add auth middleware to the route. .NET: `[Authorize]` attribute. Next.js: middleware check. Verify with test that unauthenticated returns 401.

### Vulnerable Dependency
Check reachability. If reachable: upgrade and test. If unreachable: record in `decision-store.json` with expiry. If no patch: evaluate alternatives.

### Container Vulnerabilities
Update base image to patched version. Pin by digest. Use multi-stage builds. Add `trivy image` to CI.

## Output Contract

Every mode produces this format, per the verify agent's uniform contract.

```markdown
# Scan Report: security / [mode]

## Score: N/100
## Verdict: PASS (>=80) | WARN (60-79) | FAIL (<60)

## Findings
| # | Severity | OWASP | CWE | Description | Location | Remediation |

## Tool Outputs
- gitleaks: [N findings / clean]
- semgrep: [N findings / clean]
- (other tools as applicable)

## Signals
{ "mode": "security", "sub_mode": "<mode>", "score": N, "findings": { "blocker": 0, "critical": N, "major": N, "minor": N }, "timestamp": "..." }

## Gate Check
- Blocker findings: N (threshold: 0)
- Critical findings: N (threshold: 0)
- Any secret detected: [yes/no] (threshold: no)
- Verdict justification: ...
```

## Governance Notes

- Read-only for code -- produces reports, does not modify source.
- Read-write for audit log -- emits signals via `ai-eng signals emit`.
- Blocker and critical findings block release. Zero tolerance per `standards/framework/core.md`.
- Check `state/decision-store.json` for existing risk acceptances before reporting. Reference active decisions instead of duplicating.
- Max 3 tool-failure retries before escalating with evidence.
- If a tool is unavailable, skip it and note the coverage gap in the report.

## References

- `standards/framework/security/owasp-top10-2025.md` -- full OWASP control mapping.
- `standards/framework/core.md` -- governance non-negotiables and gate thresholds.
- `.github/agents/verify.agent.md` -- verify agent that invokes this skill in 7-mode assessment.
