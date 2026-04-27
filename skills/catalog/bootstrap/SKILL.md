---
name: bootstrap
description: Use for end-to-end first-run project setup — detects stack, asks 4 CONSTITUTION framing questions, writes manifest.toml, generates IDE mirrors via sync-mirrors. Pairs with the `ai-eng bootstrap` CLI. Trigger for "bootstrap this project", "first-run setup", "initialize ai-engineering here", "set up the framework".
effort: high
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: false
---

# /ai-bootstrap

End-to-end first-run setup. Detects the project's stack, drafts the
constitution from the right profile, writes
`.ai-engineering/manifest.toml`, and generates the IDE mirror tree via
`ai-eng sync-mirrors`. Pairs with the `ai-eng bootstrap` Layer-1 CLI
verb so first-run works without an LLM call.

> **Idempotent.** Running on an already-bootstrapped project re-runs
> sync-mirrors and reports drift, never overwrites without `--force`.

## When to use

- Brand-new repo — "set up ai-engineering"
- Fork of an existing repo that lacks the framework
- Migration onto v3 from v2 — `bootstrap --upgrade-from-v2`
- After a profile change (default → regulated) to refresh manifest

## Process

1. **Stack detection** — scan for `package.json`, `pyproject.toml`,
   `Cargo.toml`, `pom.xml`, `*.csproj`, etc. Persist to manifest as
   `[stacks]`.
2. **Profile selection** — ask "default" or "regulated" (banking /
   healthcare / public sector); default selected on no answer.
3. **Constitution framing** — delegate to `/ai-constitution init` for
   the 4 framing questions and CONSTITUTION.md draft.
4. **Manifest seed** — write `.ai-engineering/manifest.toml` with:
   - `[profile]` selected profile
   - `[stacks]` detected from scan
   - `[skills]` core catalog enabled by default
   - `[agents]` core 6 + verifier
   - `[board]` provider if detected (Jira / Linear / GitHub Issues)
   - `[telemetry]` local NDJSON sink always-on, OTel endpoint blank
5. **IDE mirror generation** — call `ai-eng sync-mirrors`:
   - `.claude/skills/<name>/SKILL.md` (Claude Code)
   - `.cursor/skills/<name>.md` (Cursor)
   - `.codex/skills/<name>.md` (Codex CLI)
   - `.gemini/skills/<name>/` (Gemini CLI)
   - `.github/copilot/...` (GitHub Copilot)
6. **First-run verification** — `ai-eng doctor` runs and reports green.
7. **Stub LESSONS.md** — empty file with category headers.
8. **Open onboarding PR** — `chore(bootstrap): initialize ai-engineering`.
9. **Emit telemetry** — `bootstrap.completed` with stack list, profile,
   IDE mirror count.
10. **Suggest next** — `/ai-start` to load the new dashboard.

## Wiring with `ai-eng bootstrap` CLI

The Layer-1 CLI handles the deterministic parts (file writes,
sync-mirrors). This skill orchestrates:

- The interrogation (4 questions can't be deterministic)
- The constitution draft (LLM-authored from template + answers)
- The post-run verification narrative

The CLI runs alone for non-interactive setup (`--profile regulated
--stacks ts,py --yes`). The skill is the interactive path.

## Hard rules

- NEVER overwrite an existing `manifest.toml` without `--force`.
  Idempotent re-runs report drift, surface it for review.
- NEVER write into IDE mirror dirs by hand — `sync-mirrors` is the
  only authorized writer (Constitution Article V).
- NEVER skip `ai-eng doctor` after bootstrap — silent misconfig is the
  worst first-run experience.
- Profile selection MUST happen before manifest write — reordering
  inverts trust tiers.
- All generated mirror files carry the `DO NOT EDIT` header.

## Common mistakes

- Editing IDE mirror files directly after bootstrap — overwritten on
  next sync
- Skipping the 4 framing questions and shipping a generic constitution
- Writing `manifest.toml` without re-running `sync-mirrors` (skills
  invisible to the IDE)
- Forgetting to stub `LESSONS.md` — `/ai-learn` first run errors
- Running bootstrap on a repo with a customized manifest without `--force`
  and clobbering the customization
- Telling the user "done" before `ai-eng doctor` confirms green
