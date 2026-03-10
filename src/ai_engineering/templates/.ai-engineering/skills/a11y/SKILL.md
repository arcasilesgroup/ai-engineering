---
name: a11y
description: "Review frontend code for WCAG 2.1 AA compliance: semantic HTML, ARIA patterns, keyboard navigation, color contrast, and screen reader support."
metadata:
  version: 1.0.0
  tags: [accessibility, wcag, a11y, aria, keyboard, screen-reader]
  ai-engineering:
    scope: read-only
    token_estimate: 750
---

# Accessibility Review

## Purpose

Review frontend code for WCAG 2.1 AA compliance. Covers semantic HTML, ARIA attributes, keyboard navigation, focus management, color contrast, screen reader compatibility, and responsive accessibility. Provides actionable findings with severity-tagged remediation.

## Trigger

- Command: agent invokes accessibility skill or user requests a11y review.
- Context: pre-release review, new UI component, design system update, accessibility complaint, compliance audit.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"a11y"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Performance review** — use `perf-review` instead.
- **Security review** — use `sec-review` instead.
- **General code review** — use `code-review` instead.
- **Design system architecture** — use `agent:frontend-specialist` for holistic frontend review.

## Procedure

1. **Identify scope** — determine what to review.
   - Specific components, pages, or entire application.
   - Detect framework: React, React Native, Astro, Vue, etc.
   - Load relevant stack standard for framework-specific a11y patterns.

2. **Semantic HTML audit** — check structural semantics.
   - Exactly one `<h1>` per page. Heading hierarchy (h1→h2→h3) without skipping levels.
   - Landmarks: `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>` used correctly.
   - Lists: `<ul>`/`<ol>`/`<dl>` for list content, not styled `<div>`s.
   - Tables: `<table>` for data only, not layout. `<th>` with `scope` attribute.
   - Forms: `<label>` elements associated with inputs via `htmlFor`/`for`. `<fieldset>` + `<legend>` for groups.
   - Buttons: `<button>` for actions, `<a>` for navigation. No `<div onClick>`.

3. **ARIA attributes** — check ARIA usage.
   - ARIA used only when semantic HTML is insufficient (first rule of ARIA: don't use ARIA).
   - `aria-label` or `aria-labelledby` on all interactive elements without visible text.
   - `aria-expanded` on disclosure widgets (accordions, dropdowns).
   - `aria-live` regions for dynamic content updates (toasts, loading states).
   - `role` attributes match element behavior.
   - No redundant ARIA (e.g., `role="button"` on `<button>`).

4. **Keyboard navigation** — check keyboard accessibility.
   - All interactive elements focusable via Tab key.
   - Logical tab order matching visual order.
   - Focus visible: clear focus indicator (outline, ring) on all focusable elements.
   - Escape key closes modals/dropdowns.
   - Arrow keys navigate within composite widgets (tabs, menus, radio groups).
   - Skip navigation link for page-level keyboard users.
   - No keyboard traps.

5. **Color and contrast** — check visual accessibility.
   - Text contrast: minimum 4.5:1 for normal text, 3:1 for large text (WCAG AA).
   - Non-text contrast: minimum 3:1 for UI components and graphical objects.
   - Color not used as sole indicator (add icons, text, patterns).
   - Dark/light mode: contrast requirements met in both themes.

6. **Images and media** — check non-text content.
   - `alt` text on all informative images. Decorative images: `alt=""` or CSS background.
   - Descriptive alt text (context-dependent, not "image of...").
   - Video: captions and transcripts available.
   - Audio: transcripts available.

7. **Motion and animation** — check for motion sensitivity.
   - Respect `prefers-reduced-motion` media query.
   - No auto-playing animations longer than 5 seconds without pause control.
   - No flashing content (3 flashes per second limit).

8. **Report findings** — structured accessibility assessment.
   - Severity: critical (complete barrier) / major (significant difficulty) / minor (inconvenience) / info (best practice).
   - Each finding: WCAG criterion reference, description, impact, remediation.
   - Exhaustively address ALL findings — no partial reports.

## Output Contract

- Accessibility findings report with severity-tagged issues.
- WCAG 2.1 AA compliance status per criterion reviewed.
- Remediation plan for each finding with code examples.
- Verdict: PASS (no critical/major) / FAIL (critical/major found).

## Governance Notes

- Critical accessibility findings are blockers — same policy as security findings.
- Accessibility is not optional for user-facing applications.
- This skill reviews code; it does not replace manual testing with assistive technology.

### Iteration Limits

- Max 3 attempts to resolve the same accessibility issue. After 3 failures, escalate to user.

### Post-Action Validation

- After identifying findings, verify each against WCAG 2.1 AA success criteria.
- Cross-reference with framework-specific patterns (React, Astro, etc.).

## References

- `standards/framework/stacks/react.md` — React accessibility patterns.
- `standards/framework/stacks/react-native.md` — React Native accessibility patterns.
- `standards/framework/stacks/astro.md` — Astro accessibility patterns.
- `agents/build.md` — agent for holistic frontend review.
