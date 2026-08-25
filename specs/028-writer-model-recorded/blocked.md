# Blocked — ADR 0028 promotion, gated by the inherited MADR red of spec 026

**What was supposed to run:** task 1 of the 028 plan —
`ai-eng decide "The writer model of ai-goal is one writer implementing an approved plan;
the four-term formula is the gated future P3 target, not today" --spec 028` — creating
`docs/adr/0028-<slug>.md` with `status: "proposed"`.

**What actually happens:** the verb first validates the whole MADR graph with
`madr.validate`; on this tree that returns `INCOMPLETE [MADR_SCHEMA_INVALID]` — "frontmatter
does not match MADR v1" — so `ai-eng decide` refuses with `INCOMPLETE` and writes nothing.

**Why the graph is red (measured, not assumed):**
- The current worktree fails schema: `docs/adr/0025-the-maps-real-broken-references-are-accepted-as-a-dated-record.md`
  carries frontmatter fields the schema forbids (`accepted`, `expires`, `renewals`,
  `follow_up`) and lacks the required `supersedes`.
- The same broken record is baked into spec 026's commits `bde39e75`, `348a353b`,
  `8f25f903`, so the history reproduction (`madr._transitions`) fails even if the worktree
  file were repaired — a new commit cannot erase it.
- The four red tests are exactly the pre-existing
  `tests/test_madr.py::test_intent_supersession_madr_is_complete`,
  `::test_mission_madr_has_options_risks_and_owner`,
  `::test_cli_madr_has_hard_rename_and_transition_evidence`,
  `::test_madr_final_repro_discovery_is_conservative`, all asserting repository-wide
  `madr.validate(...) == PASS`. Documented as the inherited red in `.ai/reports/014`.

**What was tried, honestly:**
- `ai-eng decide "<title>" --spec 028` → refused (`MADR_SCHEMA_INVALID`), nothing written.
- Per-file schema probing of `docs/adr/` → 0025 is the visibly offending record; the graph
  failure also reproduces from history.
- Repairing only the worktree file is not a fix: the history reproduction still fails, and
  editing an accepted record of spec 026 is another block's approved work. Rewriting 026's
  history touches a branch of another block and requires its own approval.

**The honest fix costs (owner: you):**
1. Approved rewrite of spec 026's history so ADR 0025 conforms in `bde39e75` →
   `348a353b` → `8f25f903` (interactive rebase, ~minutes), or
2. a separate approved block that migrates 0025 to conforming frontmatter and re-bases,
   or
3. leave the red as the known, dated acceptance the register records, and re-run this
   ADR promotion after whichever repair lands.

**Then, unblocked:** re-run task 1's command; `ai-eng decide --list` shows `0028` with
`status: proposed`; then a named person (the repository owner role in `.ai/intent.md`)
accepts it with `ai-eng decide --accept 0028`.

**What is NOT blocked by this page:** everything else in the 028 plan is done and green —
the governed record (spec + plan + challenge + council), the `ai-goal` corpus refusal, the
skill-routing baseline at 350, and `tests/skill_eval.py` green at 350. This page exists so
the one blocked step is visible, named, and never silent.