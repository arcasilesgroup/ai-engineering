---
name: wiring-scanner
description: "Detect implemented but disconnected code: functions, modules, or exports that exist but are not connected to any entry point, route, CLI command, or consumer"
type: operational
cadence: weekly
---

# Wiring Scanner

## Objetivo

Detect implemented but disconnected code -- functions, modules, or exports that exist in the codebase but are never reached from any entry point, CLI command, or external consumer. This runbook does not delete code; it classifies each public symbol's connectivity and creates task work items for confirmed disconnections so the team can decide whether to wire, document, or remove them.

## Precondiciones

- `grep` available for symbol search and reference counting.
- `python3` available if using dynamic import detection.
- `gh` or `az` CLI authenticated for work item creation and deduplication.
- Source code organized under `src/` with Python modules.

## Procedimiento

### Step 1 -- Enumerate public functions and classes

Collect every public function and class definition across `src/`. Exclude private symbols (prefixed with `_`) since they are internal by convention and not expected to appear in external import chains.

```bash
grep -rn "^def \|^class " src/ --include="*.py" \
  | grep -v "^.*:def _" \
  | grep -v "^.*:class _"
```

Store each result as a record: `{symbol_name, file_path, line_number, kind: function|class}`. Record the total count as `$TOTAL_SYMBOLS` for the summary report.

### Step 2 -- Enumerate CLI command registrations

Identify all typer commands registered in the CLI entry points. These are the top-level wiring points -- any function reachable from a registered command is considered connected.

```bash
# Find typer app instances and their command registrations
grep -rn "\.command\(\|\.callback\(\|@app\." src/ --include="*.py"

# Find the main CLI entry point and its sub-app imports
grep -rn "app.add_typer\|typer.Typer" src/ --include="*.py"
```

Build a set `$CLI_ENTRY_POINTS` containing every function name registered as a typer command or callback.

### Step 3 -- Enumerate __init__.py exports

Collect all symbols exported via `__all__` in `__init__.py` files. These represent the package's public API surface.

```bash
grep -rn "__all__" src/ --include="__init__.py" -A 20
```

Parse each `__all__` list into a set `$EXPORTED_SYMBOLS`. Symbols that appear in `__all__` but have no external callers may indicate an API that was declared but never consumed.

### Step 4 -- Search for import and call references

For each public symbol from Step 1, search for evidence of usage: imports, direct calls, or attribute references. Scan both production code and tests to distinguish wiring categories.

```bash
# Search production code for imports or calls
grep -rn "SYMBOL_NAME" src/ --include="*.py" | grep -v "^.*:def SYMBOL_NAME\|^.*:class SYMBOL_NAME"

# Search test code for imports or calls
grep -rn "SYMBOL_NAME" tests/ --include="*.py"
```

For each symbol, record two counts: `$SRC_REFS` (references in `src/` excluding the definition itself) and `$TEST_REFS` (references in `tests/`). A reference is any line containing the symbol name as a discrete token -- import statements, function calls, class instantiations, or type annotations.

### Step 5 -- Classify each symbol

Apply the following classification rules based on reference counts and entry-point reachability.

| Classification | Condition | Action |
|---------------|-----------|--------|
| **Connected** | `$SRC_REFS > 0` and symbol is reachable from a CLI entry point or `__init__.py` export | No action needed |
| **Test-only** | `$SRC_REFS == 0` and `$TEST_REFS > 0` | Log separately; may be intentional internal API |
| **Disconnected** | `$SRC_REFS == 0` and `$TEST_REFS == 0` | High-confidence finding; create work item |
| **Orphaned module** | All public symbols in a module are disconnected, and no other module imports from it | High-confidence finding; create work item for the entire module |

For **Connected** classification, verify reachability by tracing the import chain. A symbol referenced only by another disconnected symbol is not truly connected.

```bash
# Trace one level of the import chain for a symbol
IMPORTING_MODULE=$(grep -rln "import SYMBOL_NAME\|from .* import.*SYMBOL_NAME" src/ --include="*.py")
# Check if the importing module itself has callers
grep -rn "$(basename "$IMPORTING_MODULE" .py)" src/ --include="*.py" | grep -c "import"
```

