---
name: architecture-drift
description: "Compare current codebase against solution-intent and constitution for architectural deviations, layer violations, and undocumented structural changes"
type: operational
cadence: weekly
---

# Architecture Drift

## Objetivo

Detect deviations between the running codebase and the declared architecture in `docs/solution-intent.md`, `.ai-engineering/CONSTITUTION.md`, and `.ai-engineering/state/decision-store.json`. This includes import-cycle violations, layer-boundary crossings, undocumented structural changes, and decisions that no longer match code reality. Runs weekly; produces task work items for every confirmed finding.

## Precondiciones

- `docs/solution-intent.md` exists with a mermaid module graph (section 2.2) defining layers and allowed dependency directions
- `.ai-engineering/CONSTITUTION.md` exists with boundary rules
- `.ai-engineering/state/decision-store.json` exists with active architecture decisions
- Work items provider configured in `manifest.yml` (`github` or `azure_devops`)
- CLI access: `gh` for GitHub, `az` for Azure DevOps
- Python 3.11+ available (Steps 4, 5, 7 use `ast` stdlib)

## Procedimiento

### Step 1 -- Extract documented architecture layers

Read the solution-intent to build the authoritative layer map. The module graph in section 2.2 defines five layers and their allowed dependency directions.

```bash
cat docs/solution-intent.md
```

Parse the mermaid graph to extract:

| Layer | Modules | Allowed imports from |
|-------|---------|---------------------|
| Interface | cli_commands, commands | Core, Policy, Platform, Auxiliary |
| Core | installer, vcs, state, maintenance, lib | Infra, Auxiliary |
| Policy | policy, validator, verify | state (Core) |
| Platform | platforms, release | vcs (Core) |
| Infra | pipeline, updater, hooks, detector, version | (leaf -- no inward deps) |
| Auxiliary | git, credentials, doctor, skills, work_items | (leaf -- no inward deps) |

Record this as `$LAYER_MAP` for boundary checks in Step 5.

### Step 2 -- Extract project scope and boundaries

Read the project identity to capture hard constraints that code must not violate.

```bash
cat .ai-engineering/CONSTITUTION.md
```

Extract the boundary rules:
- Never overwrite team-managed content (`contexts/team/`, `manifest.yml`, `.claude/settings.json`)
- Never weaken quality gate thresholds
- Never bypass security scanning
- Coordinate before changing installer output structure

These become assertions verified against recent commits in Step 6.

### Step 3 -- Load active architectural decisions

Read the decision store and filter to active architecture decisions.

```bash
python -c "
import json, sys
with open('.ai-engineering/state/decision-store.json') as f:
    store = json.load(f)
active = [d for d in store['decisions']
          if d['status'] == 'active' and d['category'] == 'architecture']
for d in active:
    print(f\"{d['id']}: {d['title']}\")
"
```

Store the result as `$ACTIVE_DECISIONS`. Each decision becomes a verification target in Step 7.

### Step 4 -- Scan for import cycles

Run a cycle-detection pass across all Python source modules. Any cycle is a threshold violation (`max_import_cycles: 0`).

```bash
python -c "
import ast, os, sys
from collections import defaultdict

PKG = 'src/ai_engineering'
graph = defaultdict(set)

for root, _, files in os.walk(PKG):
    for f in files:
        if not f.endswith('.py'):
            continue
        module = os.path.relpath(os.path.join(root, f), PKG).replace('/', '.').removesuffix('.py')
        try:
            tree = ast.parse(open(os.path.join(root, f)).read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('ai_engineering'):
                target = node.module.replace('ai_engineering.', '').split('.')[0]
                source = module.split('.')[0]
                if source != target:
                    graph[source].add(target)

# DFS cycle detection
visited, path, cycles = set(), set(), []
def dfs(node, trail):
    if node in path:
        cycle_start = trail.index(node)
        cycles.append(trail[cycle_start:] + [node])
        return
    if node in visited:
        return
    visited.add(node); path.add(node); trail.append(node)
    for dep in graph.get(node, []):
        dfs(dep, trail[:])
    path.discard(node)

for mod in list(graph):
    dfs(mod, [])

if cycles:
    print(f'FAIL: {len(cycles)} import cycle(s) detected')
    for c in cycles[:10]:
        print('  ' + ' -> '.join(c))
    sys.exit(1)
else:
    print('PASS: no import cycles detected')
"
```

