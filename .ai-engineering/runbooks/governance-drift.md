---
runbook: governance-drift
version: 1
purpose: "Verify framework alignment: mirror sync, quality gate config, hook integrity, manifest consistency, and template-vs-installed drift"
type: operational
cadence: weekly
hosts:
  - codex-app-automation
  - claude-scheduled-tasks
  - github-agents
  - azure-foundry
provider_scope:
  read: [issues, labels, code]
  write: [comments, work-items, labels]
feature_policy: read-only
hierarchy_policy:
  create: [task]
  mutate: [task]
scan_targets:
  - .claude/ (skills, agents)
  - .agents/ (skills, agents)
  - .github/ (skills, agents)
  - .ai-engineering/ (contexts, runbooks, manifest)
  - src/ai_engineering/templates/
tool_dependencies:
  - gh
  - az
  - python
  - ai-eng
thresholds:
  max_drift_files: 0
  max_findings_per_run: 15
outputs:
  work_items: true
  comments: true
  labels: true
  report: detailed
handoff:
  marker: "governance-drift"
  lifecycle_phase: triage
guardrails:
  max_mutations: 15
  protected_labels: [p1-critical, pinned]
  protected_states: [closed, resolved]
  dry_run_default: true
---

# Governance Drift

## Purpose

Detect configuration and content drift between framework-managed surfaces: IDE mirror sync, quality gate thresholds, hook script integrity, manifest internal consistency, and template-vs-installed divergence. Runs weekly and produces task work items for every verified drift finding. This runbook is strictly read-only against framework files -- it reports drift but never auto-fixes it.

## Procedure

### Step 1 -- Run mirror sync check

Verify that `.claude/` canonical sources are in sync with their mirrors in `.agents/`, `.github/`, and `src/ai_engineering/templates/`.

```bash
python scripts/sync_command_mirrors.py --check
```

Exit code 0 means all mirrors match. Exit code 1 means drift exists -- capture the diff output listing each file with a content mismatch. Record every drifted file path and its mirror counterpart.

### Step 2 -- Run ai-eng governance verification

When the `ai-eng` CLI is available, run the built-in governance check for a structured report.

```bash
ai-eng verify governance --json
```

Parse the JSON output. Each finding includes a category, severity, file path, and remediation hint. Store findings in the working set for Step 8.

### Step 3 -- Fallback: manual mirror consistency check

When `ai-eng` is unavailable, verify mirror parity manually. For each skill in `.claude/skills/ai-*/SKILL.md`, confirm the corresponding file exists and matches in all three mirror targets.

```bash
# List canonical skills
ls .claude/skills/ai-*/SKILL.md | while read -r canonical; do
  SKILL=$(basename "$(dirname "$canonical")")
  SKILL_SHORT="${SKILL#ai-}"

  # Check .agents/ mirror
  AGENTS_MIRROR=".agents/skills/$SKILL_SHORT/SKILL.md"
  if [ ! -f "$AGENTS_MIRROR" ]; then
    echo "DRIFT [missing] $AGENTS_MIRROR (canonical: $canonical)"
  elif ! diff -q "$canonical" "$AGENTS_MIRROR" > /dev/null 2>&1; then
    echo "DRIFT [content] $AGENTS_MIRROR differs from $canonical"
  fi

  # Check .github/ mirror
  GITHUB_MIRROR=".github/skills/$SKILL/SKILL.md"
  if [ ! -f "$GITHUB_MIRROR" ]; then
    echo "DRIFT [missing] $GITHUB_MIRROR (canonical: $canonical)"
  elif ! diff -q "$canonical" "$GITHUB_MIRROR" > /dev/null 2>&1; then
    echo "DRIFT [content] $GITHUB_MIRROR differs from $canonical"
  fi
done

# Repeat for agents
ls .claude/agents/ai-*.md | while read -r canonical; do
  AGENT=$(basename "$canonical")
  for MIRROR_DIR in .agents/agents .github/agents; do
    if [ ! -f "$MIRROR_DIR/$AGENT" ]; then
      echo "DRIFT [missing] $MIRROR_DIR/$AGENT"
    elif ! diff -q "$canonical" "$MIRROR_DIR/$AGENT" > /dev/null 2>&1; then
      echo "DRIFT [content] $MIRROR_DIR/$AGENT differs from $canonical"
    fi
  done
done
```

### Step 4 -- Check quality gate thresholds

Read `manifest.yml` and verify that quality gate values match the expected baselines defined in `CLAUDE.md`.

