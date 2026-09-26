# The `@google/design.md` CLI

The official tool — "the hands and eyes for design system work." It's the objective check on a DESIGN.md, and it should be run until clean before handing anything off.

Verified against **v0.4.0**.

**Contents**
- [Invocation](#invocation)
- [Commands](#commands)
- [The lint workflow](#the-lint-workflow)
- [Every rule and how to fix it](#every-rule-and-how-to-fix-it)
- [Verified gotchas](#verified-gotchas)
- [The `omitted` escape hatch](#the-omitted-escape-hatch)

---

## Invocation

No install needed:

```bash
npx -y @google/design.md@latest lint DESIGN.md
```

**Windows PowerShell** — `design.md` collides with file associations, so use the `designmd` alias:

```bash
npx -y -p @google/design.md designmd lint DESIGN.md
```

If a project already depends on it, `npm install @google/design.md` and drop the `-y`. All commands accept a file path or `-` for stdin.

Requires Node. If `npx` is unavailable, say so plainly rather than skipping the audit silently — an unaudited DESIGN.md should be flagged as such.

---

## Commands

```bash
design.md lint <FILE> [--format json|text]
design.md diff <FILE_A> <FILE_B> [--format json|text]
design.md export <FILE> --format <fmt> [--prefix <p>]
design.md spec [--rules] [--format markdown|json]
```

**`lint`** — validates structure, references, contrast, and section order. Exit `1` if any errors, `0` otherwise. **Warnings do not affect the exit code**, so never rely on exit status alone — parse the summary.

**`diff`** — token-level comparison of two DESIGN.md files. Reports additions, removals, modifications, and flags regressions. Exit `1` if regressions found. Genuinely useful in two places: showing the user what changed when revising a system, and comparing a codified-from-existing draft against a prior version.

**`export`** — converts tokens to `css-tailwind` (Tailwind v4 `@theme`), `json-tailwind` (v3 `theme.extend`, aliased as `tailwind`), `dtcg` (W3C Design Tokens), or `css-vars` (CSS custom properties, with optional `--prefix`). Not part of the default deliverable, but offer it if the user wants to wire the system into a codebase.

**`spec`** — prints the format spec; `--rules` appends the lint rule table. The full spec is already bundled at `references/designmd-spec.md`, so this is mainly for checking whether the format has moved past the version this skill was built against.

---

## The lint workflow

Use JSON — it's parseable and the paths point straight at the problem.

```bash
npx -y @google/design.md@latest lint --format json DESIGN.md
```

Output shape:

```json
{
  "findings": [
    {
      "severity": "error",
      "path": "components.button",
      "message": "Reference {colors.nope} does not resolve to any defined token.",
      "rule": "broken-ref"
    }
  ],
  "summary": { "errors": 1, "warnings": 5, "infos": 3 }
}
```

Loop until `errors: 0` and `warnings: 0`. Info findings are expected and fine — `token-summary` always fires, and `missing-sections` is informational.

Report the before/after counts to the user. "Initial lint: 1 error, 5 warnings → final: 0 errors, 0 warnings, 1 info" makes the audit visible instead of merely asserted.

---

## Every rule and how to fix it

| Rule | Severity | Trigger |
|---|---|---|
| `broken-ref` | error / warning | Unresolved or circular `{token.path}`; unknown component sub-token |
| `missing-primary` | warning | Colors defined but no `primary` |
| `contrast-ratio` | warning | A component's `backgroundColor`/`textColor` pair is below 4.5:1 |
| `orphaned-tokens` | warning | A **color** token no component references |
| `missing-typography` | warning | Colors defined but no typography tokens |
| `section-order` | warning | `##` sections out of canonical order |
| `unknown-key` | warning | A top-level YAML key that looks like a typo |
| `token-like-ignored` | warning | A top-level key that looks like tokens but isn't in the schema |
| `token-summary` | info | Always — a count of what's defined |
| `missing-sections` | info | `spacing` or `rounded` absent |
| `omitted-rules` | info | Redundant or unknown `omitted` entries |

### `broken-ref` — error

A `{path.to.token}` doesn't resolve. Check for a typo, a token you renamed, or a reference to a group (`{colors}`) instead of a leaf (`{colors.primary}`). Group references are only permitted inside `components`, and only for composite values like `{typography.body-md}`.

This is the one rule that must reach zero — an unresolved reference means an agent consuming the file gets nothing for that property.

### `broken-ref` — warning (unknown sub-token)

The same rule also fires as a *warning* for unrecognized component properties. The valid set is exactly eight:

```
backgroundColor, textColor, typography, rounded, padding, size, height, width
```

`borderColor`, `borderWidth`, `gap`, `shadow`, `opacity` are **not** valid and will warn. This is the most common surprise. Since borders and shadows are central to many directions, express them in the **Elevation & Depth** and **Shapes** prose instead — that's what the prose is for, and an agent reading the file will honor it.

### `missing-primary` — warning

Define a `primary` color token. The recommended semantic names are `primary`, `secondary`, `tertiary`, `neutral`, `surface`, `on-surface`, `error`. Without `primary`, a consuming agent auto-generates key colors and you lose control of the palette — which is precisely the failure this skill exists to prevent.

### `contrast-ratio` — warning

A component's text fails WCAG AA (4.5:1) against its own background.

**Fix the color, not the check.** Deleting `textColor` to silence it makes the design system actively harmful. Darken the text or lighten the background until the pair passes — see the contrast function in `color-craft.md` to compute it before linting rather than discovering it after.

Note the corollary: a component with a `backgroundColor` and no `textColor` is *skipped*, not passed. Define both together on every component that renders text, or the audit is checking nothing.

### `orphaned-tokens` — warning

A color token that no component references.

**Verified scope: this rule applies to colors only.** Unreferenced `typography`, `rounded`, and `spacing` tokens do not trigger it. That asymmetry is worth knowing, but don't exploit it — unused tokens in any category are usually decisions nobody needed.

Two legitimate fixes:
1. **Wire it** — if the token has a real job, add or extend a component that uses it. This is usually the right answer, and it's a useful forcing function: it means every color in your palette has a demonstrated use.
2. **Delete it** — if you can't name what it's for, it shouldn't be in the system.

Note that a color used only in the *prose* still counts as orphaned. Colors that genuinely live outside components need a component to anchor them, and two small patterns handle almost every case cleanly:

```yaml
components:
  page:                                   # anchors surface + on-surface,
    backgroundColor: "{colors.surface}"   # and gets the page-level pair
    textColor: "{colors.on-surface}"      # contrast-checked as a bonus
  divider:                                # anchors a border color, which has
    backgroundColor: "{colors.border}"    # no valid sub-token of its own —
    height: 1px                           # a 1px rule *is* a background
```

The `divider` pattern is worth remembering: since `borderColor` isn't a valid sub-token, a border color would otherwise be permanently orphaned. Modeling the rule as a component with a background and a height is accurate rather than a workaround, and it leaves the value tokenized. It also has no `textColor`, so it correctly skips the contrast check.

### `missing-typography` — warning

Colors are defined but no typography tokens are. Add them — a design system with color and no type isn't a design system. See `typography.md`.

### `section-order` — warning

`##` headings must appear in this sequence (any may be absent):

**Overview → Colors → Typography → Layout → Elevation & Depth → Shapes → Components → Do's and Don'ts**

Accepted aliases: "Brand & Style" for Overview, "Layout & Spacing" for Layout, "Elevation" for Elevation & Depth.

An `#` (h1) title is allowed and isn't parsed as a section. Unknown `##` sections (e.g. `## Iconography`) are preserved without error — but they still participate in ordering, so place them sensibly. **A duplicate section heading is an error and rejects the file.**

### `unknown-key` / `token-like-ignored` — warning

`unknown-key` catches near-miss typos (`typografy` → `typography`). `token-like-ignored` catches a top-level key that looks like a token map but isn't in the schema (e.g. `shadows:` or `borders:`) — it would be silently dropped on export, so the linter flags it.

The top-level schema is exactly: `version`, `name`, `description`, `omitted`, `colors`, `typography`, `rounded`, `spacing`, `components`. Anything else belongs in the prose.

### `missing-sections` / `token-summary` / `omitted-rules` — info

Informational. `missing-sections` notes absent `spacing` or `rounded` token blocks — worth acting on if the omission was accidental, and worth declaring via `omitted` if deliberate.

---

## Verified gotchas

Things confirmed by testing against v0.4.0 that aren't obvious from the docs:

1. **Warnings don't affect the exit code.** Only errors set exit `1`. Parse `summary`, don't trust `$?`.
2. **`orphaned-tokens` is colors-only.** Typography, rounded, and spacing tokens are never flagged as orphaned.
3. **Unknown component sub-tokens are warnings, not errors**, and they're reported under the `broken-ref` rule — so the rule name in a finding doesn't always mean what it sounds like. Read the message.
4. **`contrast-ratio` only fires when both `backgroundColor` and `textColor` are present** on the same component. Missing pairs pass silently.
5. **A broken `textColor` reference suppresses the contrast check** for that component — so fixing a `broken-ref` can *reveal* a new `contrast-ratio` warning. Always re-lint after fixing errors; the first clean pass is rarely the last.
6. **`missing-sections` refers to token blocks (`spacing`, `rounded`), not markdown sections.** Absent prose sections are not flagged at all.

---

## The `omitted` escape hatch

When a section genuinely doesn't apply, declare it rather than leaving it missing. This suppresses the warning *and* records the intent, which is the more valuable half.

```yaml
omitted:
  - spacing
  - section: rounded
    reason: "Zero-radius is a fixed property of the direction, not a scale"
```

Always prefer the object form with a `reason`. A future reader — human or agent — needs to know whether the omission was a decision or an oversight, and a bare string doesn't say.

Use this sparingly and honestly. `omitted` exists for sections that don't apply to the design, not as a way to reach a clean lint without doing the work. If `orphaned-tokens` or `missing-typography` is firing, the system is incomplete, and silencing it ships a worse design system with a better-looking audit.
