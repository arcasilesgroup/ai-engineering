# Plan: writer model recorded — 028 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 028 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. `ai-eng spec show 028 --task <n>` refuses any task whose digests
have moved.

## The order, and why

The decision first, then the routing, then the instrument that measures the routing. The ADR
is created with the verb, which validates the record as it writes it; the corpus refusal is
added only after the decision exists, so a reader of the corpus can find the record it refuses
into. The baseline move happens in the same commit as the corpus row, because an evaluation
whose number moves without its baseline moving is exactly the silent drift `tests/skill_eval.py`
exists to refuse. The final task proves the routing instrument is green, which is the part of
this spec's goal that is reachable today — the ADR promotion is blocked by an inherited red and
is recorded as a blocked task with the page a person can act on.

## The one blocked task, and why the plan still completes honestly

**Task 1 — create ADR 0028 — cannot run green today.** `ai-eng decide` first validates the whole
MADR graph with `madr.validate`; on this tree that returns `INCOMPLETE [MADR_SCHEMA_INVALID]`
from ADR 0025 of spec 026 (forbidden frontmatter fields, present in the worktree and baked into
026's history `bde39e75`→`8f25f903`), so the verb refuses and writes nothing. This is the
inherited red documented in `.ai/reports/014`. Spec 028 does not authorize rewriting that
history or editing that accepted record, so the plan records the blocker in
`specs/028-writer-model-recorded/blocked.md` (the page a person can act on) and completes every
other task. The ADR promotion is the single step the person will re-run after an approved block
repairs ADR 0025. Until then, this goal claims no green gate and adds no new MADR failure.

## What this plan is not doing, and why

- **No change to `.ai/intent.md`, `CONSTITUTION.md`, `specs/013`, or the one-writer rule.**
  The decision being recorded *is* that those stay. Touching them would be the change this
  plan exists not to make.
- **No acceptance of ADR 0028.** `ai-eng decide "<title>" --spec 028` writes `status: proposed`;
  a named person accepts. This plan stops at the record.
- **No repair of ADR 0025 / no history rewrite of spec 026.** That is another block's approved
  work; this plan only records that the promotion is gated on it.
- **No CI/CD and no observability box ticked.** Spec 028 adds no service, no endpoint, no URL.
  `/ai-plan` requires deployables; inventing the boxes here would be ticked against nothing.

## Tasks

1. **Record the writer model as a proposed Structured MADR 0028 (BLOCKED by inherited red)** —
   **file** `docs/adr/0028-*.md` (created by the CLI verb), plus the blocked page
   `specs/028-writer-model-recorded/blocked.md` that records why it cannot run green today.
   **check**: `ai-eng decide "The writer model of ai-goal is one writer implementing an approved plan; the four-term formula is the gated future P3 target, not today" --spec 028`
   **rollback**: `git revert <commit>`.
   **done when**: `ai-eng decide --list` shows `0028` with `status: proposed`. **Status now:
   BLOCKED** — the verb refuses with `INCOMPLETE [MADR_SCHEMA_INVALID]` while ADR 0025 of spec
   026 is un-repaired; `blocked.md` names the approved repair that unblocks it and the exact
   command to re-run.

2. **Pin the ADR record's status as `proposed` (no acceptance by this plan)** —
   **file** none (verification).
   **check**: `uv run python -c "from pathlib import Path; import glob; f=glob.glob('docs/adr/0028-*.md')[0]; assert 'status: \"proposed\"' in Path(f).read_text().split('---')[1]"`
   **rollback**: `git revert <commit>`.
   **done when**: (after the unblock re-runs task 1) the command exits 0 and no
   `authority_role`/`approval_ref`/`approved_at` field exists in the frontmatter.

3. **Add the labelled refusal to the ai-goal corpus** —
   **file** `.agents/skills/ai-goal/corpus.md` (add one row under `## Refuses`).
      **check**: `uv run python -c "from pathlib import Path; assert 'record the writer model as a decision' in Path('.agents/skills/ai-goal/corpus.md').read_text()"`
   **rollback**: `git revert <commit>`.
   **done when**: the corpus carries a refusal quoting the case "record the writer model as a
   decision" and naming `/ai-spec` as the destination; the row does not collide with any other
   skill's claim or refusal (verified by task 5).

4. **Move the skill-routing baseline in the same commit as the corpus row** —
   **file** `policy/pilot-register.toml` (row `[baseline] skill-routing`: `measured = 350`).
      **check**: `uv run python -c "from pathlib import Path; assert 'measured = 350' in Path('policy/pilot-register.toml').read_text()"`
   **rollback**: `git revert <commit>`.
   **done when**: the baseline row reads `measured = 350`, `margin = 0`, and the reason for the
   move is written in the commit message.

5. **Prove the routing instrument is green with the new row** —
   **file** none (verification).
   **check**: `uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: the run exits 0 and prints `RAN skilleval=350` and `baseline 350, delta +0`.

6. **Prove the change introduces no new MADR failure** —
   **file** none (verification).
   **check**: `uv run --with rich --with questionary --with "pytest>=8,<9" python -m pytest tests/test_madr.py -q`
   **rollback**: `git revert <commit>`.
   **done when**: the run reports exactly the same four pre-existing failures (the ADR 0025
   inherited red), and no fifth failure. The tree's `madr.validate` stays `MADR_SCHEMA_INVALID`
   for the inherited reason, and this change does not worsen it.

7. **Prove the spec, plan and blocked page are reviewable at exact digests** —
   **file** none (verification).
   **check**: `uv run python -c "from pathlib import Path; s=Path('specs/028-writer-model-recorded/spec.md').read_text(); assert 'D-028-01' in s and 'D-028-02' in s"`
   **rollback**: `git revert <commit>`.
   **done when**: the two decisions exist in the spec; `git status --short` shows only this
   block's files; and `git diff --stat HEAD -- .ai/intent.md specs/013` is empty.
   **rollback**: `git revert <commit>`.
   **done when**: the two decisions exist in the spec; `git status --short` shows only this
   block's files; and `git diff --stat HEAD -- .ai/intent.md specs/013` is empty.