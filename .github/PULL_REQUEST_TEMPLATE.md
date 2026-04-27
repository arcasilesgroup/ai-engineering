<!--
Thank you for contributing to ai-engineering. Please fill in the template.
PRs that don't follow it may be closed or asked to update.
-->

## Summary

<!-- 1-3 bullets explaining the WHY. Use prose, not just file names. -->

-

## Linked spec / issue

<!-- e.g. spec-NNN-<slug>, fixes #123, closes #456. Required for non-trivial work. -->

-

## Type

- [ ] feat — new feature
- [ ] fix — bug fix
- [ ] refactor — no behavior change
- [ ] perf — performance improvement
- [ ] docs — documentation only
- [ ] test — tests only
- [ ] chore — tooling / repo admin
- [ ] ci — CI changes

## Discipline checklist

- [ ] TDD: failing test exists / was added in this PR
- [ ] Coverage: domain ≥ 80%, application ≥ 70%
- [ ] Hexagonal: no domain code imports `node:fs`, framework I/O
- [ ] No `--no-verify`, no suppression comments
- [ ] Conventional commit message
- [ ] CONSTITUTION articles respected (or amendment ADR opened)

## Test plan

<!--
How did you verify this works? Commands, screenshots if UI, or links
to CI runs. Reviewers will run these.
-->

- [ ] `bun test`
- [ ] `bun run lint`
- [ ] `bun run typecheck`
- [ ] `uv run pytest python/` (if Python touched)

## Screenshots / output (optional)

<!-- Drag screenshots here or paste CLI output for UX changes. -->

🤖 Generated with [Claude Code](https://claude.com/claude-code)
