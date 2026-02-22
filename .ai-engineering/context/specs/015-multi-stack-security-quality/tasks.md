---
spec: "015"
total: 25
completed: 20
last_session: "2026-02-22"
next_session: "Phase 5 — audit remediation tasks 5.6–5.10"
---

# Tasks — Spec-015

## Phase 1 — Multi-Stack Foundation

- [x] 1.1 Create `.ai-engineering/standards/framework/stacks/dotnet.md` + mirror
- [x] 1.2 Create `.ai-engineering/standards/framework/stacks/nextjs.md` + mirror
- [x] 1.3 Create `.ai-engineering/standards/framework/quality/dotnet.md` + mirror
- [x] 1.4 Create `.ai-engineering/standards/framework/quality/nextjs.md` + mirror
- [x] 1.5 Refactor `manifest.yml` for multi-stack enforcement checks
- [x] 1.6 Refactor `gates.py` for stack-aware dispatch
- [x] 1.7 Add `DotnetTooling`, `NextjsTooling` to `models.py`
- [x] 1.8 Extend `readiness.py` for multi-stack detection

## Phase 2 — Security Capabilities Expansion

- [x] 2.1 Create `standards/framework/security/owasp-top10-2025.md` + mirror
- [x] 2.2 Create `skills/review/dast.md` + mirror + slash command
- [x] 2.3 Create `skills/review/container-security.md` + mirror + slash command
- [x] 2.4 Create `skills/quality/sbom.md` + mirror + slash command
- [x] 2.5 Update `agents/security-reviewer.md` + mirror
- [x] 2.6 Update `skills/review/security.md` + mirror
- [x] 2.7 Update `agents/platform-auditor.md` + mirror
- [x] 2.8 Add optional tooling to `manifest.yml`

## Phase 3 — CI/CD Workflow Generation

- [x] 3.1 Create `standards/framework/cicd/core.md` + mirror
- [x] 3.2 Create `skills/dev/cicd-generate.md` + mirror + slash command

## Phase 4 — Quality Audit Multi-Stack

- [x] 4.1 Update `skills/quality/audit-code.md` + mirror
- [x] 4.2 Update `agents/quality-auditor.md` + mirror
- [x] 4.3 Create `skills/utils/dotnet-patterns.md` + mirror + slash command
- [x] 4.4 Create `skills/utils/nextjs-patterns.md` + mirror + slash command

## Cross-Cutting

- [x] 5.1 Update all 6 instruction files with new skills/commands
- [x] 5.2 Update `product-contract.md` counters
- [x] 5.3 Update `CLAUDE.md` with new skills and commands
- [x] 5.4 Write tests for `gates.py`, `models.py`, `readiness.py` changes
- [x] 5.5 Run integrity-check

## Phase 5 — Audit Remediation (Platform Audit Blocking Issues)

- [ ] 5.6 Add cross-OS CI matrix — GitHub Actions with `ubuntu-latest × windows-latest × macos-latest` covering install, doctor, gate, hook flows (B1/FC-019)
- [ ] 5.7 Wire coverage and duplication thresholds into pre-push gate — integrate `pytest --cov-fail-under=80` and duplication detection into `gates.py` (B2/FC-022)
- [ ] 5.8 Implement `--no-verify` bypass detection — commit-message trailer injection at gate time + CI step to verify all commits have the trailer; enforce `non_bypassable: true` at runtime (B3)
- [ ] 5.9 Add hash-based hook integrity verification — store SHA-256 of hook content in `install-manifest.json`, verify at gate execution before running checks (B4)
- [ ] 5.10 Add hook execution integration test — `test_hook_blocks_commit_with_secret`: stage file with mock secret, run `git commit`, verify exit code != 0 and gate blocks (B5)
