# Brand Voice

This is the prose authority for spec-144 README and onboarding copy. The visual sources remain `docs/design.pen` and `docs/untitled.pen`; this Markdown file is the small, reviewable Tier 4 reference that writers and agents should use for text-only documentation.

## Evidence

- `.ai-engineering/specs/archive/spec-144-readme-rewrite-and-branch-cleanup-rename/design-intent.md` defines the approved direction: terminal-native editorial governance.
- `docs/design.pen:40` and `docs/design.pen:3291` are the captured design-source evidence for the `{ai} engineering` wordmark.
- `docs/design.pen:3862-3911` is the captured evidence for `[PASS]`, `[WARN]`, and `[FAIL]` status grammar.
- `docs/untitled.pen:522` is the captured evidence for shell-prompt CTAs.
- `docs/untitled.pen:1517` is the captured evidence for code-comment headers.
- `docs/untitled.pen:1944` is the captured evidence for the mid-dot stat line pattern.

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
- Do not edit `.pen` files when updating prose.
