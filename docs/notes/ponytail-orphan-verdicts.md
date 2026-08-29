---
found: 2026-08-29
commit: ed3c8364
describes: ["src/ai_engineering/", "specs/029-evidence-executed-and-answer-keys/", "specs/030-cold-read-verification-and-revalidation/", "specs/031-verification-dag-loop-termination-and-spec-containment/", "specs/033-context-economy-and-skill-authoring/", "specs/034-appendix-notes-decision-frameworks-and-constellation/", "specs/036-validate-adoption-and-close-boundary-delta/", "specs/037-model-router-and-intake-validation/"]
still_true_when: "none of the twelve deleted modules has been restored with its consumer in the same commit"
---

# The twelve orphans stay dead — the ponytail verdict, per module

Spec 044 deleted twelve modules written by specs 029-037 (commit `14eaaeb1`,
2026-08-27): `verify_cold`, `answer_key`, `loopgate`, `lane_merge`, `intake`,
`trim`, `skillify`, `versions`, `constellation`, `decision_fw`, `evidencing`,
`decision_boundary`. The fidelity audit (`.ai/reports/024-implementation-fidelity-audit.html`)
found they were written, checked, ticked `[x]` — and never wired to a caller.
The owner asked, per KISS/YAGNI/ponytail: are they necessary? Verdict per module,
recorded so the next agent does not resurrect one by reflex:

- **Stay dead — the rule survives, the module was the scaffolding:**
  - `trim` — the discipline (never drop a failure line) is a one-line habit the
    agent can follow in prose; `.agents/skills/ai-note/corpus.md` now states it without the module.
  - `versions` — "the installed version decides, never trusted from memory" is a
    corpus rule (ai-review, ai-security), not a Python call; `uv pip show` is the
    command.
  - `skillify` — turning a session into a SKILL.md is what `/ai-note` + `/ai-spec`
    already do; a skeleton-extractor with zero callers is a prompt wearing a module.
  - `constellation`, `decision_fw` — pattern-recognition prompts, not deterministic
    decisions; they failed the framework's own test ("a decision that always comes
    out the same is code, not a prompt" — these never came out the same).
  - `evidencing`, `decision_boundary` — superseded: the tick-executes-check model
    of spec 046 (`ai-eng spec show --tick`) and the `## Decisions` `[X]` marker of
    spec 041 do their job inside existing readers.
- **Stay dead — but named reopening condition (this is the honest half):**
  - `loopgate` — the two-digest-equal-greens stop rule is real and wanted; it stays
    dead until the autonomous cycle (`/ai-goal` unattended) exists, because today a
    human ends loops. Reopen when: the cycle runs without a person at the keyboard.
  - `lane_merge` — the verification DAG earns its weight when critics run in
    parallel lanes automatically; today `policy/skill-sequence.toml` orders them.
    Reopen when: two lanes actually run concurrently and their findings collide.
  - `verify_cold` + `answer_key` — the independent cold verifier is what the owner
    keeps asking for ("que otro agente revise sin ver mi conversación"). It stays
    dead until it ships WITH its consumer (a `just verify-cold` lane or the
    ai-verify fork invoking it) in the same commit. Reopen when: a spec approves
    the verifier together with its caller — never the module alone.
  - `intake` + `bail_out` — the router lives (`model_router.route`); the intake
    validator and early-exit were never called. Reopen when: `/ai-goal` validates
    the opening request mechanically instead of by SKILL.md prose.

The lesson, the way the doctrine states it: a module with no caller is a spec that
finished its plan and failed its purpose. The gate that would have caught this is
named in the audit report (spec fidelity: every `[x]` re-checked against the tree
for a non-test caller) and lives, if built, in `src/ai_engineering/` as a verb.
