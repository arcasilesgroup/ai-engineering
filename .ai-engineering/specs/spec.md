---
id: spec-081
title: "ai-eng update Interactive UX and Diagnostics"
status: draft
created: 2026-03-26
refs: []
---

# Spec 081: ai-eng update Interactive UX and Diagnostics

## Problem

`ai-eng update` exposes internal mechanics instead of user intent. The command currently defaults to a dry-run preview, but the human output makes that look like a failed update rather than an explicit preview mode. Denied paths are rendered as failures with raw labels such as `skip-denied`, without telling the user whether the denial is expected, why it happened, or what action, if any, is required.

This creates a sharp UX gap with `ai-eng install`, which guides the user through what is happening, separates human and automation flows cleanly, and translates degraded outcomes into understandable manual next steps. Users of `update` currently do not get enough feedback to decide whether to proceed, ignore a protected file, or take corrective action.

## Solution

Redesign `ai-eng update` as an install-style experience with explicit preview, human confirmation, structured diagnostics, and ownership-aware messaging.

For human interactive sessions with a TTY, `ai-eng update` must behave as a guided flow:
- scan for changes
- present a readable preview grouped by outcome
- explain denied paths as ownership protections, not generic failures
- show per-reason diagnostics and recommended actions
- ask for confirmation before applying changes
- apply only after confirmation
- end with a clear summary of what changed, what was skipped, and whether any manual action remains

In human TTY mode, preview and confirmation are mandatory before any write. In non-interactive or JSON mode, prompting is forbidden and writing continues to require an explicit apply flag.

For non-interactive scenarios, the compatibility contract must match `ai-eng install`:
- no prompts in `--json` mode
- no prompts when stdout/stdin environment is non-interactive or non-TTY
- preview remains non-destructive by default
- applying changes in automation still requires an explicit apply signal

The update result model must be enriched so the CLI can explain outcomes instead of printing raw action codes. Each file outcome must carry a machine-readable reason code and a human-readable explanation. At minimum, the model must distinguish:
- update available and applicable
- unchanged
- denied because the file is team-managed
- denied because the file is explicitly protected by ownership rules
- denied because the update would create a protected file
- real operational failure during apply

Human output must stop treating ownership denials as hard failures by default. Expected ownership protections should be surfaced as warnings with explanation and remediation only when remediation is actually possible. True failures must remain failures.

JSON output must expose the same reasons in structured form so agents, CI, and support tooling can tell the difference between expected protections and actual errors.

## Scope

### In Scope
- Redesign the human UX of `ai-eng update` to follow the interaction model used by `ai-eng install`
- Add interactive confirmation before apply in human TTY mode
- Preserve non-interactive behavior parity with `ai-eng install`
- Replace raw human-facing labels such as `skip-denied` with explained outcomes
- Enrich the updater result model with reason codes, explanations, and suggested actions
- Group update results into user-meaningful categories in the CLI summary
- Differentiate expected ownership protections from true apply failures
- Add structured diagnostics to JSON output
- Add tests for interactive flow decisions, reason classification, and JSON contract

### Out of Scope
- Changing ownership policy semantics or relaxing protected paths
- Changing which files are team-managed, framework-managed, or deny-listed
- Rewriting `ai-eng install`
- Changing update template contents
- Adding new board, telemetry, or governance features unrelated to update UX

## Acceptance Criteria
- [ ] In a human TTY session, `ai-eng update` shows a preview first and asks for confirmation before writing any file
- [ ] In a human TTY session, `ai-eng update` does not write immediately even when apply intent is provided; it still previews first and requires confirmation
- [ ] In `--json` mode, `ai-eng update` never prompts and returns structured preview data unless explicit apply mode is requested
- [ ] In non-TTY mode, `ai-eng update` never prompts and follows the same compatibility rule as `ai-eng install`
- [ ] Human output clearly labels preview mode as preview, not as an applied update
- [ ] Human output no longer exposes raw internal labels such as `skip-denied` as the primary user-facing explanation
- [ ] Ownership-protected files are presented as warnings or protected items, not generic failures, when the denial is expected behavior
- [ ] True operational errors during apply are presented separately from ownership protections and remain failures
- [ ] Every file result includes a machine-readable reason code in the service model
- [ ] JSON output includes, for every changed or skipped file, the path, outcome, reason code, human explanation, and any recommended action
- [ ] The CLI summary groups results into at least: applied, available to apply, protected/skipped, unchanged, failed
- [ ] When protected files are skipped, the command explains why they are protected and whether the user needs to do anything
- [ ] When no user action is required for a protected file, the output explicitly says that no action is needed
- [ ] When remediation is possible, the output suggests the next step in human terms instead of exposing only internal state
- [ ] Existing automation remains compatible: scripts using non-interactive or JSON flows are not forced into prompts
- [ ] Automated tests cover TTY interactive behavior, non-TTY behavior, JSON output, reason classification, and failure/protection separation

## Assumptions
- ASSUMPTION: The current default non-destructive preview behavior of `ai-eng update` should be preserved for automation compatibility.
- ASSUMPTION: The interactive confirmation step should only exist for human TTY sessions.
- ASSUMPTION: Ownership denials are usually expected protections, not exceptional errors.
- ASSUMPTION: Matching the behavioral contract of `ai-eng install` is more important than preserving the current exact wording of `update` output.

## Risks
- Backward compatibility risk: some users may rely on current wording or counts in human output.
  Mitigation: keep the JSON contract explicit and add regression tests for automation-facing behavior.
- Classification risk: if reason codes are too coarse, the CLI will still be unable to explain real causes.
  Mitigation: define explicit reason categories in the service layer before redesigning the renderer.
- Interaction risk: interactive confirmation may accidentally appear in contexts that should stay non-interactive.
  Mitigation: use the same TTY and JSON gating rules as `ai-eng install` and test them directly.

## Dependencies
- Existing updater service in `src/ai_engineering/updater/service.py`
- Existing CLI command in `src/ai_engineering/cli_commands/core.py`
- Existing human output helpers in `src/ai_engineering/cli_ui.py`
- Existing dual human/JSON routing conventions used by `ai-eng install`
