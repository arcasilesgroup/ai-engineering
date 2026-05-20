# Design Intent — spec-144

## Design

**Routing:** auto-routed by `/ai-plan` because the spec mentions design-system, UX, typography, layout, and interface work.

**Conceptual direction:** terminal-native editorial governance. The READMEs read like a precise command surface, not a SaaS brochure: code-comment headers, shell prompts, mid-dot stats, bracket-tag statuses, short paragraphs, and no decorative emoji.

**Audience:** first-time operators, framework maintainers, security/compliance reviewers, and implementation agents.

**Voice system:**

- Use `{ai} engineering` in body prose; reserve `ai-engineering` for package, repository, URLs, and CLI-adjacent technical names.
- Prefer imperative second-person copy: install, run, verify, ship.
- Use `bash` fences for shell commands and `yaml` fences for manifest/config snippets.
- Compress feature counts as mid-dot stat lines, e.g. `53 skills · 9 agents · 6 surfaces · 1 governed flow`.
- Use `[PASS]`, `[WARN]`, `[FAIL]`, and `[PENDING]` as status grammar instead of emoji.
- Keep root README under 120 lines and use line length that remains readable in GitHub's markdown viewport.

**Information architecture:**

1. Root `README.md`: hero, install, canonical chain, why governance matters, surfaces, verification links, attribution.
2. `.ai-engineering/README.md`: inline Quick Start, persistence doctrine, canonical chain, runbook/docs map, sync/ownership rules.
3. Template governance README: byte-identical mirror of `.ai-engineering/README.md`.
4. Team README: keep minimal placeholder unless a concrete defect is discovered.

**Accessibility/readability gates:**

- No image-only onboarding path; all instructions are text and copyable commands.
- No emoji or color-only meaning; bracket tags carry text semantics.
- No external second-tab dependency for first success.
- Preserve required links: `AGENTS.md`, `CONSTITUTION.md`, `CHANGELOG.md`, `CONTRIBUTING.md`.

**Pre-delivery checklist result:** PASS for planning intent. Visual asset generation, motion, touch targets, and responsive UI checks are not applicable because the deliverable is Markdown documentation, not a browser interface.
