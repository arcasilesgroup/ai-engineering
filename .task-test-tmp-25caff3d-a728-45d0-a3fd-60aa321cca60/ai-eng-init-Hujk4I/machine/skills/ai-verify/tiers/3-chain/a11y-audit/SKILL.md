---
name: a11y-audit
description: Audit the UI for accessibility defects against WCAG 2.2 AA — semantic structure, keyboard operability, focus management, form labeling, ARIA correctness, contrast, and motion — with each finding tied to the user it locks out. Use when asked to check accessibility or a11y, review UI for screen-reader or keyboard support, or verify WCAG compliance.
---

# Accessibility audit

Find the places where someone cannot use this app. Every finding names the
**user and the barrier**: "a keyboard user cannot dismiss this dialog" is a
finding; "missing ARIA attributes" is a lint message.

Read `.claude/review/CONVENTIONS.md` first — stack detection, scope, severity,
false-positive gate, report format. Target is **WCAG 2.2 level AA**.

WCAG is an external standard, so this skill is largely stack-independent — but
where the checks below name a file or a styling mechanism, map it to whatever
this project actually uses. Identify these three things up front:

- **The root document shell** — wherever `<html lang>`, landmarks, and the
  page skeleton are set (a root layout, a template, `index.html`, a base view).
- **The global stylesheet and design tokens** — wherever focus resets, color
  variables, and motion settings live.
- **The styling mechanism** — utility classes, CSS modules, CSS-in-JS, or plain
  stylesheets. This decides how you resolve a color to an actual value in §6.

## Checklist

