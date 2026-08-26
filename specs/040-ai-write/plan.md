# Plan: ai-write skill — 040 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their digests in their own record. One repository
writer, on a branch carrying the whole 040 change. Each task is one atomic commit; rollback
for every task is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the gate in the same
chain as the commit itself. `ai-eng spec show 040 --task <n>` refuses any task whose
digests have moved.

## The order, and why

Proof objects first: the fixture (`tests/test_040_ai_write.py`) lands red before the
skill. Then the skill + corpus (B-040-1/2) turn it green, then the capability entry, then
the reverse routes + baseline move, then the count move (README/AGENTS "eighteen"), then
the map acceptances for this block's own references, then the gate. The spec's example
commands are the acceptance tests; each `--tick` seals its box.

## What this plan is not doing, and why

- **No port of the claude-agents technical-writer.** It stays an insumo (D-040-01).
- **No revival of the absorbed `ai-docs` name.** The surface is `ai-write`; spec 010 `:414`
  keeps `ai-docs` as absorbed.
- **No cleanup of the 208 pre-existing map reals.** They are named pre-existing and
  verified not to grow; only this block's own references are accepted, with a dated record.
- **No acceptance of ADR 0025** — the inherited `madr.validate` red stays; the final gate
  asserts no new MADR failure.
- **No CI/CD box ticked.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

`ai-write` verifies every document against the tree and exits `not-covered: <reason>` for
what it cannot verify; the three states and the vocabulary are the fixture's, never
invented at write time. The skill writes only into the homes the user names. The routing
refusals keep ai-write apart from the four existing surfaces; the reverse routes make the
harness see distinct cases, never a fork. The capability entry uses all mode fields. The
count move touches exactly the two prose pins. The map accepts exactly this block's
references.

## Tasks

1. [x] <!--t:c3c554ace359--> **Red fixture: verified / no-cache / not-covered / routing / count** —
   **file** `tests/test_040_ai_write.py` (new): `verified` (a doc naming real files,
   checkable sections, no environment restatement passes), `no_cache` (a doc repeating the
   environment is refused), `not_covered` (an unverifiable claim exits `not-covered` with a
   reason), `routing` (a changelog routes to `/ai-ship`, a wiki is taken here), `count`
   (README.md and AGENTS.md say "eighteen").
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_040_ai_write.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture runs and fails for the right reason (no skill, no count move).

2. [x] <!--t:7c27c2cbfb80--> **The ai-write skill + corpus (B-040-1/2)** —
   **file** `.agents/skills/ai-write/SKILL.md` (new, model-invoked, under the audit
   contract: frontmatter + `## What it produces` + `## Steps` + `## What this is not` +
   `## Done when`, pointing at `.agents/skills/ai-report/references/documentation-writer.md` (039) as its single
   standard, no-cache and completion-criteria rules, verifying against the tree and exiting
   `not-covered`) + `.agents/skills/ai-write/corpus.md` (new: `## Routes here` with the
   taken docs cases, `## Refuses` routing changelog→/ai-ship, spec→/ai-spec, note→/ai-note,
   issue→/ai-report), plus the `verified` case green.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_040_ai_write.py -k verified`
   **rollback**: `git revert <commit>`.
   **done when**: the skill passes `contract.audit_one` (no craft-lane problems), the
   corpus has Routes and Refuses, and the verified case passes.

3. [ ] **Capability entry (B-040-1)** —
   **file** `policy/capabilities.toml` (add `[[capabilities]] id = "ai-write"` with its
   mode using all fields: id, read_roots `["."]`, write_roots `["docs", "README.md"]`,
   exec_allowlist git scoped.change, network `[]`, secrets `[]`, human_gate
   `before_write`, enforcement `["preflight.read", "preflight.write", "preflight.exec",
   "preflight.human-gate"]`, proof_requirements with allow/deny + installed_artifact).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_040_ai_write.py -k verified && uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: the capability parses, the capability contract test passes over it, and
   the routing harness still counts.

4. [ ] **Reverse routes + baseline move (B-040-2)** —
   **file** `.agents/skills/ai-ship/corpus.md`, `.agents/skills/ai-spec/corpus.md`,
   `.agents/skills/ai-note/corpus.md`, `.agents/skills/ai-report/corpus.md` (each gains a
   quoted route: a README/wiki/product-docs request routes to `/ai-write`, phrased
   differently per surface) + `policy/pilot-register.toml` + `docs/requirements.toml`
   (baseline moves with its reason in this same commit).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_040_ai_write.py && uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: the four reverse routes parse as distinct cases, `routing` passes, and
   the baseline moves with a stated reason.

5. [x] <!--t:0088b23a6df8--> **Count move** —
   **file** `README.md` ("Seventeen written procedures") + `AGENTS.md` ("carries seventeen
   skills") → "Eighteen"/"eighteen", satisfying the `test_contracts.py` COUNTED pin.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k count`
   **rollback**: `git revert <commit>`.
   **done when**: the README and AGENTS prose match the derived count of eighteen.

6. [ ] **Map acceptances for this block's references** —
   **file** `policy/skill-map-accepted.toml` (accept the exact `(node, target)` pairs
   ai-write introduces — its pointer to `documentation-writer.md` and its corpus routes —
   with the dated record; the 039 documentation routes previously added are accepted in the
   same record since they are the same documentation block) — and verify the map's real
   count does not grow beyond 208 pre-existing when the block landed without acceptances.
   **check**: `just map`
   **rollback**: `git revert <commit>`.
   **done when**: `just map` prints the real-and-unaccepted count at or below the
   pre-existing 208 (ideally below, once this block's pairs are accepted), and the accepted
   entries carry the dated record.

7. [ ] **The gate** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0 with the 040 suite green, `tests/test_madr.py`
   reporting exactly the same pre-existing failures as before this block (the ADR 0025
   inherited red) — no new failure — and the spec, plan and approval of 040 are committed
   at their exact digests.