Any cycle found is recorded as a finding with severity `high`.

### Step 5 -- Check layer boundaries

Verify that no module imports from a layer it is not permitted to depend on according to `$LAYER_MAP`.

```bash
python -c "
import ast, os, sys

PKG = 'src/ai_engineering'
LAYERS = {
    'cli_commands': 'Interface', 'commands': 'Interface',
    'installer': 'Core', 'vcs': 'Core', 'state': 'Core',
    'maintenance': 'Core', 'lib': 'Core',
    'policy': 'Policy', 'validator': 'Policy', 'verify': 'Policy',
    'platforms': 'Platform', 'release': 'Platform',
    'pipeline': 'Infra', 'updater': 'Infra', 'hooks': 'Infra',
    'detector': 'Infra', 'version': 'Infra',
    'git': 'Auxiliary', 'credentials': 'Auxiliary', 'doctor': 'Auxiliary',
    'skills': 'Auxiliary', 'work_items': 'Auxiliary',
}
ALLOWED = {
    'Interface': {'Core', 'Policy', 'Platform', 'Infra', 'Auxiliary'},
    'Core':      {'Infra', 'Auxiliary'},
    'Policy':    {'Core'},
    'Platform':  {'Core'},
    'Infra':     set(),
    'Auxiliary':  set(),
}

violations = []
for root, _, files in os.walk(PKG):
    for f in files:
        if not f.endswith('.py'):
            continue
        fpath = os.path.join(root, f)
        module = os.path.relpath(fpath, PKG).split('/')[0].removesuffix('.py')
        src_layer = LAYERS.get(module)
        if not src_layer:
            continue
        try:
            tree = ast.parse(open(fpath).read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('ai_engineering'):
                target_mod = node.module.replace('ai_engineering.', '').split('.')[0]
                tgt_layer = LAYERS.get(target_mod)
                if tgt_layer and tgt_layer != src_layer and tgt_layer not in ALLOWED.get(src_layer, set()):
                    violations.append(f'{fpath}:{node.lineno} -- {src_layer}/{module} imports {tgt_layer}/{target_mod}')

if violations:
    print(f'FAIL: {len(violations)} layer violation(s)')
    for v in violations[:20]:
        print(f'  {v}')
    sys.exit(1)
else:
    print('PASS: no layer boundary violations')
"
```

Each violation is recorded with severity `high`, the offending file and line, and the boundary rule it breaks.

### Step 6 -- Detect undocumented structural changes

Compare the current module tree against what solution-intent documents. New top-level modules, renamed packages, or moved files that are not reflected in the architecture diagram are flagged as drift.

```bash
# List current top-level modules under the package
ls -d src/ai_engineering/*/  2>/dev/null | xargs -I{} basename {} | sort > /tmp/drift_current_modules.txt

# Extract modules documented in solution-intent (from the mermaid graph labels)
grep -oP '(?<=subgraph |^\s{8})\w+(?=\[")' docs/solution-intent.md | sort -u > /tmp/drift_documented_modules.txt

# Modules in code but not in docs
comm -23 /tmp/drift_current_modules.txt /tmp/drift_documented_modules.txt
```

```bash
# Detect files moved or renamed since the last solution-intent review date
LAST_REVIEW=$(grep -oP '(?<=Last Review: )\d{4}-\d{2}-\d{2}' docs/solution-intent.md)
git log --since="$LAST_REVIEW" --diff-filter=R --name-status --format="" -- src/
```