### Step 6 -- Filter by confidence threshold

Only report findings that meet the minimum confidence threshold (`min_confidence: 0.8`). Confidence is computed as:

- **1.0** -- Zero references in both `src/` and `tests/` (truly dead)
- **0.9** -- Zero references in `src/`, present only in `tests/` as a fixture or helper target
- **0.8** -- Referenced only by other disconnected symbols (transitive disconnection)
- **< 0.8** -- Ambiguous cases (dynamic imports, `getattr` usage, plugin registries) -- exclude from report

```bash
# Check for dynamic import patterns that reduce confidence
grep -rn "importlib\|getattr\|__import__\|globals()" src/ --include="*.py" | grep -c "SYMBOL_NAME"
```

If a symbol appears in any dynamic import pattern, downgrade confidence to 0.5 and exclude it from work item creation.

### Step 7 -- Create work items for disconnected findings

For each finding that passes the confidence filter, check for an existing open issue before creating a new one. Respect the `max_findings_per_run` limit (15).

```bash
# Deduplicate: check for existing open issue
gh issue list --state open --label "dead-code" --search "in:title SYMBOL_NAME" --json number,title

# GitHub -- create task
gh issue create \
  --title "[dead-code] SYMBOL_NAME in file_path:line" \
  --label "dead-code" \
  --body "**Symbol:** SYMBOL_NAME | **File:** file_path:line | **Kind:** function|class
**Classification:** disconnected | orphaned-module | **Confidence:** 0.9

Evidence: 0 import/call refs in src/, 0 refs in tests/.
Action: wire to entry point, document as internal API, or remove.
*Created by wiring-scanner runbook*"

# Azure DevOps -- create task
az boards work-item create --type Task \
  --title "[dead-code] SYMBOL_NAME in file_path:line" \
  --description "Symbol: SYMBOL_NAME | File: file_path:line | Classification: disconnected | Confidence: 0.9" \
  --fields "System.Tags=dead-code"
```

Stop after 15 items; log any overflow in the report and defer to the next run.

### Step 8 -- Generate summary report

Produce a structured report to stdout and optionally as a PR comment or workflow artifact.

```
=== Wiring Scanner Report ===
Date:               <TIMESTAMP>
Scan scope:         src/ (all Python modules)

Symbol Census:
  Total public symbols:   <TOTAL_SYMBOLS>
  Connected:              <N> (<CONNECTED_PCT>%)
  Test-only:              <N>
  Disconnected:           <N>
  Orphaned modules:       <N>

Confidence Distribution:
  1.0 (zero refs):        <N>
  0.9 (test-only ref):    <N>
  0.8 (transitive):       <N>
  Excluded (< 0.8):       <N>

Work Items:
  Created:                <N>
  Skipped (existing):     <N>
  Deferred (over limit):  <N>

Orphaned Modules:
  <module_path> -- <N> public symbols, 0 external imports
  ...
==============================
```

## Output

Disconnected code report to stdout. Work items created for confirmed dead code. No local files are written.

## Guardrails

1. **Never deletes code.** This runbook inspects source files and creates task work items. It does not commit, push, merge, or alter any source file.
2. **Test-only wiring is reported separately.** Symbols referenced only from `tests/` are logged in the report under "Test-only" but are not escalated to work items by default. They may represent intentional internal APIs exercised through unit tests.
3. **Dynamic imports reduce confidence.** Symbols found in `importlib`, `getattr`, or plugin registry patterns are excluded from findings to avoid false positives against pluggable architectures.
4. **Bounded mutations.** A maximum of 15 work items are created per run. If the finding count exceeds this limit, the report notes the overflow and defers remaining items to the next run.
5. **Mutations enabled by default.** All qualifying findings are created as work items automatically.
6. **Protected states.** Items in `closed` or `resolved` state are never reopened or modified. Labels `p1-critical` and `pinned` are never removed.
7. **Idempotent.** Before creating a work item, the scanner searches existing open issues for the symbol name and file path. Duplicates are skipped and logged.
