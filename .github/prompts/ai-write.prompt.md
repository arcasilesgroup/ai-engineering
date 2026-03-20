---
name: ai-write
description: "Use when writing technical content: documentation, changelogs, articles, pitches, sprint reviews, and presentation outlines. Handler-based with audience targeting."
model: opus
effort: high
argument-hint: "docs|changelog|content <type>|--audience developer|manager|executive"
mode: agent
tags: [writing, documentation, changelog, content, communication]
---



# Technical Writing

Router skill for comprehensive technical writing. Dispatches to handler files based on content type. Always: clear structure, audience-appropriate, no fluff.

## When to Use

- Writing or updating documentation (README, API docs, guides).
- Generating changelogs from conventional commits.
- Creating pitch decks, sprint reviews, blog posts, architecture board presentations.
- NOT for code explanations -- use `/ai-explain`.
- NOT for code changes -- use `ai-build agent`.

## Routing

| Sub-command | Handler | Purpose |
|-------------|---------|---------|
| `docs` | `handlers/docs.md` | README, API docs, guides, wiki pages |
| `changelog` | `handlers/changelog.md` | Release notes from conventional commits |
| `content` | `handlers/content.md` | Articles, pitches, presentations, sprint reviews |

Default (no sub-command): `docs`.

## Audience Targeting

| Audience | Tone | Detail Level | Jargon |
|----------|------|-------------|--------|
| `developer` | Technical, precise | Implementation details | Full technical vocabulary |
| `manager` | Results-oriented | Impact and timeline | Minimal, explained when used |
| `executive` | Strategic | Business value and risk | None |

Default: `developer`.

## Quick Reference

```
/ai-write docs                              # documentation (default)
/ai-write changelog                         # release notes from commits
/ai-write content pitch                     # elevator pitch
/ai-write content sprint-review             # sprint review summary
/ai-write content blog                      # blog post
/ai-write content presentation              # presentation outline
/ai-write content architecture-board        # architecture decision for review
/ai-write content solution-intent           # solution intent document
/ai-write docs --audience manager           # manager-targeted docs
```

## Shared Rules

- Write what users can DO, not what you BUILT.
- Active voice. Present tense.
- No "basically", "simply", "just".
- Every section earns its place -- cut anything that does not serve the reader.
- Audience determines vocabulary, not quality.

## Integration

- Composes with `/ai-commit` documentation gate for auto-updates.
- Changelog mode follows Keep a Changelog format.
- Content mode adapts to audience tier.

## References

- `.ai-engineering/manifest.yml` -- governance documentation requirements.
$ARGUMENTS

---

# Handler: changelog

Generate changelogs and release notes from conventional commits.

## Process

1. **Identify scope** -- determine range:
   - Between tags: `git log v1.0.0..v2.0.0 --oneline`.
   - Since last release: `git log $(git describe --tags --abbrev=0)..HEAD --oneline`.
   - Time-based: `git log --since="2 weeks ago" --oneline`.

2. **Collect material** -- for each commit/PR: message, changed files, linked issues.

3. **Classify impact**:
   - User-visible: behavior change, new capability, bug fix.
   - Internal: refactoring, tests, CI (exclude from changelog).
   - Breaking: API change, feature removal (requires migration guide).
   - Security: vulnerability fix (include CVE, impact, affected versions).

4. **Map to categories** (Keep a Changelog):
   - **Added**: new capability users could not do before.
   - **Changed**: existing capability improved or different.
   - **Deprecated**: still works, include removal timeline.
   - **Removed**: previously available, now gone.
   - **Fixed**: was broken, now works.
   - **Security**: vulnerability fix with CVE reference.

5. **Transform language** -- user-facing, not technical:
   ```
   Bad:  "Refactored ReportExporter to support pagination"
   Good: "Reports now load 3x faster when filtering large datasets"
   ```
   Rules: start with "You can now..." / "Fixed an issue where...", present tense, no internal references.

6. **Format CHANGELOG.md** -- entries in `[Unreleased]` section. For releases: rename to `[X.Y.Z] - YYYY-MM-DD`, add comparison links.

7. **Quality check** -- reject: "various bug fixes", "updated dependencies" without impact, internal jargon, missing dates, buried breaking changes.

## Output

- CHANGELOG.md entries in Keep a Changelog format.
- Optional: GitHub Release Notes with highlights, upgrade guide, contributors.
# Handler: content

Technical content creation: pitches, sprint reviews, presentations, blog posts, architecture boards, and solution intent documents.

## Content Types

### pitch
Elevator pitch for a feature, project, or initiative.
1. **Problem** -- 1-2 sentences on the pain point.
2. **Solution** -- what you built and how it solves the problem.
3. **Impact** -- quantified results or expected outcomes.
4. **Ask** -- what you need (approval, resources, feedback).

### sprint-review
Sprint review summary for stakeholders.
1. **Completed** -- features delivered with demo-ready descriptions.
2. **Metrics** -- velocity, burndown, quality indicators.
3. **Blockers** -- what slowed the team and how it was resolved.
4. **Next sprint** -- planned work and risks.

### blog
Technical blog post for developer audience.
1. **Hook** -- open with the problem or surprising finding.
2. **Context** -- why this matters, who benefits.
3. **Solution** -- technical walkthrough with code examples.
4. **Results** -- measured outcomes, benchmarks.
5. **Conclusion** -- key takeaway and call to action.

### presentation
Presentation outline (slide-by-slide structure).
1. **Title slide** -- topic, author, date.
2. **Problem/context** -- why we are here (2-3 slides).
3. **Solution/demo** -- what we built (3-5 slides).
4. **Results/impact** -- what changed (2-3 slides).
5. **Next steps** -- what is needed (1 slide).
6. **Appendix** -- technical detail for Q&A.

### architecture-board
Architecture decision presentation for review board.
1. **Context** -- business driver and technical constraint.
2. **Options evaluated** -- comparison matrix with criteria.
3. **Recommendation** -- selected option with rationale.
4. **Risk assessment** -- what could go wrong and mitigation.
5. **Implementation plan** -- phases, timeline, rollback.

### solution-intent
Solution intent document (SAFe-style).
1. **Vision** -- desired end state.
2. **Current state** -- what exists today.
3. **Solution overview** -- architecture, components, boundaries.
4. **Compliance** -- regulatory and governance requirements.
5. **Economic framework** -- cost, benefit, ROI estimate.
6. **Key decisions** -- made and pending.

## Audience Adaptation

- **Developer**: include code snippets, technical tradeoffs, implementation detail.
- **Manager**: focus on timeline, resource needs, risk, progress metrics.
- **Executive**: focus on business value, strategic alignment, ROI, competitive advantage.

## Output

- Structured content document in markdown.
- Adapted to specified audience tier.
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