New modules not in the documented map are findings with severity `medium`. Renames detected via `git log --diff-filter=R` that are not reflected in solution-intent are severity `medium`.

### Step 7 -- Verify active decisions against code

For each decision in `$ACTIVE_DECISIONS`, run a targeted verification.

```bash
python -c "
import json, os, glob

with open('.ai-engineering/state/decision-store.json') as f:
    store = json.load(f)

checks = {
    'DEC-001': {
        'assertion': 'Flat skill layout -- no nested skill directories',
        'check': lambda: not any(
            os.path.isdir(os.path.join(d, sub))
            for d in glob.glob('.claude/skills/ai-*')
            for sub in os.listdir(d) if os.path.isdir(os.path.join(d, sub))
        ),
    },
}

active = [d for d in store['decisions'] if d['status'] == 'active' and d['category'] == 'architecture']
for dec in active:
    did = dec['id']
    if did in checks:
        result = checks[did]['check']()
        status = 'PASS' if result else 'FAIL'
        print(f\"{status}: {did} -- {checks[did]['assertion']}\")
    else:
        print(f'SKIP: {did} -- no automated check registered')
"
```

Each `FAIL` result is recorded as a finding with severity `high`. Each `SKIP` is noted in the report without creating a work item.

### Step 8 -- Create work items for drift findings

For each finding from Steps 4-7, create a task work item. Respect the 10-item mutation limit.

```bash
# GitHub Issues
gh issue create \
  --title "[architecture-drift] Layer violation: $SOURCE_LAYER imports $TARGET_LAYER" \
  --body "## Architecture Drift Finding

**Category:** $CATEGORY (import-cycle | layer-violation | undocumented-module | decision-mismatch)
**Severity:** $SEVERITY
**Evidence:** \`$FILE:$LINE\`
**Rule violated:** $RULE_DESCRIPTION
**Remediation:** $SUGGESTED_FIX

Detected by: architecture-drift runbook" \
  --label "architecture-drift"

# Azure DevOps
az boards work-item create --type Task \
  --title "[architecture-drift] $FINDING_SUMMARY" \
  --description "<body>" \
  --area "Project\\TeamName"
```

### Step 9 -- Generate drift report

Produce a structured report to stdout.

```
=== Architecture Drift Report ===
Run:                2026-03-28T10:00:00Z
Scan scope:         src/ai_engineering (22 modules)

Import cycles:      0 (threshold: 0)
Layer violations:   0 (threshold: 0)
Undocumented modules: 1
Decision mismatches:  0
---
Total findings:     1 / 10 max

Decision compliance:
  DEC-001: PASS (flat skill layout)
  DEC-005: PASS (single-source generation)
  DEC-019: SKIP (no automated check)

Structural changes since 2026-03-19:
  + ai_engineering/new_module/ (not in solution-intent)
  ~ ai_engineering/hooks/ -> ai_engineering/hook_manager/ (rename not documented)

Items created:      1
Mutations used:     1 / 10
```

## Output

Structured report to stdout. Work items created for confirmed findings. No local files are written.

## Guardrails

1. **Never modifies code.** This runbook reads source files, parses imports, and compares structure against documentation. It does not commit, push, merge, or alter any source file.
2. **Never modifies architecture docs.** Solution-intent, constitution, and the decision store are read-only inputs. Updating them is a human responsibility triggered by the findings.
3. **Mutations enabled by default.** Work items are created automatically.
4. **Bounded mutations.** A maximum of 10 work items are created per run. If findings exceed this limit, the report notes the overflow and stops creating items.
5. **Protected states.** Items in `closed` or `resolved` state are never reopened or modified. Labels `p1-critical` and `pinned` are never removed.
6. **Idempotent.** Before creating a work item, the runbook searches existing open issues for the same finding signature (category + file + rule). Duplicates are skipped.
7. **No inferred violations.** Only explicitly documented layers, boundaries, and decisions are checked. The runbook does not speculate about undeclared architectural intent.
