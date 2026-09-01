# README writer — the standard-readme discipline

Loaded when writing or reviewing a README.md. Sources: standard-readme spec
(richardlitt/standard-readme), Google docguide READMEs, AI-oriented README
practice (ben3d.ca "Crafting READMEs for AI").

## The contract

A README is the single entry point for humans and AI agents. It defines the
module; the code is the implementation detail. Write one README for both
audiences: agents parse structure, humans skim prose — structure serves both.

## Section order (standard-readme; optional sections may be omitted)

1. **Title** — matches repo/package name; or a display title with the name in
   italics.
2. **Banner** (optional) — local image, directly after the title, no heading.
3. **Badges** (optional) — newline-delimited, no heading, few and current.
4. **Short description** — no heading, one line, <120 chars, matches the
   package manager `description` field.
5. **Long description** — no heading; a few paragraphs: what it is, why it
   exists, what makes it different.
6. **Table of Contents** — links every section; required >100 lines.
7. **Security** — early if it is a headline concern.
8. **Background** — motivation, provenance, prior art.
9. **Install** — copyable commands; name prerequisites and versions.
10. **Usage** — a runnable quick start, then per-verb/per-API reference;
    CLI projects get a `CLI` subsection; anti-patterns beat warnings.
11. **Extra sections** — core concepts, troubleshooting, FAQ, each its own
    heading, between Usage and API.
12. **API** (optional) — exported surface, signatures, return types.
13. **Maintainers** — the people to ping, not the whole org.
14. **Contributing** — where to ask, what PRs need, links to CONTRIBUTING and
    a code of conduct.
15. **License** — SPDX identifier + owner; always last.

## Writing rules

- **Executable quick start** — a newcomer copies the Usage block and it works;
  an example the reader cannot run is a broken contract.
- **Version alignment** — every referenced command, flag and file must exist in
  the shipped version; stale docs cost agents token-expensive rediscovery.
- **Anti-patterns over platitudes** — show what NOT to do next to what to do.
- **No broken links** — verify every internal link against the tree.
- **Docs are a cache** — keep it short; the repo remains the source of truth.
  A README that restates `--help` is a maintenance liability (see
  documentation-writer.md, pruning).
- English only (canon rule); no machine-specific paths; no token-limit talk.
