# CONTRIBUTING & community files writer — the OSS front-door discipline

Loaded when writing or reviewing CONTRIBUTING.md, CODE_OF_CONDUCT.md or a
changeset/release workflow README. Sources: standard OSS practice
(contributor-facing docs), changesets' documented flow.

## CONTRIBUTING.md — the contract

A first-time contributor reaches a green local run and a merged PR by reading
only this file plus the README. Everything deducible from CI configs or the
repo's own AGENTS.md stays there; this file is the bridge for outsiders.

## CONTRIBUTING.md — section order

1. **Ground rules** — the hard lines: no hook bypass, no linter silencing, no
   secrets; the changeset requirement for user-visible changes.
2. **Setup** — clone → install → build → test → lint → typecheck as copyable
   commands; name the generated files that break without their generator.
3. **How to work** — test expectations, import hygiene, the architecture
   boundary, where the product spec lives and how §-references bind behavior.
4. **Commit and PR conventions** — commit format, PR title format, CI parity
   ("your commit must pass everything it will face in CI").
5. **Changesets and releases** — how to add a changeset, bump semantics, what
   merge to main does vs what a tag push does.
6. **Reporting** — bugs to issues (with diagnostics), vulnerabilities to
   SECURITY.md, never public.

## CODE_OF_CONDUCT.md — the contract

Short beats comprehensive: a CoC that is never read protects no one.

1. **The standard** — respectful, constructive, on-topic; the positive
   behaviors first, the prohibited second.
2. **Scope** — repo spaces, official channels, representation in public.
3. **Enforcement** — a real contact address, a review window, escalating
   consequences, maintainers included.
4. **Attribution** — Contributor Covenant lineage, named.

## Writing rules

- **Numbers over adverbs** — "reviewed within 72 hours", not "promptly".
- **Every rule names its enforcement point** — a hook, a CI job, an address.
- **No machine-specific paths, English only**, and no tool invocation the
  reader cannot reproduce on a fresh clone.
