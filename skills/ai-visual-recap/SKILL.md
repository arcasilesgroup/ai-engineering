---
name: ai-visual-recap
description: >-
  Build an optional self-contained HTML recap when the user manually invokes
  this skill. The output is a local file on the feature branch.
license: Apache-2.0
---

# ai-visual-recap

When manually invoked by the user, create the optional recap as
`.ai-engineering/recap.html` from the changes on the current feature branch. Use
the repository's template and keep the output self-contained. The orchestrator
never invokes this skill automatically, and a missing recap never blocks review
or merge.

## Procedure

1. **Scope the change.** Read `git diff --stat main...HEAD` and
   `git diff --name-status main...HEAD`, then inspect the relevant changed files
   and test results. Include this feature's follow-up fixes. Exclude unrelated
   baseline changes.
2. **Read the local format.** Start with `templates/recap.html.tpl`, follow
   [the artifact design](../../skills/ai-brainstorm/references/artifact-design.md), and
   use [the wireframe guidance](references/wireframe.md) only when the change
   alters a visible interface.
3. **Write the recap.** Replace each template placeholder with accurate,
   HTML-escaped text. Add matching navigation links and sections inside the
   template's main container. Summarize the outcome, meaningful decisions,
   changed files, verification evidence, and any real compatibility risks.
   Use the template's existing cards, notes, tables, and code panels. Include
   before/after visuals only when they explain a user-visible change.
4. **Protect the contents.** Use repository evidence only. Never include
   credentials, private service output, raw work items, machine-specific paths,
   or unrelated changes. Keep code excerpts short and accurate.
5. **Verify the page.** Confirm no `{{...}}` placeholders remain, every
   navigation target names an existing section, and the existing scroll-spy
   script is unchanged. Run `bun test tests/artifact-layout.spec.ts` and
   `bun test tests/artifact-scroll-spy.spec.ts`.
6. **Write the artifact.** Save the complete page to
   `.ai-engineering/recap.html` on the feature branch. The orchestrator includes
   it in the close commit only if the user requested this skill and the file
   exists; this skill does not commit or merge.

## Lifecycle

Lane: standard, full
Writes: `.ai-engineering/recap.html`
Read by: the human, during app review
Dies: when the feature branch is merged
Next: none
Stop: close
Stop words: close, cierra, done, listo
Stop confirms: the local HTML recap is written and verified
Stop runs: git status --short
