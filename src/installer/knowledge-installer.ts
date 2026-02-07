import { writeFile, ensureDir, resolvePath } from '../utils/filesystem.js';
import { logger } from '../utils/logger.js';

export function installKnowledge(projectRoot: string): void {
  const knowledgeDir = resolvePath(projectRoot, '.ai-engineering/knowledge');
  const decisionsDir = resolvePath(knowledgeDir, 'decisions');

  ensureDir(knowledgeDir);
  ensureDir(decisionsDir);

  writeFile(
    resolvePath(knowledgeDir, 'learnings.md'),
    `# Project Learnings

> This file is automatically created by ai-engineering and is YOURS to maintain.
> It is never modified by framework updates.

Document lessons learned during development. The AI assistant reads this
at the start of each session to avoid repeating past mistakes.

## Format

\`\`\`markdown
### [Date] — Short description
- What happened
- Why it happened
- What we learned
- What to do differently
\`\`\`

## Learnings

<!-- Add entries below -->
`,
  );

  writeFile(
    resolvePath(knowledgeDir, 'patterns.md'),
    `# Project Patterns

> This file is automatically created by ai-engineering and is YOURS to maintain.
> It is never modified by framework updates.

Document project-specific patterns and conventions that go beyond the
general stack standards. The AI assistant follows these patterns when
writing new code.

## Format

\`\`\`markdown
### Pattern: Short name
- **When**: When to use this pattern
- **How**: How to implement it
- **Example**: Reference file or code snippet
- **Why**: Why this pattern exists in this project
\`\`\`

## Patterns

<!-- Add entries below -->
`,
  );

  writeFile(
    resolvePath(knowledgeDir, 'anti-patterns.md'),
    `# Project Anti-Patterns

> This file is automatically created by ai-engineering and is YOURS to maintain.
> It is never modified by framework updates.

Document things to avoid in this specific project. The AI assistant
reads this to avoid introducing known bad patterns.

## Format

\`\`\`markdown
### Anti-Pattern: Short name
- **What**: What the bad pattern looks like
- **Why bad**: Why it causes problems in this project
- **Instead**: What to do instead
- **Example**: Reference to past incident or code
\`\`\`

## Anti-Patterns

<!-- Add entries below -->
`,
  );

  writeFile(
    resolvePath(decisionsDir, 'README.md'),
    `# Architecture Decision Records (ADRs)

> This directory is automatically created by ai-engineering.
> It is never modified by framework updates.

Store Architecture Decision Records here. ADRs document significant
technical decisions made during the project's lifetime.

## Template

Create new ADRs as \`NNNN-short-title.md\`:

\`\`\`markdown
# ADR-NNNN: Title

## Status
Accepted | Deprecated | Superseded by ADR-XXXX

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or more difficult to do because of this change?
\`\`\`
`,
  );

  logger.success('Initialized knowledge directory');
}
