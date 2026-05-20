# Plan Schema

Contract for `.ai-engineering/specs/plan.md` files produced by `/ai-plan`
and consumed by `/ai-build`. Sub-spec plans under
`.ai-engineering/runtime/autopilot/sub-NNN/plan.md` (produced during
`/ai-autopilot` Phase 3) honour the same contract.

## Required Frontmatter

| Field | Type | Example |
|-------|------|---------|
| `spec` | string | `spec-126` |
| `title` | string | `Hook-side NDJSON Append Lock Parity` |
| `status` | enum | `draft` \| `approved` \| `in-progress` \| `shipped-pending-pr-merge` \| `shipped` |
| `pipeline` | enum | `standard` \| `autopilot` |
| `phases` | integer | `5` |
| `execution_route` | object | see "Execution Route" below |

Notes:

- `status: shipped-pending-pr-merge` is the legitimate post-implementation
  state between PR open and merge. During this window the plan rotates
  from a checkbox task list to an aggregate index (see "Lifecycle" below);
  the task-line contract is **relaxed** for this status only.
- `status: shipped` is the post-merge terminal state. Plans in this state
  are usually rotated to `.ai-engineering/specs/archive/<spec>/plan.md`
  by `/ai-pr` cleanup.
- `status` is the only approval source of truth. Do not add `approved`,
  `approval`, or similar fields under `execution_route`.

## Execution Route

New plans include an `execution_route` frontmatter object so `/ai-plan`
records the next framework executor without auto-dispatching it:

| Field | Type | Example |
|-------|------|---------|
| `version` | integer | `1` |
| `spec` | string | `spec-145` |
| `executor` | enum | `build` \| `autopilot` |
| `automation` | enum/string | `hitl` |
| `concern_count` | integer | `1` |
| `estimated_files` | integer | `4` |
| `reason` | string | `Single-concern plan below autopilot threshold.` |
| `safe_next_command` | enum | `/ai-build` \| `/ai-autopilot` |

`executor: build` requires `safe_next_command: "/ai-build"`.
`executor: autopilot` requires `safe_next_command: "/ai-autopilot"`.
Host capacity, RAM, swap, pressure, and `ok_to_dispatch` data are not
plan metadata and do not participate in plan approval.

## Required Sections

| Section | Content |
|---------|---------|
| `# Plan: <spec>` or `# Plan — <spec>` | Top-level H1 anchor identifying the spec the plan implements. |
| `## Tasks` (or per-phase H2 like `## Phase 1: …`) | Container for the task checkbox list. |

When `pipeline: autopilot`, the aggregate `plan.md` may delegate task
detail to per-sub-spec plans under
`.ai-engineering/runtime/autopilot/sub-NNN/plan.md`. The aggregate file
keeps only the wave-level summary (see "Lifecycle" below).

## Task Line Format

Every executable task line MUST start with a Markdown checkbox using
exactly the `- [ ]` (pending) or `- [x]` / `- [X]` (done) form, at
zero indent or any nested level. The validator matches this regex:

```
^\s*-\s*\[([ xX])\]
```

Conventional shape:

```markdown
- [ ] **T-<phase>.<index>**: <imperative description>
  <optional 2-line context / acceptance>
```

Examples (taken from `.ai-engineering/specs/archive/spec-126-lock-parity/plan.md`):

```markdown
- [x] **T-1.1**: Create `.ai-engineering/scripts/hooks/_lib/locking.py` as
      the hook-layer mirror of `src/ai_engineering/state/locking.py`.
- [x] **T-2.1**: RED — write `tests/unit/hooks/test_locked_append_retry.py`
      asserting retry-on-stale-lock semantics.
```

**Anti-patterns** (flagged by the validator):

- `- T-1.1: …` (no checkbox at all)
- `* [ ] T-1.1: …` (bullet style other than `- `)
- `- [ok] T-1.1: …` (non-canonical marker)
- A task line with no `T-N.M` identifier is allowed but not preferred —
  the validator only requires the checkbox, identifier convention is a
  documentation aid.

## Counting Contract

`session_bootstrap.py` and other tooling derive `tasks_total` /
`tasks_done` from the checkbox count. Sections that mix non-task
checkboxes (e.g., requirements lists, decision rosters) MUST live
**outside** the `## Tasks` / `## Phase …` containers, OR they will be
counted alongside real tasks. If you need a checkbox-style list that is
not a task, use `* [ ]` (asterisk bullet) instead of `- [ ]` — the regex
anchors on `-`.

## Lifecycle

A plan progresses through the following states:

1. `draft` — `/ai-plan` first emits the plan but hasn't finalised it.
2. `approved` — operator approves; `/ai-build` can now execute.
3. `in-progress` — tasks are being checked off during build.
4. `shipped-pending-pr-merge` — `/ai-pr` opened the PR; plan file may
   rotate to a wave-level summary index (autopilot pipeline). Task
   regex is intentionally relaxed for this status to allow the
   summary-format rotation.
5. `shipped` — PR merged; plan archived to
   `.ai-engineering/specs/archive/<spec>/plan.md` by `/ai-pr` cleanup.

## Validation Rules

Enforced by `tools/spec_lint/checks/plan.py` (invoked by
`python -m spec_lint --check` when a sibling `plan.md` exists):

1. **Frontmatter present**: file must start with a YAML frontmatter
   block containing at minimum the `spec`, `title`, `status` fields.
2. **Status is enum**: `status` must be one of the five enum values.
3. **Task lines exist** when `status` ∈ `{draft, approved, in-progress}`:
   the file must contain at least one line matching `^\s*-\s*\[([ xX])\]`.
4. **Task line shape**: every line that looks like a checkbox bullet
   (`- [` at start, allowing leading whitespace) must use the canonical
   `[ ]` / `[x]` / `[X]` form; deviations (`[?]`, `[ok]`, `[*]`, etc.)
   emit a BLOCKER.
5. **Shipped exemption**: when `status` ∈ `{shipped-pending-pr-merge,
   shipped}`, rule 3 is skipped — these states legitimately carry no
   active tasks (the file rotated to an aggregate index).
6. **No duplicate task IDs**: when present, `T-<phase>.<index>` tokens
   must be unique within the file. ADVISORY (not BLOCKER) so the rule
   does not break sub-spec plans that share a numbering range.
7. **Execution route shape**: when `execution_route` is present,
   `executor` must be `build` or `autopilot`, `safe_next_command` must
   match the executor, `execution_route.spec` must match plan `spec`,
   and approval fields inside `execution_route` are forbidden.

## Why This Schema Exists

- `/ai-build` reads the checkbox state to track progress; without
  checkboxes there is no contract.
- `session_bootstrap.py` surfaces `tasks_done / tasks_total` on
  `/ai-start` — a malformed plan makes the dashboard misleading
  (operator-pain #18b instance).
- The shipped-state exemption is what lets `spec-131`'s aggregate-index
  rotation coexist with the checkbox contract without false positives.
