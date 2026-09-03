# Accessibility reference — Ally checklist (WCAG 2.2 AA)

Ally is the accessibility checker used in Blackboard/Anthology learning environments. It is based on WCAG 2.2 AA, with additional checks that target usability and quality above the conformance floor. This reference translates Ally's categories into a design-build checklist.

## Conformance levels: AA vs AAA

**AA is the floor.** Most legislation worldwide (ADA, EN 301 549, Section 508) aligns with WCAG 2.2 AA. It is the default.

**AAA is the target for text-heavy interfaces.** When the page's job is reading — long-form content, reports, documentation — aim for AAA on contrast and target size.

| Check | AA | AAA |
|---|---|---|
| Text contrast (normal) | 4.5:1 | 7:1 |
| Text contrast (large ≥ 18pt or ≥ 14pt bold) | 3:1 | 4.5:1 |
| Non-text contrast (UI elements, graphical objects) | 3:1 (1.4.11) | — |
| Target size (WCAG 2.5.8) | 24×24px | 44×44px (2.5.5) |
| Input font on mobile | 16px | 16px |

The audit passes `--aa` to relax the contrast target from AAA to AA.

## Semantic code and ARIA attributes

Native elements carry meaning by default. ARIA is for when HTML does not have a built-in role.

### Principles

- **Native first.** Use `<button>`, `<nav>`, `<main>`, `<h1>`-`<h6>`, `<ul>`, `<table>` with `<th scope>`, `<label>`. Only reach for ARIA when no element does the job.
- **Accessible names.** Every interactive element must have an accessible name. Via text content, `aria-label`, `aria-labelledby`, `title`, or inner `img[alt]` — one must exist and not be empty.
- **ARIA validity.** Roles must be valid WAI-ARIA values. Attributes must be allowed on that role, use valid names, and conform to valid value types.
- **Required attributes.** `aria-level` on `role=heading`, `aria-checked` on `role=checkbox`, `aria-sort` on `role=columnheader`, etc. Required attributes must be present.
- **Owned and contained elements.** `role=listitem` must be contained by a list; `role=option` must be owned by a listbox/menu; `role=tab` by `role=tablist`. Roles must be contained by their expected parents.
- **No tabindex > 0.** Positive tabindex breaks the DOM reading order. Use `tabindex="-1"` only to remove from tab order (and provide an alternative).
- **No aria-hidden on focusable elements.** `aria-hidden="true"` on a focusable element makes it invisible to screen readers but reachable by keyboard.
- **Skip link first.** The page should have a skip link as its first visible link, pointing to an on-page fragment (usually `#main`).
- **Landmarks.** All content should be inside a landmark region (`header`, `nav`, `main`, `aside`, `footer`, or equivalent `role`).
- **Language.** `<html>` must have a valid `lang` attribute. Parts in a different language must have `lang` set.
- **Title.** Every document must have a non-empty `<title>` element.
- **Unique IDs.** `id` values must be unique within the page.
- **Unique accesskeys.** `accesskey` values must be unique.

### Ally checklist items mapped to browser checks

| Check | Severity | WCAG |
|---|---|---|
| `<html>` has valid `lang` | High | 3.1.1 |
| Non-empty `<title>` | High | 2.4.2 |
| Image missing `alt` attribute | High | 1.1.1 |
| Heading structure present, starts at H1, no empty headings | High | 1.3.1, 2.4.6 |
| Heading levels skip by more than one | Medium | 1.3.1 |
| Heading structure goes beyond 6 levels | Low | 1.3.1 |
| Links have discernible text | High | 1.1.1, 4.1.2 |
| Buttons have discernible text | High | 4.1.2 |
| Form controls have associated label | High | 1.3.1, 3.3.2 |
| Form controls have a visible label (not placeholder-only) | High | 3.3.2 |
| Radio/checkbox with same name in a `<fieldset>` or `role=group` | High | 1.3.1 |
| Valid ARIA roles on every `[role]` element | High | 4.1.2 |
| ARIA attribute names are valid | High | 4.1.1, 4.1.2 |
| ARIA attribute values conform to valid values | Medium | 4.1.2 |
| Required ARIA attributes are present per role | Medium | 4.1.2 |
| No `aria-hidden="true"` on focusable elements | High | 4.1.2 |
| No `tabindex > 0` | Medium | 2.1.1 |
| Unique IDs (no duplicates) | Medium | 2.4.2 |
| Unique accesskeys (no duplicates) | Low | 2.1.1 |
| No deprecated `<blink>` or `<marquee>` | High | 2.2.2 |
| Timed refresh (`meta http-equiv=refresh`) | High | 2.2.1, 2.2.4, 3.2.5 |
| Video has `<track kind="captions">` | Medium | 1.2.2, 1.2.3 |
| Video has audio description track | Medium | 1.2.5 |
| All `<td>` in tables larger than 3×3 have an associated `<th>` | High | 1.3.1 |
| All `<th>` elements have data cells they describe | High | 1.3.1 |
| Table headers use `scope` attribute | Medium | 1.3.1 |
| Data cells do not duplicate caption text | High | 1.3.1 |
| `<ul>`/`<ol>` contain only `<li>` children | Low | 1.3.1 |
| `<dt>`/`<dd>` are contained by `<dl>` | Low | 1.3.1 |
| Frames/iframes have unique, non-empty title | Medium | 2.4.1 |
| Skip link is the first link on the page | High | 2.4.1 |
| Content is contained in a landmark region | High | 1.3.1 |
| Zoom not disabled (`user-scalable=no`) | High | 1.4.4 |
| Zoom allows maximum scale of 5 | Medium | 1.4.4 |

