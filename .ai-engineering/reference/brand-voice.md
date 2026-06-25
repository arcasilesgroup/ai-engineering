# Brand Voice

This is the prose authority for README and onboarding copy. The visual sources are the committed, reviewable brand assets (the opaque `.pen` design files were retired in spec-177); this Markdown file is the small Tier 4 reference that writers and agents should use for text-only documentation.

## Evidence

- `.ai-engineering/specs/archive/spec-144-readme-rewrite-and-branch-cleanup-rename/design-intent.md` defines the approved direction: terminal-native editorial governance.
- `.github/assets/banner-dark.svg` is the canonical source for the `{ai} engineering` wordmark and the navy/teal palette.
- `docs/architecture/brand-tokens.md` codifies the palette, JetBrains-Mono type, `[PASS]`/`[WARN]`/`[FAIL]` status grammar, and the mid-dot stat line.
- `docs/architecture/diagrams/build_diagrams.py` is the source for the README diagram system (shell-prompt CTAs, code-comment headers, branded figures).

## Naming

Use `{ai} engineering` in body prose when describing the framework as a product or operating model. Use `ai-engineering` only for package names, repository names, URLs, CLI-adjacent technical identifiers, and code examples.

Preferred:

```text
{ai} engineering turns AI-assisted delivery into a governed local workflow.
```

Technical identifier:

```bash
pipx install ai-engineering
```

## Voice Rules

- Lead with the next command, then explain why it matters.
- Prefer imperative second-person copy: install, run, verify, ship.
- Keep paragraphs short enough to scan in a terminal or GitHub markdown viewport.
- Use code-comment headers when a section benefits from a compact label, for example `// Governed flow`.
- Use a mid-dot stat line for compact inventories, for example `53 skills · 9 agents · 6 surfaces · 1 governed flow`.
- Use bracket status tags for semantic state: `[PASS]`, `[WARN]`, `[FAIL]`, and `[PENDING]`.
- Use no emoji. Status and emphasis must be textual, not decorative or color-only.

## Code Fences

Use bash fences for shell commands:

```bash
ai-eng install .
ai-eng doctor
```

Use yaml fences for manifest or configuration snippets:

```yaml
providers:
  stacks: [python]
```

Avoid unlabelled fences for command examples. If the block is plain output, use `text`.

## README Application

Root README copy should be concise: hero, install, canonical chain, current surfaces, verification links, attribution, and contributor links. Governance README copy should keep the first-success path inline: `ai-eng install`, `/ai-start`, and `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`.

## Prohibitions

- Do not add machine-specific paths, names, or conversational references.
- Do not make image-only onboarding paths.
- Do not use decorative symbols where text carries the meaning.
- Do not hand-edit rendered brand assets (SVGs, diagram PNGs); change the source (`build_diagrams.py`, `brand-tokens.md`, the banner SVGs) and re-render in CI.
