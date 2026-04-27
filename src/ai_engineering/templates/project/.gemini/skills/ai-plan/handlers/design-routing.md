# Handler: Design Routing

## Purpose

Auto-detect UI/frontend specs and route through `/ai-design` before task decomposition. UI work is common in target audience and `/ai-design` opt-in only means UI specs reach `/ai-dispatch` without design intent -- the developer pays the late cost. This handler inverts the default: route by keyword detection, allow `--skip-design` opt-out.

This file is read by `/ai-plan` at planning time. It is NOT a user-invocable skill (no frontmatter) and does NOT replace `/ai-design` itself -- it only decides whether `/ai-design` should run before task decomposition.

---

## Keyword Allowlist

Conservative substring match (case-insensitive) against the body of `.ai-engineering/specs/spec.md`. Matching ANY single keyword is sufficient to set `route_required=True`.

```
page, component, screen, dashboard, form, modal,
design system, color palette, typography, layout,
ui, ux, frontend, react component, vue component,
interface, mobile screen, responsive, accessibility
```

Rationale: keyword list curated from D-106-02. Conservative by design -- false positives are mitigated by the explicit log line (so user sees rationale) and the `--skip-design` override.

---

## Detection Logic

1. Read the body of `.ai-engineering/specs/spec.md` (the active spec). Strip the YAML frontmatter; keep only the markdown body.
2. Lowercase the body once.
3. For each keyword in the allowlist, perform a substring search against the lowercased body.
4. Collect every keyword that matches into `matched_keywords` (a deduplicated list, preserving allowlist order).
5. If `matched_keywords` is non-empty, set `route_required=True`. Otherwise `route_required=False`.

This is intentionally a substring match (not a token match) so multi-word keywords like `design system` and `react component` work without tokenization. False-positive risk is acknowledged in R-2 and accepted in exchange for the simpler matcher; the `--skip-design` override is the safety valve.

---

## Override Flag

When the user invokes `/ai-plan --skip-design`, the handler short-circuits:

- Skip detection entirely.
- Set `route_required=False` regardless of keywords present.
- Emit the log line `design-routing: skipped (--skip-design)` so the decision is auditable.

The override is per-invocation -- it does NOT persist to the plan or change the default for subsequent invocations of `/ai-plan`.

---

## Routing Flow

When `route_required=True` AND `--skip-design` was NOT passed:

1. Resolve the spec ID from the spec frontmatter (`spec: spec-NNN`). If not present, fall back to the spec filename stem.
2. Determine the design-intent path:
   - Per-spec subdirectory: `.ai-engineering/specs/<spec-id>/design-intent.md` when `<spec-id>` is known.
   - Fallback: `.ai-engineering/specs/design-intent.md` when `<spec-id>` cannot be resolved.
3. Invoke `/ai-design` with the spec body as input context.
4. Capture the `/ai-design` output and write it to the resolved design-intent path.
5. Proceed to plan integration (below).

When `route_required=False`:

1. Skip steps 1 through 5 above.
2. Proceed directly to task decomposition.

---

## Plan Integration

When routing occurred (`route_required=True` AND override NOT set), `/ai-plan` adds a `## Design` section to `plan.md` immediately after the title block. The section links the design-intent artifact:

```markdown
## Design

Design intent captured at `.ai-engineering/specs/<spec-id>/design-intent.md` (auto-routed from /ai-plan because matched keywords: page, dashboard).
```

This makes the design context discoverable to `/ai-dispatch` and downstream agents without re-running `/ai-design`. If the user wants to re-generate the design intent, they invoke `/ai-design` directly.

When routing was skipped (no keywords matched OR `--skip-design` set), no `## Design` section is added.

---

## Output Behavior

The handler emits exactly one log line per invocation, stating the routing decision and the rationale. This is mandatory for R-2 (false-positive mitigation): the user must always see WHY a routing decision was made.

| Scenario | Log line |
|----------|----------|
| Keywords matched, no override | `design-routing: routed (matched keywords: <comma-separated list>)` |
| No keywords matched | `design-routing: skipped (no keywords matched)` |
| Override flag passed | `design-routing: skipped (--skip-design)` |

Examples:

```
design-routing: routed (matched keywords: page, dashboard, responsive)
design-routing: skipped (no keywords matched)
design-routing: skipped (--skip-design)
```

The log line goes to stdout (or the equivalent observable surface for the IDE) so it is captured in session transcripts and telemetry.

---

## Consumers

This handler is consumed by:

- `.gemini/skills/ai-plan/SKILL.md` -- Process step "Design routing" runs this handler before task decomposition.

When this handler improves, `/ai-plan` inherits the improvement automatically.
