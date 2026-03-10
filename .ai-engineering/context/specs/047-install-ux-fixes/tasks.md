---
spec: "047"
total: 10
completed: 10
last_session: "2026-03-10"
next_session: "CLOSED"
---

# Tasks — Fix `ai-eng install` UX

## Phase 0: Scaffold [S]

- [x] 0.1 Create spec directory and files
- [x] 0.2 Activate spec in `_active.md`
- [x] 0.3 Commit scaffold

## Phase 1: VCS Alias + Output Cleanup [M]

- [x] 1.1 Add `azdo` alias to prompt choices and `--vcs` flag help in `core.py`
- [x] 1.2 Normalize `azdo` → `azure_devops` in `_resolve_vcs_provider()` after prompt/flag
- [x] 1.3 Display `azdo` in user-facing output (`kv("VCS", ...)`)
- [x] 1.4 Add `azdo` to `_PROVIDERS` dict in `factory.py` and `_VALID_PROVIDERS` in `vcs.py`
- [x] 1.5 Remove inline branch policy guide from install output in `core.py`
- [x] 1.6 Add blank line separators between output sections in `core.py`

## Phase 2: Platform Filtering + Sonar URL [M]

- [x] 2.1 Add `vcs_provider` param to `setup_platforms_cmd` and filter opposite VCS from undetected
- [x] 2.2 Normalize Sonar URL (extract scheme+netloc) in `validate_token` and `_validate_token_urllib`
- [x] 2.3 Add JSON parse error message and update Sonar prompt hint

## Phase 3: Tests + Verification [S]

- [x] 3.1 Add/update unit tests for azdo alias, platform filtering, Sonar URL normalization
