---
"ai-eng": patch
---

The 2025-11-14 review lands: releases gate on green checks (ci-gate polls the dispatched SHA's check runs, platforms runs on v* tags, the version-packages pull request wakes its own CI, SonarCloud waits retry through infrastructure failures), the policy guard reads Windows paths and PowerShell verbs and stops reading commit-message prose as shell, the secrets gate scans the allowlist editor without exemptions and doctor compares the live allowlist against a versioned baseline, skill mirrors fall back to junction and byte-verified copies on Windows, the identity ledger hashes line-ending-normalized text, doctor keeps the newest audits and survives directories, the injection guard never opens a network share, local-rules patterns with catastrophic backtracking shapes die at load, and a long tail of portability, documentation and simplicity fixes (adapters split by job, one path predicate, the learnings log archived).