## Accessibility of downloadable documents

Design work produces more than pages: PDFs, Word documents, and PowerPoint decks. Ally checks them with the same principles as HTML.

### PDF checklist

| Check | Severity | What to verify |
|---|---|---|
| PDF is malformed | Severe | Openable, not corrupted |
| PDF is encrypted | Severe | Not password-protected |
| PDF is scanned (image layer only) | Severe | Must be tagged text with reading order |
| PDF is untagged | Major | Must have a tag tree (reading order) |
| PDF does not have a language set | Minor | `lang` attribute on the PDF root |
| PDF does not have the correct language | Minor | Correct language value in metadata |
| Images without alternative descriptions | Major | Every image has alt text |
| Text with contrast issues | Major | Meets AA/AAA contrast thresholds |
| No headings present | Major | Structure present (3+ pages) |
| Heading structure not appropriate | Minor | H1 start, no skips between levels |
| Heading structure does not start at H1 | Major | First heading is H1 |
| Heading structure goes beyond 6 levels | Minor | ≤ 6 heading levels |
| Tables without headers | Major | `<th>` elements with `scope` |
| No document title | Minor | `Title` metadata field |

### Word / LibreOffice Writer checklist

| Check | Severity | What to verify |
|---|---|---|
| Document is malformed | Severe | Openable |
| Document is encrypted | Severe | Not password-protected |
| Language not set | Minor | `lang` in document properties |
| Language incorrect | Minor | Correct `lang` value |
| Images without alt text | Major | Alternative text on every image |
| Text with insufficient contrast | Major | AA/AAA contrast |
| No headings | Major | Heading structure present (12+ paragraphs) |
| Heading structure not appropriate | Minor | H1 start, no skips |
| Heading does not start at H1 | Major | First heading is H1 |
| Heading goes beyond 6 levels | Minor | ≤ 6 levels |
| Tables without headers | Major | Header cells with `scope` |

### PowerPoint / LibreOffice Impress checklist

| Check | Severity | What to verify |
|---|---|---|
| Presentation is malformed | Severe | Openable |
| Presentation is encrypted | Severe | Not password-protected |
| Language not set | Minor | `lang` in document properties |
| Language incorrect | Minor | Correct `lang` value |
| Images without alt text | Major | Alt text on every image |
| Text with insufficient contrast | Major | AA/AAA contrast |
| No heading (title) | Major | One title per ~7 slides |
| Tables without headers | Major | Header cells with `scope` |

## Design flexibility: responsive, zoom, and orientation

The interface must work in any viewport, any orientation, any zoom.

| Check | Severity | What to verify |
|---|---|---|
| Zoom not disabled | High | No `user-scalable=no`; viewport allows 200% zoom |
| Maximum scale of 5 | Medium | `maximum-scale` not lower than 5 (Ally recommendation) |
| Orientation not locked | Major | Content reflows in both orientations; no `screen.orientation.lock()` or `@media`-only portrait/landscape code |
| Reflow at 320px | Major | No horizontal overflow at 320px equivalent width |
| 16px minimum input font | Major | `font-size: 16px` on inputs (prevents iOS auto-zoom on focus) |
| Touch target floor | Major | 24×24px minimum (WCAG 2.5.8 AA); 44×44px for AAA (2.5.5) |
| `prefers-reduced-motion` | Major | Animations respect the system preference |
| Inverted / high-contrast mode | Minor | Interface works with OS-level dark/inverted mode (WCAG 1.3.5) |

## Conformance ladder in practice

**Decision at direction phase (Step 1):** choose the conformance target before any code. Default is AA. AAA on contrast (7:1, 4.5:1 large) and target size (44px) when the interface is text-heavy or legally required (public sector, education).

**Measurement:** run `ai-design-audit --checks a11y contrast --widths 320 390 820 1440` after Build. Use `--aa` to relax contrast to AA thresholds.

**Document audit:** PDFs and Office files must be checked separately (outside the browser). Use the document checklists above, or an automated tool like Ally itself, `pdfjs` with tags inspection, or `mammoth.js` for DOCX structure.

## Ally checklist source

This reference is based on the [Ally Accessibility Checklist](https://help.anthology.com/ally-web/en/administrators/ally-accessibility-checklist.html), which uses WCAG 2.2 AA as its baseline and adds usability checks beyond the conformance floor. Severity labels follow Ally's own convention (Severe / Major / Minor).