```bash
python3 -c "
import yaml, sys, pathlib

manifest = yaml.safe_load(pathlib.Path('.ai-engineering/manifest.yml').read_text())
quality = manifest.get('quality', {})

expected = {'coverage': 80, 'duplication': 3, 'cyclomatic': 10, 'cognitive': 15}
drift = []

for key, want in expected.items():
    got = quality.get(key)
    if got is None:
        drift.append(f'DRIFT [missing] quality.{key}: expected {want}, not set')
    elif got != want:
        drift.append(f'DRIFT [threshold] quality.{key}: expected {want}, found {got}')

if drift:
    print('\n'.join(drift))
    sys.exit(1)
else:
    print('Quality gates OK')
"
```

### Step 5 -- Verify hook integrity

Check that installed hook scripts have not been modified by comparing their SHA-256 hashes against the source copies in `scripts/hooks/`.

```bash
for HOOK_SRC in scripts/hooks/*; do
  HOOK_NAME=$(basename "$HOOK_SRC")
  HOOK_INSTALLED=".git/hooks/$HOOK_NAME"

  if [ ! -f "$HOOK_INSTALLED" ]; then
    echo "DRIFT [missing] $HOOK_INSTALLED not installed (source: $HOOK_SRC)"
    continue
  fi

  SRC_HASH=$(shasum -a 256 "$HOOK_SRC" | cut -d' ' -f1)
  INST_HASH=$(shasum -a 256 "$HOOK_INSTALLED" | cut -d' ' -f1)

  if [ "$SRC_HASH" != "$INST_HASH" ]; then
    echo "DRIFT [integrity] $HOOK_INSTALLED hash mismatch (expected: ${SRC_HASH:0:12}..., found: ${INST_HASH:0:12}...)"
  fi
done
```

### Step 6 -- Check template-vs-installed drift

Compare framework-managed files under `src/ai_engineering/templates/project/` against their installed counterparts in the repository root. Only check files that the framework owns (paths listed in `manifest.yml` under `ownership.framework`).

```bash
TEMPLATE_ROOT="src/ai_engineering/templates/project"

# Compare .claude/ templates against installed
find "$TEMPLATE_ROOT/.claude" -type f | while read -r tmpl; do
  RELATIVE="${tmpl#$TEMPLATE_ROOT/}"
  if [ ! -f "$RELATIVE" ]; then
    echo "DRIFT [missing] $RELATIVE not installed (template: $tmpl)"
  elif ! diff -q "$tmpl" "$RELATIVE" > /dev/null 2>&1; then
    echo "DRIFT [template] $RELATIVE differs from template $tmpl"
  fi
done

# Compare .agents/ and .github/ templates
for SURFACE in .agents .github; do
  find "$TEMPLATE_ROOT/$SURFACE" -type f 2>/dev/null | while read -r tmpl; do
    RELATIVE="${tmpl#$TEMPLATE_ROOT/}"
    if [ ! -f "$RELATIVE" ]; then
      echo "DRIFT [missing] $RELATIVE not installed"
    elif ! diff -q "$tmpl" "$RELATIVE" > /dev/null 2>&1; then
      echo "DRIFT [template] $RELATIVE differs from template"
    fi
  done
done
```

### Step 7 -- Verify manifest internal consistency

Check that every skill and agent declared in `manifest.yml` has a corresponding file on disk, and that no orphaned files exist without a registry entry.

```bash
python3 -c "
import yaml, pathlib, sys

manifest = yaml.safe_load(pathlib.Path('.ai-engineering/manifest.yml').read_text())
drift = []

# Check skill registry vs disk
registry = manifest.get('skills', {}).get('registry', {})
for skill_name in registry:
    skill_path = pathlib.Path(f'.claude/skills/{skill_name}/SKILL.md')
    if not skill_path.exists():
        drift.append(f'DRIFT [orphan-registry] {skill_name} in manifest but no file at {skill_path}')

# Check disk vs skill registry
for skill_dir in sorted(pathlib.Path('.claude/skills').iterdir()):
    if skill_dir.is_dir() and (skill_dir / 'SKILL.md').exists():
        if skill_dir.name not in registry:
            drift.append(f'DRIFT [unregistered] {skill_dir.name} on disk but not in manifest registry')

# Check agent names vs disk
agent_names = manifest.get('agents', {}).get('names', [])
for agent in agent_names:
    agent_path = pathlib.Path(f'.claude/agents/ai-{agent}.md')
    if not agent_path.exists():
        drift.append(f'DRIFT [orphan-registry] agent {agent} in manifest but no file at {agent_path}')

# Check disk vs agent registry
for agent_file in sorted(pathlib.Path('.claude/agents').glob('ai-*.md')):
    name = agent_file.stem.replace('ai-', '')
    if name not in agent_names:
        drift.append(f'DRIFT [unregistered] agent {name} on disk but not in manifest')

# Check declared totals
actual_skills = len(registry)
declared_skills = manifest.get('skills', {}).get('total', 0)
if actual_skills != declared_skills:
    drift.append(f'DRIFT [count] skills.total: declared {declared_skills}, registry has {actual_skills}')

actual_agents = len(agent_names)
declared_agents = manifest.get('agents', {}).get('total', 0)
if actual_agents != declared_agents:
    drift.append(f'DRIFT [count] agents.total: declared {declared_agents}, list has {actual_agents}')

if drift:
    print('\n'.join(drift))
    sys.exit(1)
else:
    print('Manifest consistency OK')
"
```

