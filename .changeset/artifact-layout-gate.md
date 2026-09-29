---
"ai-engineering": patch
---

Fix artifact HTML alignment drift at the source: the artifact design system now
carries one CSS block instead of two drifted copies, the skills say to copy the
whole block verbatim (copying only the tokens left each writer inventing layout),
and a new layout gate (tests/artifact-layout.spec.ts) rejects centered or 68ch-capped
body text, missing `.container` wrappers, and unaligned notes — the defect that
shipped research 007-014 and the audit page. The gate also caught two template
defects: `--radius-lg` was used 12× but never declared (border-radius computed
to 0px — square corners — in every verbatim copier) and the shipped carriers
were missing 18 canonical rules (`.sr`, `.pipe`, `.tiers`, `nav::after`).
Both templates now carry the canonical block whole. Research gains the same
guarantee it never had: `templates/research.html.tpl` (carrier nº3, gated by
the layout and scroll-spy tests) and ai-research now starts from it instead of
hand-writing a `<style>` block per report.
