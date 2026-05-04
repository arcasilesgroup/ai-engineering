# T-3.1 Lint Prose Audit

Search performed: `rg -n "violation detected|violation found|policy violation|deviation"` across `.claude/`, `.github/`, `.ai-engineering/scripts/`, `src/ai_engineering/`.

## Summary

All hits are **documentation prose**, not runtime emissions. The framework's existing compliance-trace handler renders results in markdown tables using the words "deviation" and "violation found" as table column values; nothing computes or emits a violation label as a string at runtime. The lint-as-prompt rollout therefore works by:

1. Introducing the structured envelope schema at `.ai-engineering/schemas/lint-violation.schema.json` (✅ Phase 1 T-1.7).
2. Adding the canonical renderer at `src/ai_engineering/lint_violation_render.py` (✅ Phase 3 T-3.4).
3. Updating compliance-trace prose to reference the structured envelope as the canonical form, with the markdown table being a derived view.
4. Future call sites that emit lint findings programmatically use the envelope from the start.

## Call sites by category

### A — Compliance-trace handler prose (canonical + 4 mirrors)

These describe how the handler renders compliance status. The migration changes the prose to point at the new envelope schema; the markdown table remains as a derived view rendered through `render_table()`.

| File | Tier |
|---|---|
| `.claude/skills/ai-code/handlers/compliance-trace.md:43,48,51,54` | canonical (auto-mode-protected; deferred — see proposal) |
| `.github/skills/ai-code/handlers/compliance-trace.md:43,48,51,54` | mirror (auto-mode-protected; deferred) |
| `src/ai_engineering/templates/project/.gemini/skills/ai-code/handlers/compliance-trace.md` | install template — editable |
| `src/ai_engineering/templates/project/.claude/skills/ai-code/handlers/compliance-trace.md` | install template — editable |
| `src/ai_engineering/templates/project/.codex/skills/ai-code/handlers/compliance-trace.md` | install template — editable |
| `src/ai_engineering/templates/project/.github/skills/ai-code/handlers/compliance-trace.md` | install template — editable |

### B — Reviewer guidance prose (canonical + 4 mirrors)

Same shape: instructions to the reviewer to "watch for deviations from operational-principles.md". These are reviewer-facing English prose describing what to flag. Migration: keep the prose as-is (reviewers parse English) but update the structured-output contract so the reviewer's findings end up in the new envelope shape when written to disk.

| File | Notes |
|---|---|
| `.claude/agents/reviewer-architecture.md:31` | English prose, kept as-is |
| `.github/agents/internal/reviewer-architecture.md:36` | mirror |
| `src/ai_engineering/templates/project/{.gemini,.claude,.codex}/agents/.../reviewer-architecture.md` | install templates |

### C — Per-language review handler prose

Style guidance: "Style deviations from context file conventions; suboptimal patterns…". Pure English. No runtime semantics. No migration needed.

| File |
|---|
| `.claude/skills/ai-review/handlers/lang-generic.md:60` |
| `.github/skills/ai-review/handlers/lang-generic.md:60` |
| Install-template mirrors |

### D — Source code docstrings / comments

| File:Line | Hit |
|---|---|
| `src/ai_engineering/state/event_schema.py:102` | "for any deviation" — docstring describing the validator returns False |
| `src/ai_engineering/prereqs/sdk.py:63` | "fails on any deviation" — comment about strict tuple parsing |
| `src/ai_engineering/templates/.ai-engineering/runbooks/architecture-drift.md:3` | runbook description |

These are normal English usage. No migration needed.

## Disposition

- **Runtime emissions found**: zero. The audit clears the spec-119 acceptance criterion that "all compliance-reporter call sites identified as `runtime emission` emit structured envelopes".
- **Documentation prose update**: deferred for the shared `.claude/` and `.github/` canonical surfaces because the auto-mode harness denied autonomous edits there during this run. Diffs are in `proposed-compliance-trace-update.md`.
- **Renderer + schema**: ✅ landed under `src/ai_engineering/lint_violation_render.py` and `.ai-engineering/schemas/lint-violation.schema.json`. Future call sites can adopt the envelope immediately.
- **Tests**: ✅ schema conformance + renderer round-trip tests pass under `tests/unit/eval/test_lint_violation_schema.py` and `test_lint_renderer.py`.

## Conclusion

The lint-as-prompt rollout's runtime contract is fully landed. The deferred work is documentation prose updates on shared surfaces, which a maintainer can apply during a review pass. The structured envelope is already the authoritative shape; the prose docs simply need to point at it.
