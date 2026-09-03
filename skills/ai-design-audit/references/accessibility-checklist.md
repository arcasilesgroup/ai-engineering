# Accessibility checklist reference

The a11y pass in `ai-design-audit` checks HTML rendered in a browser. This reference covers what it cannot reach: downloadable documents, screen-reader behaviour, orientation lock, and non-text contrast.

## How to interpret the a11y audit output

Every finding carries a severity (high, medium, low). The pass only reports a value that differs from the expected default, so a clean run does not mean the page is accessible — it means no automated check caught a violation.

**Severity in the script output:**

- **high** — a structural blocker. The item makes the page unusable for an assistive-technology user (no label on a form control, no lang attribute, zoom disabled, deprecated elements). Fix first.
- **medium** — a real impairment that a screen-reader user will notice (missing captions, duplicate IDs, missing required ARIA attributes, heading skips). Fix in the same pass.
- **low** — an accessibility quality gap that does not block use on its own (table scope missing, list-integrity edge case). Fix when convenient.

When several high findings land on the same element, one fix often resolves them all. Group the changes, not the severity labels.

## Ally severity taxonomy

Ally (the automated checker used in Blackboard/Anthology learning environments) uses **Severe**, **Major**, and **Minor**. The a11y pass maps to a coarser three-tier system. Here is how to judge each:

| Ally label | a11y equivalent | How to judge |
|---|---|---|
| Severe | high | The page is broken for someone. Screen reader cannot parse it, zoom is disabled, content is entirely image-based (scanned PDF, not tagged). Fix before anything else. |
| Major | high or medium | A clear violation that a real user will hit. Missing labels, invalid ARIA, no heading structure on long pages, untagged documents. Fix in the same sprint. |
| Minor | medium or low | A quality gap that does not block core use. Wrong language tag, missing table scope, a heading level that could be tighter. Fix when the code is in the area. |

When the a11y pass and Ally disagree, trust the a11y pass for HTML (it runs against the live DOM) and trust Ally for the document file (it parses the binary).

## Downloadable document checklist

The a11y pass cannot evaluate PDF, Word, or PPTX files — these do not render in the browser. Use the manual checklists below, or run Ally / `pdfjs` / `mammoth.js` against the files directly.

### PDF

| Check | Severity | What to verify |
|---|---|---|
| File is malformed | Severe | Opens without errors in a reader |
| File is encrypted / password-protected | Severe | No password required to read |
| Scanned image layer (no text layer) | Severe | Must be OCR'd or re-exported as tagged text |
| No tag tree (untagged) | Major | Must have reading order (Structure panel shows tags) |
| No language set | Minor | Language in Properties > Description |
| Images without alt text | Major | Every meaningful image has alt |
| Text contrast below AA | Major | Meets 4.5:1 (normal) / 3:1 (large) |
| No headings on long documents (3+ pages) | Major | Heading structure present |
| Headings skip levels | Minor | H1 → H2, no H1 → H3 |
| Headings do not start at H1 | Major | First heading is H1 |
| Tables without header cells | Major | `<th>` with `scope` in data tables |
| No document title | Minor | Title metadata set |

### Microsoft Word / LibreOffice Writer

| Check | Severity | What to verify |
|---|---|---|
| Document is malformed | Severe | Opens without errors |
| Document is encrypted / password-protected | Severe | No password required |
| No language set | Minor | Language in File > Properties |
| Language incorrect | Minor | Correct `lang` value in properties |
| Images without alt text | Major | Alt text on every meaningful image |
| Text contrast below AA | Major | Meets 4.5:1 / 3:1 |
| No headings (12+ paragraphs) | Major | Document-level heading structure present |
| Headings skip levels | Minor | Sequential levels |
| Headings do not start at H1 | Major | First heading is H1 |
| Headings beyond level 6 | Minor | ≤ 6 levels |
| Tables without header cells | Major | Header cells with `scope` |

### PowerPoint / LibreOffice Impress

| Check | Severity | What to verify |
|---|---|---|
| Presentation is malformed | Severe | Opens without errors |
| Presentation is encrypted / password-protected | Severe | No password required |
| No language set | Minor | Language in Slide Design > Slide Master |
| Language incorrect | Minor | Correct `lang` value |
| Images without alt text | Major | Alt text on every meaningful image |
| Text contrast below AA | Major | Meets 4.5:1 / 3:1 |
| No heading / title | Major | One title per ~7 slides |
| Tables without header cells | Major | Header cells with `scope` |

## Non-text contrast

WCAG 2.5.8 (Target Size) and 1.4.11 (Non-text Contrast) require a 3:1 ratio against adjacent colours for UI components and graphical objects. The `contrast` pass in `ai-design-audit` only measures text against its immediate background. Non-text contrast on icons, dividers, form borders, and focus rings is not measured.

**How to check:** open DevTools, pick the element, inspect `background` and `border` / `outline` colours, compute the ratio with any contrast checker. If a UI element (button outline, tab border, input border) is indistinguishable on a white background without colour, it fails.

## Orientation lock

No code should force portrait or landscape. Content must reflow when the device rotates.

- **Check:** set `screen.orientation.lock()` in the console — if it throws, the app has locked orientation. Also look for `@media (orientation: portrait)` blocks that hide content on one side.
- **Fix:** remove the lock call. Ensure all layouts are fluid so rotation does not produce horizontal overflow or clipped content.

## Screen reader testing

Automated checks cover structure, not experience. A screen reader user tests:

- **Tab order matches visual order.** Press Tab through every interactive element. The focus should follow the left-to-right, top-to-bottom reading order.
- **All content is reachable.** No hidden panels, modals, or overlays that require mouse-only interaction.
- **Error messages are announced.** Submit a form with invalid data — the SR should announce the error immediately, not require the user to hunt.
- **Dynamic content updates.** Open/close a dropdown, expand an accordion — the SR should announce the state change.

**Tools:** VoiceOver (macOS, Cmd+F5), NVDA (Windows, free), VoiceOver iOS (Settings > Accessibility > VoiceOver).

## References

- [Ally Accessibility Checklist](https://help.anthology.com/ally-web/en/administrators/ally-accessibility-checklist.html) — the source taxonomy used here
- [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) — the conformance baseline
- [WCAG 2.2 AAA](https://www.w3.org/TR/WCAG22/#level-aaa) — the higher target for text-heavy interfaces