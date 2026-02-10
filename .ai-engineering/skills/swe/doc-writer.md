# Doc Writer

## Purpose

Transform codebase knowledge into polished, user-facing open-source documentation that end users actually understand and appreciate. Reads code, configuration, `.ai-engineering` context (specs, learnings, product-contract), and project metadata to produce README.md, CONTRIBUTING.md, docs/ site content, Wiki pages, and CODE_OF_CONDUCT.md. Writes what users can DO, not what you BUILT — translating technical implementation into benefits, capabilities, and clear instructions.

## Trigger

- Command: agent invokes doc-writer skill or user requests project documentation.
- Context: creating or updating README.md, writing getting-started guides, producing contribution guidelines, generating docs/ site content, building Wiki articles, onboarding new users, preparing a project for open-source release.

## Procedure

### Phase 1: Codebase Discovery

Autonomously scan the project to build a complete mental model before writing a single line of documentation.

1. **Read project identity** — understand what the project is and who it serves.
   - Read `context/product/product-contract.md` — goals, KPIs, release status.
   - Read `context/product/framework-contract.md` — identity, personas, roadmap.
   - Read `pyproject.toml` — project name, version, description, entry points, dependencies.
   - Read `__version__.py` or equivalent — current version string.

2. **Read project context** — understand current scope and institutional knowledge.
   - Read `context/specs/_active.md` and the active spec's `spec.md` — current scope, decisions, what's in/out.
   - Read `context/learnings.md` — retained institutional knowledge, past decisions.
   - Scan `standards/framework/core.md` — governance model (for understanding, not for user docs).

3. **Scan source code** — identify user-facing features and capabilities.
   - Read CLI entry points (`cli.py`, `cli_factory.py`, or equivalent) — available commands and options.
   - Scan feature modules in `src/` — public API surface, key classes, exported functions.
   - Read configuration files — what users can configure and how.
   - Identify install method — pip, uv, package manager, from source.

4. **Produce Project Knowledge Map** — structured internal artifact (not published):

   | Dimension         | What to capture                                      |
   |-------------------|------------------------------------------------------|
   | **Identity**      | Name, tagline, one-sentence value proposition        |
   | **Audience**      | Who uses this and why                                 |
   | **Install**       | How to install (pip, uv, from source)                 |
   | **Quick start**   | Minimum steps to first useful result                  |
   | **Features**      | User-facing capabilities (not internal modules)       |
   | **Configuration** | What can be customized and how                        |
   | **Architecture**  | Simplified view — only what users need to understand  |
   | **Ecosystem**     | Related tools, integrations, plugins                  |

### Phase 2: Documentation Standards and Structuring

Establish writing standards and document architecture before drafting.

5. **Apply voice and tone rules** — every document follows these conventions:
   - Address the reader as "you." Use active voice and present tense.
   - Professional, friendly, and direct tone — not corporate, not casual.
   - Use simple vocabulary. Avoid jargon, slang, and marketing hype.
   - Write for a global audience — standard US English, no idioms or cultural references.
   - Be clear about requirements ("must") vs. recommendations ("we recommend"). Avoid "should."
   - Use contractions (don't, it's). Avoid "please" and anthropomorphism.
   - Start instructions with imperative verbs: "Run...", "Create...", "Add...".

