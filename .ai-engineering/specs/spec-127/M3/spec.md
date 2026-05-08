---
id: sub-004
parent: spec-127
milestone: M3
title: "Progressive-disclosure slim-down (≤120 line ceiling)"
status: planning
files:
  - .claude/skills/ai-animation/SKILL.md
  - .claude/skills/ai-video-editing/SKILL.md
  - .claude/skills/ai-governance/SKILL.md
  - .claude/skills/ai-platform-audit/SKILL.md
  - .claude/skills/ai-skill-evolve/SKILL.md
  - .claude/skills/**/references/
  - tools/skill_lint/checks/no_nested_refs.py
  - tests/conformance/test_no_nested_refs.py
depends_on:
  - sub-003
---

# Sub-Spec 004: M3 — Progressive-disclosure slim-down

## Scope

Slim the top-5 over-length skills to ≤120 lines per D-127-08 internal target:
`ai-animation` (228 → ≤120), `ai-video-editing` (194 → ≤120), `ai-governance`
(182 → ≤120), `ai-platform-audit` (181 → ≤120), `ai-skill-evolve` (179 →
≤120). Move detail to `references/` directory per skill. Apply skill/agent
split contract per brief §22 — pair files (`ai-autopilot`, `ai-verify`,
`ai-review`, `ai-plan`, `ai-guide`) reduce duplication, declare dispatch
threshold in skill body. Ship `tools/skill_lint/checks/no_nested_refs.py` and
`tests/conformance/test_no_nested_refs.py` to enforce no nested ref→ref.
Re-run `skill_lint --check` — assert all SKILL.md ≤120 lines.

## Exploration

### Top-5 over-length skills (current line counts)

- `.claude/skills/ai-animation/SKILL.md`: 228 → ≤120 (−108)
- `.claude/skills/ai-video-editing/SKILL.md`: 194 → ≤120 (−74)
- `.claude/skills/ai-governance/SKILL.md`: 182 → ≤120 (−62)
- `.claude/skills/ai-platform-audit/SKILL.md`: 181 → ≤120 (−61)
- `.claude/skills/ai-skill-evolve/SKILL.md`: 179 → ≤120 (−59)

Total: 1,095 lines → ≤600 (~−495).

### Reference layout strategy (per skill)

- **ai-animation**: move easing-curves, accessibility, stagger-and-debug to
  `references/`; keep 6 handlers as-is in body
- **ai-video-editing**: new `references/` for layer details, ffmpeg tables,
  social presets
- **ai-governance**: move detailed governance hooks to `references/`
- **ai-platform-audit**: existing `references/report-template.md` precedent;
  expand to capture detail
- **ai-skill-evolve**: move grading rubric + optimizer phase tables to
  `references/`

### Pair-file split contract (brief §22)

Apply to: `ai-autopilot`, `ai-verify`, `ai-review`, `ai-plan`, `ai-guide`.
Skill body declares dispatch threshold (e.g. "if N concerns ≥ 3 → dispatch
to agent in fresh context"). Pair agent file reads same threshold from skill
body via reference, not duplication.

### Dependencies

- sub-003 (M2): Examples + Integration sections must exist before slim-down
  so target line counts are realistic against the new sections.
- Coordinates with M4: post-rename, `ai-platform-audit` → `ai-ide-audit` and
  `ai-skill-evolve` → `ai-skill-tune`. M3 task targets MAY use either name
  depending on M4 ordering; if M3 lands first, the rename in M4 picks up the
  slimmed bodies.

### No-nested-refs guard

`tools/skill_lint/checks/no_nested_refs.py` walks every `references/<file>.md`
and asserts no internal markdown link `[text](references/...)` resolves
inside another `references/` file (one level deep only).
`tests/conformance/test_no_nested_refs.py` runs the checker over all skills.