**1. Semantics before ARIA**
The most common real defect is a `<div>` doing a control's job. A `<div
onClick>` is invisible to screen readers, not focusable, and does not fire on
Enter/Space — use `<button>`. Likewise: `<a>` for navigation, `<button>` for
actions (an `<a>` with no `href` is not focusable), real `<ul>/<li>` for lists,
`<table>` with `<th scope>` for tabular data.

Check landmarks (`main`, `nav`, `header`, `footer`) exist and are not duplicated
without labels; exactly one `<h1>` per page; heading levels that descend without
skipping; `<html lang>` set in the root document shell.

**The first rule of ARIA is not to use ARIA.** A native element with correct
semantics beats `role="button"` plus three attributes. Report added ARIA as a
finding when a native element would have worked.

**2. Keyboard operability**
Walk each interactive element and ask: can I reach it with Tab, operate it with
Enter/Space, and leave it?

- Anything interactive must be reachable. `tabIndex={-1}` on a control, or a
  custom widget with no `tabIndex`, removes it.
- **Focus traps** — modals/menus that keep focus inside with no Escape route.
  Critical severity: the user is stuck.
- **Positive `tabIndex`** (`tabIndex={1}`+) breaks document order. Always a finding.
- Tab order must follow visual order — watch for CSS (`order`, `flex-direction:
  row-reverse`, absolute positioning) that reorders visually but not in the DOM.
- Custom widgets need their expected key handling (Escape closes, arrows move
  within a composite control).

**3. Focus management and visibility**
Focus must always be visible. A focus outline removed with no `:focus-visible`
replacement is the single most common instance — grep for `outline-none`,
`outline: none`, and `outline: 0` across styles and utility classes. The
indicator needs 3:1 contrast against its background.

On dynamic changes: focus moves into an opened dialog and returns to the trigger
on close; route changes do not strand focus on a removed element; content that
appears (errors, results) is announced or focused. A "skip to main content" link
should exist when there is repeated navigation.

**4. Forms**
Every input has a programmatic label — `<label htmlFor>`, `aria-label`, or
`aria-labelledby`. Placeholder is not a label; it disappears on input. Required
fields marked with `required`/`aria-required`, not color or an asterisk alone.
Errors associated via `aria-describedby` and announced (`role="alert"` or a live
region), not communicated by red border alone. Related radios/checkboxes wrapped
in `<fieldset>` with `<legend>`. Autocomplete attributes on personal-data fields.

**5. Images and non-text content**
Meaningful images need `alt` describing their *function*, not their appearance —
a logo linking home is `alt="Home"`. Decorative images take `alt=""` (present and
empty, never missing). Icon-only buttons need an accessible name. Inline SVGs
need `role="img"` + `<title>`, or `aria-hidden="true"` when decorative. Text
baked into an image is a finding.

**6. Contrast and color**
AA: **4.5:1** for body text, **3:1** for large text (≥18.66px bold / ≥24px) and
for UI component boundaries and focus indicators.

Resolve every color to an actual value — follow utility classes to the theme
config, CSS variables to their definitions, and tokens to the design system — then
**compute** the ratio. Do not eyeball it. Watch for low-contrast conventions: mid
grays on white, placeholder text, disabled states that still need to be readable,
and text over images or gradients. Check both light and dark themes if
`prefers-color-scheme` or a theme toggle is present — a pair that passes in light
often fails in dark.

Color must never be the only carrier of meaning (status by hue alone, links
distinguished from body text by color alone).

**7. Motion, timing, zoom**
Animations respect `prefers-reduced-motion` — check the global stylesheet and
any animation utilities or libraries. Nothing auto-plays or auto-advances without a pause
control. No content lost at 200% zoom or 320px width. No horizontal scroll of the
page body at narrow widths.

**8. Dynamic content**
Live regions (`aria-live`) for content that updates without a user action —
toasts, async results, validation. Loading states announced, not just spinners.
`aria-expanded` / `aria-controls` on disclosure triggers, kept in sync with state.
Content hidden visually must also be hidden from assistive tech (`display:none`
or `hidden`, not `opacity-0` alone, which leaves it focusable).

## Method

1. Detect the stack and resolve scope per `CONVENTIONS.md`; identify the
   components and routes in play.
2. Read the root document shell and the global stylesheet first — lang,
   landmarks, focus resets, motion settings, and the color system are established
   there and affect every page.
3. For each interactive component, walk it as a keyboard user, then as a screen
   reader user: what is announced, in what order, and what happens on activation?
4. Resolve and compute contrast for every text/background pair you find.
5. **Verify pass.** Check the parent for a label or role you missed, check
   `globals.css` for a global `:focus-visible` style, and confirm a component is
   actually rendered before reporting it. Drop what does not survive.
6. Report.

Static review cannot see computed styles or real screen-reader output. State that
limit honestly in `Not covered` rather than guessing — and note that an automated
checker run against the running app complements this review by catching
computed-style issues. `npx @axe-core/cli <dev-url>` works for any web app
regardless of framework; use the project's own dev URL and port.

## Report

Follow the output contract in `CONVENTIONS.md`. Write to
`.claude/reviews/a11y-audit-<stamp>.md`.

Add the WCAG criterion to each finding, and write **Trigger** as the blocked user:

- **[HIGH] Icon-only close button has no accessible name** — WCAG 4.1.2
- **Where:** `src/components/Dialog.tsx:34`
- **Trigger:** screen-reader user reaches the button; it announces as "button"
- **Consequence:** no way to know it closes the dialog
- **Fix:** add `aria-label="Close dialog"`

Severity by exclusion: **Critical** = a user group cannot complete a core task
(focus trap, unreachable control). **High** = a task is possible but seriously
degraded. **Medium** = friction or a failure on a secondary path. **Low** = polish.

## Relationship to `design-check`

Your source of truth is **WCAG**, not `design.md`. A defect is a defect whether or
not the design document asked for it — so:

- **"The design specified it" is never a defense.** If the spec mandates 3:1 body
  text, that is a finding here, and the fix is to change the design. (WCAG 2.2 AA
  requires 4.5:1 for body text.)
- Do not read `design.md` to decide what is correct, and do not report a
  divergence from the spec — that is `design-check`'s job and it will catch it.
- When a finding traces back to something the design explicitly mandates, note
  `design-specified` on it. `full-review` pairs that with `design-check`'s
  conformance verdict and reports the conflict, which is how the design gets
  fixed rather than the two reviews quietly cancelling out.

This skill therefore runs and produces full value even when no design document
exists.
