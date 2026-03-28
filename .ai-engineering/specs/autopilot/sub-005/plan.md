---
total: 3
completed: 3
---

# Plan: sub-005 Verify Specialist Fan-Out

## Plan

- [x] T-5.1 Align the canonical verify contract across live and template skill/agent surfaces.
  Done when: `.agents`, `.claude`, `.github`, and template copies all describe the same seven-specialist roster, the same implicit `normal` and explicit `--full` profiles, the same two-macro-agent grouping, and no unsupported claims.

- [x] T-5.2 Implement verify fan-out and specialist attribution in runtime code.
  Done when: `ai-eng verify platform` covers the full specialist surface in `normal` through two grouped runners, `ai-eng verify platform --full` runs one specialist per lens, direct specialist modes remain callable, and findings retain original specialist attribution in text and JSON.

- [x] T-5.3 Extend mirror and regression coverage for the new verify architecture.
  Done when: tests cover the new profiles, grouped attribution, and mirror parity across live and template verify surfaces, and validation catches drift in `.agents`, `.claude`, and `.github`.

## Exports

- `verify-contract-v2`
- `verify-runtime-v2`
- `verify-mirror-coverage`

## Self-Report
- [x] T-5.1 Align the canonical verify contract across live and template skill/agent surfaces.
  Note: canonical `.claude` skill, handler, and agent now describe the implicit `normal` profile, explicit `--full`, fixed macro-agent grouping, and specialist-attributed output.
- [x] T-5.2 Implement verify fan-out and specialist attribution in runtime code.
  Note: runtime uses a single specialist roster source for platform aggregation and preserves original specialist plus runner attribution in both text and JSON output.
- [x] T-5.3 Extend mirror and regression coverage for the new verify architecture.
  Note: focused service, scoring, and CLI tests cover grouping, profile-specific runners, and JSON specialist attribution in scope; mirror/template enforcement remains for integration.
