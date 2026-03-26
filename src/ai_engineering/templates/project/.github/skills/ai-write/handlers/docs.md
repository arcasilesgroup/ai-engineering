# Handler: docs

Documentation authoring for README, API docs, guides, wiki pages, and CONTRIBUTING files.

## Pre-conditions

1. Read `.ai-engineering/manifest.yml` — `documentation` section.
2. Check `documentation.auto_update` flags to determine what to update.

## Process

1. **Detect doc type** -- classify: tutorial, how-to, explanation, reference, ADR.
2. **Read existing** -- if updating, read current content to preserve structure and links.
3. **Gather context** -- read source code, config, `manifest.yml`, project metadata.
4. **Apply Divio structure**:
   - **Tutorial**: learning-oriented, step-by-step, concrete outcomes.
   - **How-to**: task-oriented, assumes knowledge, goal-focused.
   - **Explanation**: understanding-oriented, context and reasoning.
   - **Reference**: information-oriented, accurate and complete.
5. **Write content** -- audience-appropriate vocabulary, active voice, no fluff.
6. **Validate** -- verify internal links resolve, markdown structure is valid.

## Doc Types

### README
- Project name and one-line description.
- Quick start (3 steps max to "hello world").
- Installation, usage, configuration.
- Contributing, license.

### README Update Mode

Triggered when `manifest.yml` `documentation.auto_update.readme` is `true`.

1. Scan project recursively for ALL README*.md files (README.md, README_es.md, etc.)
   - **Exclude**: `.venv/`, `node_modules/`, `.git/`, `__pycache__/`, `.pytest_cache/`, `build/`, `dist/`
2. For EACH README found:
   a. Read the README in context of its directory (what does this directory contain?)
   b. Read sibling files to understand the module/package purpose
   c. Update the README to reflect current state of that directory
   d. Preserve existing structure and formatting; update content in-place
3. Report which READMEs were updated and which were unchanged

### API Docs
- Endpoint/function signature.
- Parameters with types and constraints.
- Response format with examples.
- Error codes and handling.

### Guides
- Prerequisites clearly stated.
- Numbered steps with expected outcomes.
- Troubleshooting section for common failures.

### ADR (Architecture Decision Record)
- Status, context, decision, consequences.
- Alternatives considered with tradeoffs.
- Date and participants.

## Output

- Markdown file(s) ready to commit.
- Validation report: link check, structure check.