### Step 8 -- Create work items for drift findings

For each drift finding from Steps 1-7, create a task work item. Respect the `max_mutations` guardrail (15 per run). Apply dry-run mode unless explicitly overridden.

```bash
# GitHub Issues
gh issue create \
  --title "[governance-drift] <drift_type>: <file_path>" \
  --body "## Governance Drift Finding

**Category:** mirror-sync | threshold | hook-integrity | template-drift | manifest-consistency
**Drift type:** missing | content | threshold | integrity | orphan-registry | unregistered | count
**File:** <file_path>
**Expected:** <expected_value_or_hash>
**Actual:** <actual_value_or_hash>
**Remediation:** <action>

**Detected by:** governance-drift runbook v1" \
  --label "governance-drift"

# Azure DevOps
az boards work-item create --type Task \
  --title "[governance-drift] <drift_type>: <file_path>" \
  --description "<body>" \
  --area "Project\\TeamName"
```

In dry-run mode, print the work item payloads to stdout without creating them.

### Step 9 -- Generate report

Produce a structured report summarizing all findings and the overall framework health score.

```
=== Governance Drift Report ===
Date:          2026-03-28T00:00:00Z
Drift files:   4 (threshold: 0)
Total findings: 7 / 15 max

By category:
  Mirror sync:          2
  Quality thresholds:   0
  Hook integrity:       1
  Template drift:       3
  Manifest consistency: 1

Framework health score: 86/100
  Mirror parity:        -6  (2 files drifted)
  Gate config:           0  (all thresholds match)
  Hook integrity:       -3  (1 hook modified)
  Template alignment:   -3  (3 files diverged)
  Manifest consistency: -2  (1 orphan entry)

Items created: 7 (dry-run: true)
Mutations used: 7 / 15
```

The health score starts at 100 and deducts points per finding: mirror sync -3/file, threshold -5/gate, hook integrity -3/hook, template drift -1/file, manifest inconsistency -2/entry. A score below 70 indicates the framework needs immediate remediation.

## Provider Notes

| Concern | GitHub (`gh`) | Azure DevOps (`az`) |
|---------|---------------|---------------------|
| Work item creation | `gh issue create --label "governance-drift"` | `az boards work-item create --type Task` |
| Labels | `--label` flag on issue create | Tag field via `System.Tags` |
| Comments | `gh issue comment --body` | `az boards work-item update --discussion` |
| Auth | `GH_TOKEN` env var or `gh auth login` | `az login` or service principal via `AZURE_DEVOPS_EXT_PAT` |

Both providers produce identical report output. The provider is read from `manifest.yml` field `work_items.provider`.

## Host Notes

| Host | Considerations |
|------|---------------|
| codex-app-automation | Full CLI access. Both `python` and `ai-eng` are available. Run `sync_command_mirrors.py --check` and `ai-eng verify governance --json` natively. Timeout budget is 10 minutes. |
| claude-scheduled-tasks | Operates within Claude agent context. Use tool calls for `python`, `gh`, and shell commands. When `ai-eng` is unavailable, fall back to Step 3 manual checks. Report output as structured markdown. |
| github-agents | Runs as a GitHub Actions scheduled workflow. Python is available via `actions/setup-python`. The `ai-eng` CLI must be installed via `pip install ai-engineering` in the workflow. Use `GITHUB_TOKEN` for API calls. Azure DevOps commands are unavailable. |
| azure-foundry | Authenticate via managed identity. Python is pre-installed. Install `ai-eng` via pip if not cached. GitHub commands require a PAT stored in Key Vault. |

## Safety

1. **Never auto-fixes drift.** This runbook detects and reports drift. It does not run `sync_command_mirrors.py` without `--check`, does not overwrite framework files, and does not modify hook scripts.
2. **Never modifies framework files.** No write operations target `.claude/`, `.agents/`, `.github/`, `.ai-engineering/`, or `src/ai_engineering/templates/`. Remediation is delegated to a human or to `sync_command_mirrors.py` (without `--check`) after review.
3. **Read-only by default.** The `dry_run_default: true` guardrail means no work items are created unless the operator explicitly passes `--apply`.
4. **Bounded mutations.** A maximum of 15 work items are created per run. If findings exceed this limit, the report notes the overflow and stops creating items.
5. **Protected states.** Items in `closed` or `resolved` state are never reopened or modified. Labels `p1-critical` and `pinned` are never removed.
6. **Idempotent.** Before creating a work item, search existing open issues for the same file path and drift type. Duplicate findings are skipped.
