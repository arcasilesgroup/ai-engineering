# Naming lint allow-lists (D-131-10 defer)

This reference documents the allow-lists in
`tools/skill_lint/checks/naming.py` so the spec-132 cleanup wave has a
single grep target. The constants
`_R2_DEFERRED_LEGACY` and `_R5_DEFERRED_SKILL_SCRIPTS` MUST stay in
lock-step with the tables below.

The naming lint emits advisory severities for two legacy classes:

## R2 banned-metaphor allow-list (MINOR)

The seven legacy `copilot-*.sh` filenames below were inherited from the
spec-107/108 hooks landing. They violate brief §2.5 R2 (verb-noun with
no banned metaphor) but are deferred per **D-131-10**: the lint emits
`MINOR` (not `MAJOR`) so existing CI does not break on the legacy
surface. The follow-up `spec-132` closes each rename.

| Filename                       | Reason                                                            |
|--------------------------------|-------------------------------------------------------------------|
| `copilot-instinct-extract.sh`  | `instinct` metaphor; rename to `copilot-observation-extract.sh`   |
| `copilot-instinct-observe.sh`  | metaphor + verb pair; rename to `copilot-observation-collect.sh`  |
| `copilot-strategic-compact.sh` | unmotivated adjective; rename to `copilot-context-compact.sh`     |
| `copilot-mcp-health.sh`        | no verb; rename to `copilot-mcp-check.sh`                         |
| `copilot-skill.sh`             | no verb; rename to `copilot-skill-dispatch.sh`                    |
| `copilot-error.sh`             | no verb; rename to `copilot-error-handle.sh`                      |
| `copilot-agent.sh`             | no verb; rename to `copilot-agent-dispatch.sh`                    |

## R5 deferred skill-script .sh files (INFO)

Three skill-owned scripts lack `.ps1` siblings today. They are out of
scope for sub-006 (preprocessor work shipped via spec-129 for the
hot-path skills only). The naming lint emits `INFO` so the gap is
visible without breaking CI; spec-132 closes the parity.

| Filename                    | Owning skill              |
|-----------------------------|---------------------------|
| `board-sync-github.sh`      | `/ai-board`               |
| `cleanup-settings-local.sh` | `/ai-analyze-permissions` |
| `scaffold-skill.sh`         | `/ai-scaffold`              |

## Lock-step contract

The two frozensets in `tools/skill_lint/checks/naming.py`
(`_R2_DEFERRED_LEGACY` and `_R5_DEFERRED_SKILL_SCRIPTS`) MUST contain
exactly the basenames documented above. A unit test
(`tests/conformance/test_naming_lint.py`) pins the live-surface
outcomes; the next refactor that touches these tables MUST sync both
sides.

## Why advisory (not blocker)

Per **D-131-10** the legacy renames are deferred to spec-132 to keep
sub-006 scope bounded. Promoting these to `MAJOR` blocking severity is
a one-line change in `tools/skill_lint/cli.py` `_exit_code` once the
backlog is burned — until then the operator sees the picture via the
`naming OK=N INFO=N MINOR=N MAJOR=N` summary line.