6. **Apply formatting rules** — consistent structure across all artifacts:
   - ATX-style headers (`#`, `##`, `###`). Sentence case for headings.
   - Every heading followed by at least one introductory paragraph before lists or sub-headings.
   - Numbered lists for sequential steps. Bullet lists for non-sequential items.
   - Code blocks with language tags (` ```bash `, ` ```python `, ` ```yaml `).
   - Bold for UI elements and emphasis. Backticks for filenames, commands, API elements.
   - Descriptive link text — never "click here." Links must make sense out of context.
   - Meaningful names in examples — never "foo", "bar", or "test123."
   - Alt text for all images. Lowercase hyphenated filenames for media.

7. **Select and outline artifacts** — determine which documents to produce:

   | Artifact              | When to produce                                           |
   |-----------------------|-----------------------------------------------------------|
   | **README.md**         | Always — the project's front door                         |
   | **CONTRIBUTING.md**   | When the project accepts external contributions           |
   | **docs/ site content**| When the project has enough features to warrant guides    |
   | **Wiki pages**        | When conceptual/architectural guides complement docs/     |
   | **CODE_OF_CONDUCT.md**| When the project is published as open-source              |

   For each selected artifact, generate a **section outline** with placeholder headings. Present the outlines to the user for validation before writing.

### Phase 3: Co-Authoring and Drafting

Iteratively build each document section by section. Never dump a full draft — collaborate through structured refinement.

8. **For each artifact, work section by section**:

   1. **Clarify** — ask 3-5 targeted questions about what to include in this section.
   2. **Brainstorm** — propose 5-10 content options for the section, drawing from the Project Knowledge Map.
   3. **Curate** — user indicates what to keep, remove, or combine (shorthand is fine: "keep 1,3,5 — remove 2,4").
   4. **Draft** — write the section based on curated selections. Create or update the file directly.
   5. **Iterate** — user reviews and provides feedback. Apply surgical edits — never reprint entire documents for small changes.

   Repeat steps 1-5 until the user approves the section, then move to the next.

9. **Track style preferences** — as the user provides feedback across sections, learn and apply their preferences to subsequent sections. Common patterns to track:
   - Preferred level of technical detail.
   - Tone adjustments (more formal, more casual, more concise).
   - Structural preferences (more examples, fewer tables, shorter paragraphs).

10. **Apply artifact-specific structure** — each document type has its own anatomy:

#### README.md

```markdown
# Project Name

Brief description — what it does, who it's for, why it matters.

## Features

Key capabilities as a bullet list — user benefits, not implementation details.

## Quick start

### Prerequisites

What users need before installing.

### Installation

Exact install commands (pip, uv, from source).

### First use

Minimum steps to a first useful result.

## Usage

Expanded usage guide — common workflows, CLI commands, configuration.

## Configuration

Available options, environment variables, config files.

## Architecture

Simplified view — only what helps users understand the project.
Not internal module structure — user-facing concepts.

## Documentation

Links to docs/, Wiki, API reference.

## Contributing

Brief mention + link to CONTRIBUTING.md.

## License

License type and link.
```

#### CONTRIBUTING.md

```markdown
# Contributing to Project Name

Thank your contributors. Set the tone for collaboration.

## Development setup

Exact steps: clone, install dependencies, verify setup works.

## Code style

Linting, formatting, type checking tools and commands.

## Testing

How to run tests. Coverage expectations.

## Pull request process

Branch naming, commit conventions, PR template, review process.

## Reporting issues

How to report bugs. What to include.

## Code of conduct

Link to CODE_OF_CONDUCT.md.
```

#### docs/ site content

- **Getting started guide**: prerequisites, installation, first use, next steps.
- **Feature guides**: one per major feature — what it does, how to use it, examples.
- **Configuration reference**: all options, defaults, environment variables.
- **FAQ / Troubleshooting**: common questions and known issues.

#### Wiki pages

- **Conceptual guides**: architecture for users, design philosophy, integration patterns.
- **How-to articles**: task-oriented guides for specific use cases.
- **Glossary**: project-specific terminology.

#### CODE_OF_CONDUCT.md

- Adopt [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) as default.
- Customize: project name, contact info, enforcement details.
- Keep it standard — deviations from Contributor Covenant must be justified.

### Phase 4: Reader Testing

Validate documentation quality by testing with a fresh perspective.

11. **Predict user questions** — generate 5-10 questions a new user would ask:
    - "How do I install this?"
    - "What does this project do?"
    - "How do I configure X?"
    - "What are the prerequisites?"
    - "How do I report a bug?"

12. **Test with sub-agent** — invoke a fresh agent (no conversation history) with only the document content and one question at a time.
    - Does the agent find the answer from the docs alone?
    - Is anything ambiguous or assumed?
    - Are there comprehension gaps?

13. **Validate technical accuracy**:
    - Are install instructions actually runnable?
    - Are code examples syntactically valid?
    - Do all links resolve?
    - Does the documented version match `__version__.py`?
    - Are CLI commands and flags accurate against the actual implementation?

14. **Fix gaps** — for any failing tests, loop back to Phase 3 step 5 for the affected section. Don't rewrite from scratch — apply surgical fixes.

### Phase 5: Ship and Integrate

Finalize and position documentation in the project.

15. **Final coherence review** — read all artifacts end-to-end and check:
    - Consistent terminology across all documents (same name for same concept everywhere).
    - No contradictions between README, docs/, and CONTRIBUTING.
    - Cross-references work (README links to CONTRIBUTING, docs links to README, etc.).
    - No orphaned sections or dead-end flows.

16. **Version alignment** — ensure documentation reflects the current state:
    - Version string matches `__version__.py` or `pyproject.toml`.
    - Features documented match features that actually exist in the current release.
    - Roadmap or "coming soon" items are clearly marked as such.

17. **Add navigation** — connect all documentation artifacts:
    - README → docs/, CONTRIBUTING.md, CODE_OF_CONDUCT.md.
    - docs/ pages → back to README, between guides.
    - CONTRIBUTING.md → CODE_OF_CONDUCT.md.

18. **Recommend next steps** — suggest improvements beyond the current scope:
    - Add documentation CI (link checking, markdown linting).
    - Set up a docs site (Nextra, MkDocs, Docusaurus) if `docs/` content warrants it.
    - Add documentation updates to the PR template checklist.
    - Schedule periodic documentation review (quarterly).

## Output Contract

- One or more documentation files from the supported set: README.md, CONTRIBUTING.md, docs/*, Wiki pages, CODE_OF_CONDUCT.md.
- Each file follows the voice, tone, and formatting standards from Phase 2.
- Every claim is traceable to code, configuration, or `context/` content — no hallucinated features.
- Reader Testing passes: a fresh agent can answer user questions from the docs alone.
- Install instructions are verified or explicitly marked as untested.
- All cross-references and links resolve.

## Governance Notes

- Never expose internal governance details (`.ai-engineering/` internals, state files, audit logs, decision store) in user-facing documentation — describe user-facing behavior only.
- Never fabricate features, commands, or configuration options — all documented capabilities must be verifiable in source code.
- Never overwrite team-managed or project-managed content without user confirmation.
- Respect the framework-contract's identity: use the correct project name, positioning, and value proposition from `context/product/product-contract.md`.
- Security-sensitive information (API keys, secrets handling, credentials) must reference the security review skill before documenting.
- Install and usage instructions must be tested against the actual codebase or explicitly marked as untested.
- Breaking changes and deprecations must be prominent, never buried — mirror the changelog-documentation skill's conventions.
- Code examples in documentation must be syntactically valid and idiomatic.

## References

- `context/product/product-contract.md` — source of truth for project identity and positioning.
- `context/product/framework-contract.md` — roadmap, personas, value proposition.
- `context/learnings.md` — institutional knowledge that may inform documentation content.
- `standards/framework/core.md` — governance model (for understanding internal structure, not for user docs).
- `skills/swe/changelog-documentation.md` — user-facing language conventions and anti-patterns.
- `skills/swe/code-review.md` — quality patterns for code examples in documentation.
- `skills/swe/prompt-engineer.md` — Chain of Density for content compression and summaries.
- `skills/swe/security-review.md` — security assessment before documenting sensitive features.
- `agents/codebase-mapper.md` — complementary agent for deep codebase understanding.
