---
name: ai-constitution
description: "Interviews the operator to produce a project-identity CONSTITUTION.md (Mission / Stakeholders / Vocabulary / Prohibitions / Compliance gates / Anti-goals / Boundaries / Escalation / Language / Lifecycle phase). Trigger for 'set up the constitution', 'define project identity', 'who is this project for', 'what does this project never do', 'amend the constitution'. Not for AI-behaviour rules — those live in CANONICAL.md / AGENTS.md. Not for spec governance; use /ai-governance instead."
effort: mid
argument-hint: "[generate|update|amend]"
---

# Constitution

Interviews the operator to produce (or amend) a project-identity CONSTITUTION.md covering Mission, Stakeholders, Vocabulary, Prohibitions, Compliance gates, Anti-goals, Boundaries, Escalation, Language, and Lifecycle phase. Use it to set up or change project identity — not AI-behaviour rules (those live in CANONICAL.md).

## Quick start

```
/ai-constitution generate   # interview + write CONSTITUTION.md from scratch
/ai-constitution update     # change a single section (Mission, Prohibitions, etc.)
/ai-constitution amend      # formal amendment with version bump + audit event
```

## Workflow

Principles: §10.6 (SDD) — every write traces to a spec decision (D-131-04 anchored this rewrite). §10.4 (DRY) — project identity lives ONCE in CONSTITUTION.md; AI-behaviour content lives in CANONICAL.md; the two never overlap.

1. **Auto-detect** — read `.ai-engineering/manifest.yml` + package files (`pyproject.toml` / `package.json` / `Cargo.toml`) to seed name, stack, version.
2. **Read existing** — if `CONSTITUTION.md` exists, load it and show the operator the diff BEFORE any overwrite. NEVER overwrite without diff + explicit confirm (R-131-03 mitigation).
3. **Interview the 10 sections** — see "Interview" below.
4. **Write** — emit `CONSTITUTION.md` on the 10-section skeleton. Refuse to write any AI-behaviour / engineering-principle header (those belong to CANONICAL.md): Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution, Plan-Mode Default, Subagent Strategy, Self-Improvement Loop, Demand Elegance, Autonomous Bug Fixing, KISS, YAGNI, SOLID, DRY, TDD, SDD, Clean Code, Hexagonal Architecture. (Framework dev repo canonical list: `tools/skill_lint/checks/md_mirror.py:FORBIDDEN_CONSTITUTION_HEADERS`.)
5. **Rotate** — on `update`/`amend` that replaces operator-authored content, copy the pre-write body to `.ai-engineering/specs/_history-constitution-<YYYY-MM-DD>.md` so prior identity is recoverable.
6. **Verify + record** (fail-open — never block the write on verify/audit failure):
   - Re-read `CONSTITUTION.md`; confirm it carries only the 10 identity sections and none of the Step 4 AI-behaviour headers.
   - Do NOT shell out to `skill_lint`: it is a framework-dev mirror-parity gate whose module is absent on a consumer's bare `python3` and which false-fails on `.codex`/`.github` mirror surfaces a consumer legitimately lacks.
   - The run is already audited as a `skill_invoked` event by the UserPromptSubmit hook — no manual emit required. Optional distinct marker: emit `framework_event` `kind=framework_operation` (`operation=constitution_update`, `component: ai-constitution`, `detail: {version, sections_changed, mode}`).

## Interview

| Section | Question |
|---------|----------|
| Mission | What does this project do, and what does it never do? |
| Stakeholders | Who relies on this project? Who pays the cost when it breaks? |
| Vocabulary | What domain terms must every contributor use precisely? |
| Prohibitions | What must the AI / contributors NEVER do? |
| Compliance gates | What pipelines / audits / certifications gate releases? |
| Anti-goals | What use cases are explicitly out of scope (and why)? |
| Boundaries | Which surfaces are framework-owned vs team-owned? |
| Escalation | Who is paged when prohibitions / gates fail? |
| Language | Project natural language for docs / commits. |
| Lifecycle phase | greenfield · stabilising · mature · sunset. |

## Examples

User: "amend the constitution to add 'no LLM-generated production secrets' to prohibitions" → `/ai-constitution amend` loads the existing body, presents the diff for the Prohibitions section, applies the amendment, bumps the minor version, records the amendment row in the governance footer, and rotates the pre-amendment body into `_history-constitution-<date>.md`.

## Integration

Called by: `ai-eng install` (governance phase), `/ai-start` (cold-load identity). Reads: `manifest.yml`, package files, existing `CONSTITUTION.md`, `decision-store.json`. Writes: `CONSTITUTION.md`, `_history-constitution-<date>.md` (on rotate). Consumed by: every skill at Step 0. CI-guarded (framework dev repo only) by `tools/skill_lint/checks/md_mirror.py:check_constitution_clean` — any AI-behaviour header fails that gate; consumers rely on the inline Step 6 self-check. See also: `/ai-governance` (compliance against the constitution), CANONICAL.md (AI-behaviour layer — never written by this skill).

$ARGUMENTS
