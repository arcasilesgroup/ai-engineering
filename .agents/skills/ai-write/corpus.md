# Corpus: ai-write

Writes technical documentation for this repository against the framework's single writing
standard (references/documentation-writer.md, spec 039) and verifies every document
against the tree: real files, no environment restatement, checkable completion criteria,
and a `not-covered: <reason>` exit for what cannot be verified.

## Routes here

- "write the README" — a project needs its definitive entry point, written against the standard and verified against the tree.
- "update the wiki" — the wiki page needs the same verification: real files, checkable sections.
- "document this API" — the endpoints exist in the code; each claim traces to the source.
- "write a technical post about X" — the post claims things about the tree; whatever cannot be verified exits `not-covered`.
- "refresh the product docs" — the docs drifted from the tree; this skill re-writes them against what is actually there.

## Refuses

- "update the changelog" — use `/ai-ship`, because the changelog entry is part of landing the work, not a document to write.
- "write the spec for this" — use `/ai-spec`, because a decision record needs its options, its evidence and its authority.
- "note this down" — use `/ai-note`, because a finding stamped with its commit is a note, not a document.
- "file an issue" — use `/ai-report`, because an issue is a fault report with a payload, not prose.
- "restate our config and commands for the reader" — refused: a doc that repeats the environment is a cache, and this skill writes documents, not caches.