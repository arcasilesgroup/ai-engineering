# Plan: governed agentic engineering foundation — P0 atomic execution

## Approval and atomicity gate

No further implementation starts until a human explicitly approves **this exact `spec.md` and this exact `plan.md`**, explicitly including the SHA-256 digest of each file; any edit to either digest invalidates approval and requires re-approval. Tasks 1–39, the first two Block B repair commits, Task 39a, and Tasks 39b–39d with their `464bd161` repair are committed history implemented under earlier exact approvals. The human approved the amended specification at exact SHA-256 `6afc0721df6d3eb13589efeaefa94391ca62eaa71c0b1f2bc653fe3d34117759`, committed unedited as `e4c118bdc68b147df099cbc1c69c854b13685373`. That approval covers the specification only. The previously approved plan digest `742e8ffd0483f57c03fe4dca860ff01f222021c1ae655ef732f76d5d28590b09` is invalidated because the amended specification replaces the embedded-YAML acceptance writer with immutable published records, which that plan neither names nor budgets. No Task 39e or later implementation may start until the human approves the new exact plan digest. The reply is the gate; no `approval.md` is created.

**The specification has changed since that approval, and this line is what says so.** It now
hashes to `364d83c56c7d9e7b4e2aeb975c9ada5c7b0db6822d79eb939e9010b9417e75db`, because the
final candidate never proved its exact-HEAD receipts and `status` went back to `draft` under
the audit of 2026-08-15. The approval above covered `6afc0721…` and covers these bytes no
longer. Nothing here treats the difference as approval; it is recorded so that a reader can
see which of the two numbers is the file in front of them, and
`tests/test_record.py::test_the_approval_digests_in_the_plan_are_read_by_something` fails
when this paragraph and the file disagree. That check is the answer to PO-24: the digests
were prose that nothing read, so an edit to either file changed nothing anybody would notice.

The amended specification also states that treating a controlling-terminal response as the P0 human-authority handoff requires renewed human approval of this exact amended specification **and** this exact plan. That grant is not bundled into the digest approval, because a person approving a budget amendment should not silently also be granting the P0 authority semantics. The approval reply must therefore contain two separate named statements: one approving the exact plan digest, and one granting the controlling-terminal handoff. A reply carrying only the digest approves the plan and withholds the grant, and every acceptance task stays blocked until the grant arrives.

There is exactly one repository writer before P3. One delegated writer executes the Tasks in a block sequentially; a fresh independent read-only reviewer reviews the closed block before any later block may consume it. No global initialization, installation, network mutation, publishing, tagging, or deployment runs without separate explicit consent. Each Task remains one atomic commit. A Task may change exactly **one primary production, policy, documentation, or workflow file**, plus only its focused supporting test/fixture file(s); it may not change a second product home. Revisiting a primary file is allowed only for a named, distinct semantic change and a distinct commit. A block-review repair may revisit the affected Task's primary file only to resolve a named ledger finding; it remains an atomic commit inside that Task's original scope, and a finding never authorizes a second product home or broader behavior. The sole exception is the final transition: one semantic transaction updates primary spec010, its predecessor spec004, the dogfood `.ai/intent.md`, and `src/ai_engineering/contract.py`, plus their focused readiness and contract tests, to avoid either a stale record or an intermediate line ceiling; spec010 remains the named primary. Rollback for every Task and repair commit is `git revert <commit>`.

The checks for committed Tasks 1–39d are historical evidence. Every check for unstarted Tasks 39e–39u, 40–52, 52a–52c and 53 is an exact future red check: run it with `uv`, using the named `path::node`; it is red now because the node/file is absent or its assertion fails, and becomes green only after that Task. No broad `-k`, placeholder node, or invented green result is acceptable. P0 may verify release workflow/provenance contracts but cannot claim a release; spec 010 remains draft and boxes unticked until the final candidate proves its own exact-HEAD receipts. Remote checks select the current `HEAD` SHA and return `INCOMPLETE` when authentication or a run is unavailable. Publishing/tag authority is always a separate human decision.

Tasks 39b–39d and the `464bd161` repair are committed. The specification amendment is
committed at `e4c118bdc68b147df099cbc1c69c854b13685373`, which is the clean base this plan
amendment lands on as a record-only child. Task 39e then starts from that amendment commit.

One consequence is already observable and is not a defect to be fixed outside the plan: the
amendment changed `spec.md`, so `.ai/intent.md` still names the superseded target digest and
`tests/test_intent.py::test_repository_dogfood_intent_is_canonical` fails with
`INTENT_RELATION_STALE`. That is the branch's current red, it is not a `PASS`, and Task 39e
is the first governed task precisely so the branch does not stay red until Task 53.

Task 1 records a provisional maximum of **17,807 + 4,500 = 22,307 lines** in `contract.py`. Exceeding 22,307 stops work and requires an approved re-plan; it is not permission to raise the ceiling. The final candidate transaction measures the committed tree and removes slack.

The observed first nine tasks added 3,381 lines, or about 376 lines per task. Applying that observed rate to the 44 remaining implementation tasks forecast 16,544 more lines, so Task 10 re-planned the P0 maximum to **17,807 + 20,000 = 37,807 lines**. That forecast is now history. The committed tree after Task 39 measured 30,737 lines. Tasks 17–39 therefore added 6,530 lines across 23 tasks, about 284 per task; applying that rate to Tasks 40–53 forecasts 3,976 more. The two landed repair commits then added net 575 and 425 lines, so the measured pre-Task-39a base was 31,737 and the observed repair average is exactly 500. Five remaining product repair commits forecast another 2,500. The evidence-based total is therefore 31,737 + 3,976 + 2,500 = 38,213, already above the then-active ceiling. Task 39a raised the provisional maximum to **17,807 + 25,000 = 42,807 lines** and added one net line. That line and the bounded Task 39d workflow/test overhead consume the 4,594-line contingency; they do not change product scope, and the final candidate transaction still removes every line of slack.

### Measured budget at the acceptance amendment

`contract.repo_lines` counts every tracked file outside `specs/`, `docs/adr/`, `LICENSE` and
`NOTICE`. The specification amendment therefore added zero counted lines. Each figure below
was measured from the exact commit object, not estimated:

| Commit | Counted tree | Added |
|---|---|---|
| `c7642fab` Task 39a base | 31,738 | — |
| `0683cdec` Task 39b native backend | 33,387 | +1,649 |
| `464bd161` inventory repair | 33,567 | +180 |
| `e7cf9424` Task 39c integration | 34,520 | +953 |
| `75939c75` Task 39d matrix | 34,892 | +372 |
| `e4c118bd` specification amendment | 34,892 | +0 |

Every forecast below uses one of four measured rates and states which. No figure is invented
per task:

- **Native-wave rate, 789.** The four commits above added 3,154 lines, 788.5 each. It is the
  measured cost of creating or rewriting a product module together with its focal suite.
- **General task rate, 284.** Tasks 17–39 added 6,530 lines across 23 tasks.
- **Repair rate, 393.** The three landed ledger repairs added 575, 425 and 180 lines.
- **Record-only rate, 1.** Task 39a rewrote a comment block and added one net line.

The acceptance wave has seventeen implementation commits. Task 39e is record-only, so 1.
Task 39p is record-only, so 1. Tasks 39r and 39s are ledger repairs on shipped modules, so
393 each = 786. The remaining thirteen — the schema, the corpus, the two deterministic
scanners, the Gitleaks gate, the shared-backend generalization, the unified reader, the
chain allocator, the two writer integrations, the workflow, and the two CLI-contract
commits — each create or rewrite a module and its focal suite, so 789 each = **10,257**.
The wave forecast is 1 + 1 + 786 + 10,257 = **11,045**.

Tasks 40–52 keep the general rate: 284 × 13 = **3,692**. Tasks 52a–52c each add a new
`tests/test_madr.py` node, which `contract.repo_lines` counts even though `docs/adr/` is
excluded, so 284 × 3 = **852**. Task 53 keeps the general rate, **284**. Five block reviews
remain — the 39e–39p early sub-block, the Block B close, Block C, Block D and the final
cross-block review — at two bounded repairs each and the measured repair rate:
5 × 2 × 393 = **3,930**.

The evidence-based total is therefore 34,892 + 11,045 + 3,692 + 852 + 284 + 3,930 =
**54,695**, which exceeds the active 42,807 ceiling by 11,888. Work is not scoped down to
fit that number and the number is not raised by inertia. Task 39p is an explicit re-plan to
**17,807 + 38,000 = 55,807**, leaving 55,807 − 54,695 = 1,112 lines of contingency, and it
lands only under this plan's exact approved digest.

Task 39p is deliberately the last checkpoint of the early sub-block rather than an early
one, so the raise is justified by a measurement taken after the wave's largest and least
certain tasks have landed. At the forecast rate the tree reaches 34,893 after Task 39e and
42,783 after Task 39o — 24 lines under the active ceiling — so nothing crosses 42,807 before
Task 39p, and the sub-block's own repairs land after it. Task 39p records the tree it
actually measures, not this forecast; if that measurement makes the recomputed total exceed
55,807, work stops for another exact approved re-plan rather than proceeding. Reaching or
exceeding 55,807 is likewise a hard stop.

That 24-line margin is the residue of a mean, and 789 is the mean of observations that ran
from 372 to 1,649. One checkpoint running 25 lines over its forecast trips the active
ceiling before its own re-plan lands. The writer therefore measures the tree at every
checkpoint of this wave, and if any checkpoint before Task 39p measures 42,807 or more,
Task 39p is pulled forward to immediately before that task and measures there. Pulling it
forward changes its position only; its exact 55,807 assertion, its measured base and its
stop-work rule are unchanged, so the approved number is never raised by the reordering.

`contract.TEST_RATIO_MAX` remains 2.0 and the measured ratio is 1.455 (17,882 test lines
over 12,291 product lines). The comparable wave split its 3,154 lines as 1,312 test and
1,728 product, so the same proportions over 11,045 forecast 4,594 test and 6,052 product
lines and a ratio of 22,476 / 18,343 = 1.225. Every block gate observes both limits. The final
candidate transaction still measures the committed tree and removes every line of slack.

## Block checkpoint and review protocol

The optimization removes repeated hand-offs, not evidence. Before the first Task in a block, record the exact base SHA. For every Task checkpoint the single writer must:

1. confirm the authorized one-primary-file scope and run the named focal check red for the expected reason;
2. implement only that Task, make the focal check green, and run the immediate module suite when one exists;
3. run `git diff --check` and scan the changed content for secrets, personal data, machine paths, suppression comments, compatibility shims, and out-of-scope writes;
4. create one verified, revertible commit without `--no-verify`; and
5. label the hand-off **UNREVIEWED**. It is not approved, done, mergeable, publishable, a dependency for another block, or evidence of `PASS`.

`UNREVIEWED` is derived from the absence of a clean block review and gate; a commit message,
model statement, test label, or metadata field cannot turn it into approval. A Task's
existing “done when” sentence means only that its checkpoint is eligible to enter the
block review. The writer continues directly to the next Task in the same block. A full
semantic review and `just check` do **not** run after each Task. The block closes before any
later block depends on it. At closure:

1. freeze writes and run the block's named related suite;
2. give one fresh read-only reviewer the recorded base SHA, every checkpoint commit, and the accumulated range;
3. review each commit against its parent for Task scope and rollback, then the full range for architecture, integration, authority, fail-closed behavior, untrusted input, filesystem/Git/concurrency boundaries, security, privacy, and test strength;
4. return one consolidated finding ledger; the same writer resolves it in the smallest atomic repair commit or commits, and the reviewer performs one bounded re-review of those findings;
5. run `git diff --check` and `just check` once after review is clean. Re-run `just check` only when that run fails and code changes to fix it; and
6. report in the block hand-off the base, final HEAD, reviewed commits, related-suite output, reviewer disposition, repair commits, and gate output. This execution evidence does not create a new repository home or grant product authority. Only then is the block approved and available to the next block.

If a Task exposes a new authority or terminal outcome, fail-closed guard or blocking dispatcher path, parser of untrusted input, Git-history/filesystem/symlink/concurrency transaction, global mutation, network/release action, or evidence/provenance gate that later Tasks would consume, close the current prefix as an early sub-block before continuing. This is an exceptional dependency boundary, not a return to review-after-every-Task.

At the post-Task-16 cadence amendment, absent an evidenced early boundary, the remaining
cadence was four block-review starts plus one final cross-block review rather than one
review start per Task. Block A is now approved. Block B is reopened by this amendment for
the acceptance wave and its outstanding ledger repairs, and closes once at Tasks 39e–39u;
Blocks C and D plus the final cross-block review remain unopened.

Tasks 39k, 39l and 39n each expose a new fail-closed authority, filesystem or untrusted-input
boundary that every later acceptance task consumes. Under the early sub-block rule above,
the prefix 39e–39p closes as an early sub-block review before Task 39q starts. That is the
one exceptional boundary in this wave; it is not a return to review-after-every-Task.

The committed tree after Task 16 measured 24,207 lines. The committed tree at the specification amendment measures 34,892 lines. Every block gate observes the executable ceiling and the executable test ratio. Until Task 39p lands, reaching or exceeding 42,807 stops work; after it, 55,807 is the hard stop and requires another exact approved re-plan. Batching is never permission to raise or bypass either number.

## Ordered P0 atomic tasks

1. **Provisional line budget** — **file** `src/ai_engineering/contract.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_contracts.py::test_provisional_repo_ceiling_is_22307`.
   **rollback**: `git revert <commit>`.
   **done when**: records the exact 17,807 + 4,500 arithmetic, stop/re-plan rule, and provisional assertion only.

2. **Constitution mission and identity** — **file** `CONSTITUTION.md`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_contracts.py::test_constitution_mission_identity_and_never_rules`.
   **rollback**: `git revert <commit>`.
   **done when**: establishes the governed-agent mission, vocabulary, phase, and non-negotiable prohibitions without claiming unobserved controls.

3. **ai-spec governed procedure** — **file** `.agents/skills/ai-spec/SKILL.md`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_contracts.py::test_ai_spec_skill_requires_evidence_options_self_challenge_and_authority`.
   **rollback**: `git revert <commit>`.
   **done when**: procedure reads evidence, presents two options, self-challenges, records BDD/risks, and returns `INCOMPLETE` without authority.

4. **Intent schema** — **file** `policy/intent-v1.schema.json`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_intent.py::test_intent_v1_schema_is_closed_and_versioned`.
   **rollback**: `git revert <commit>`.
   **done when**: closed, versioned schema defines identity, solution intent, ownership, relations, and status transitions.

5. **Intent fixture corpus** — **file** `tests/fixtures/intent-v1.json`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_intent.py::test_intent_fixture_corpus_covers_valid_and_all_invalid_cases`.
   **rollback**: `git revert <commit>`.
   **done when**: contains valid plus every invalid missing, unknown, stale, broken, and cycle case used by the exact validator checks.

6. **Intent writer and validator** — **file** `src/ai_engineering/intent.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_intent.py::test_intent_validator_rejects_unknown_missing_stale_and_broken_relations`.
   **rollback**: `git revert <commit>`.
   **done when**: validates one canonical intent and emits exact `INCOMPLETE` reasons; no writes to foreign homes.

7. **Intent-only disposable ignore** — **file** `.ai/.gitignore`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_intent.py::test_ai_gitignore_unignores_only_intent_md`.
    **rollback**: `git revert <commit>`.
   **done when**: `.ai/` remains disposable while exactly `.ai/intent.md` is unignored and no other framework file is exposed.

8. **Write-once intent seed** — **file** `src/ai_engineering/skeletons.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_intent.py::test_skeleton_seed_is_write_once`.
    **rollback**: `git revert <commit>`.
   **done when**: the seed writes `.ai/intent.md` only when absent, refuses overwrite, and validates the canonical schema.

9. **Dogfood intent instance** — **file** `.ai/intent.md`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_intent.py::test_repository_dogfood_intent_is_canonical`.
    **rollback**: `git revert <commit>`.
   **done when**: this repository has one canonical, schema-valid intent instance used by doctor and audit.

10. **Evidence-based P0 budget re-plan** — **file** `src/ai_engineering/contract.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_contracts.py::test_replanned_repo_ceiling_is_37807`.
    **rollback**: `git revert <commit>`.
   **done when**: hard-replaces and removes the obsolete `test_provisional_repo_ceiling_is_22307` assertion with `test_replanned_repo_ceiling_is_37807`, records baseline 17,807 + 20,000 = 37,807 justified by the observed +3,381 across Tasks 1–9 (about 376 per task) and 44 remaining tasks, retains the old arithmetic only as history, and preserves the hard stop, re-plan requirement, and final zero-slack close.

11. **AGENTS doctrine home** — **file** `AGENTS.md`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_contracts.py::test_agents_is_nondisposable_home_and_doctrine_ceiling`.
    **rollback**: `git revert <commit>`.
   **done when**: `.ai/intent.md` joins the non-disposable homes and the doctrine ceiling passes; AGENTS.md remains the doctrine file.

12. **Intent doctor report** — **file** `src/ai_engineering/doctor.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_intent.py::test_doctor_reports_intent_home_and_incomplete_reasons`.
   **rollback**: `git revert <commit>`.
   **done when**: doctor reports missing, unknown, stale, and broken intent relations at the exact home.

13. **Intent audit** — **file** `src/ai_engineering/audit.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_intent.py::test_audit_recomputes_intent_relations_without_metadata_proof`.
   **rollback**: `git revert <commit>`.
   **done when**: audit independently recomputes intent relations and never treats metadata as proof.

14. **MADR schema** — **file** `policy/madr-v1.schema.json`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py::test_madr_v1_schema_graph_and_transitions_are_closed`.
   **rollback**: `git revert <commit>`.
   **done when**: closed schema defines decision graph, alternatives, consequences, owner, status, and supersession.

15. **MADR validator** — **file** `src/ai_engineering/madr.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py::test_madr_validator_fails_closed_on_invalid_graph_and_transition`.
    **rollback**: `git revert <commit>`.
   **done when**: validates MADR graph and transitions, returning `INCOMPLETE` on ambiguity.

16. **Hard `--madr` CLI semantic** — **file** `src/ai_engineering/decide.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py::test_decide_madr_accepts_madr_and_rejects_adr_alias`.
    **rollback**: `git revert <commit>`.
   **done when**: uses `--madr` as the only spelling and hard-rejects `--adr`; no compatibility alias.

### Block A — governed contract foundation (Tasks 17–26)

The block result is the complete MADR, capability, outcome, and evidence foundation. Task
checkpoints remain UNREVIEWED until the block closes. The required related suite is:
`uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py tests/test_capabilities.py tests/test_outcomes.py tests/test_evidence.py`.

17. **MADR Intent supersession record** — **file** `docs/adr/0005-intent-supersedes-0004.md`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py::test_intent_supersession_madr_is_complete`.
    **rollback**: `git revert <commit>`.
   **done when**: records why Intent supersedes ADR 0004 and preserves the historical record.

18. **MADR mission record** — **file** `docs/adr/0006-governed-mission.md`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py::test_mission_madr_has_options_risks_and_owner`.
    **rollback**: `git revert <commit>`.
   **done when**: records the mission decision with alternatives, risks, consequences, and owner.

19. **MADR CLI record** — **file** `docs/adr/0007-cli-contract.md`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py::test_cli_madr_has_hard_rename_and_transition_evidence`.
    **rollback**: `git revert <commit>`.
   **done when**: records canonical verbs, hard renames, output contract, and open risks (not accepted); no risk is accepted by this draft.

20. **Capability schema** — **file** `policy/capability-manifest.schema.json`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_capabilities.py::test_capability_schema_is_closed_and_permission_distinct`.
    **rollback**: `git revert <commit>`.
   **done when**: closed schema models capability, mode, scope, enforcement, and proof requirements.

21. **Fifteen capability declarations** — **file** `policy/capabilities.toml`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_capabilities.py::test_capabilities_toml_declares_exactly_fifteen_capabilities`.
    **rollback**: `git revert <commit>`.
   **done when**: declares all 15 capabilities with permission-distinct modes and no undeclared escape hatch.

22. **Capability validator/preflight** — **file** `src/ai_engineering/capability.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_capabilities.py::test_capability_preflight_denies_undeclared_and_unenforced_actions`.
    **rollback**: `git revert <commit>`.
   **done when**: validates declarations and installed preflight, returning `INCOMPLETE` when enforcement cannot be observed.

23. **Outcome schema** — **file** `policy/outcome-v1.schema.json`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_outcomes.py::test_outcome_v1_schema_is_closed_and_exact`.
    **rollback**: `git revert <commit>`.
   **done when**: closes READY/PASS/WARN/FAIL/INCOMPLETE/CANCELLED/WOULD_CHANGE, exits, reasons, and next actions.

24. **Outcome core** — **file** `src/ai_engineering/outcome.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_outcomes.py::test_outcome_core_maps_status_to_exact_exit_and_next_action`.
    **rollback**: `git revert <commit>`.
   **done when**: provides one canonical result object and exact exit mapping.

25. **Check/evidence schema** — **file** `policy/check-evidence-v1.schema.json`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_evidence.py::test_check_evidence_schema_requires_receipt_owner_protocol_and_independence`.
    **rollback**: `git revert <commit>`.
   **done when**: requires executable command, owner, protocol, receipt, independence, freshness, and digest fields.

26. **Evidence verifier** — **file** `src/ai_engineering/evidence.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_evidence.py::test_evidence_verifier_distinguishes_fail_missing_stale_malformed_and_digest_mismatch`.
    **rollback**: `git revert <commit>`.
   **done when**: distinguishes executed FAIL from missing/stale/malformed/digest-mismatched evidence and never treats labels as proof.

### Block B — emission, UI, and ten-verb integration (Tasks 27–39)

Block B cannot start until Block A is approved. Its result is one integrated CLI contract
over the governed foundations, including the immutable acceptance record writer added by the
amended specification. The required related suite for the closing block review is:
`uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_hooks.py tests/test_ui.py tests/test_cli_migration.py tests/test_spec_transaction.py tests/test_acceptance.py tests/test_record.py tests/test_mut_accept.py tests/test_intent.py tests/test_contracts.py tests/test_quality_gate.py tests/test_doctor.py`.
The early sub-block review at Task 39p runs the same command restricted to
`tests/test_spec_transaction.py tests/test_acceptance.py tests/test_cli_migration.py tests/test_record.py tests/test_mut_accept.py tests/test_intent.py tests/test_contracts.py tests/test_doctor.py`.
Both lists include every file that holds a focal node of a task in their range, and
`tests/test_mut_accept.py` and `tests/test_doctor.py` because Tasks 39n–39o rewrite the
writer and the reader those suites and `doctor` assertion 16 depend on.

27. **Hot-path IDs and emission** — **file** `hooks/_emit.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_hooks.py::test_emit_is_stdlib_only_and_assigns_opaque_operation_and_trace_ids`.
    **rollback**: `git revert <commit>`.
   **done when**: emits privacy-safe operation/trace IDs and rejects chain gaps without importing the package.

28. **UI semantics** — **file** `src/ai_engineering/ui.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_ui.py::test_ui_plain_rich_json_noninteractive_and_a11y_parity`.
    **rollback**: `git revert <commit>`.
   **done when**: guarantees stable reading order, text marks, `NO_COLOR`, `TERM=dumb`, non-TTY, and human/JSON parity.

29. **CLI JSON dispatch** — **file** `src/ai_engineering/cli.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_ui.py::test_cli_noninteractive_json_is_one_object_and_never_null`.
    **rollback**: `git revert <commit>`.
   **done when**: dispatches canonical verbs without prompts and emits one non-null JSON object.

30. **`init` migration** — **file** `src/ai_engineering/init.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_init_writes_only_canonical_homes_and_receipt`.
    **rollback**: `git revert <commit>`.
   **done when**: migrates init to the outcome/intent/capability contracts without touching another product home.

31. **`doctor` migration** — **file** `src/ai_engineering/doctor.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_doctor_migration_reports_all_contract_states`.
    **rollback**: `git revert <commit>`.
   **done when**: distinct semantic commit integrates canonical outcome reporting with existing doctor checks.

32. **`update` migration** — **file** `src/ai_engineering/update.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_update_is_explicit_non_auto_and_returns_outcome`.
    **rollback**: `git revert <commit>`.
   **done when**: update is explicit, never automatic, and returns canonical outcomes.

33. **`spec` migration** — **file** `src/ai_engineering/spec.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_spec_command_enforces_intent_and_authority`.
    **rollback**: `git revert <commit>`.
   **done when**: spec command consumes governed intent and refuses unapproved mutation.

34. **`decide` outcome migration** — **file** `src/ai_engineering/decide.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_decide_returns_canonical_outcome_after_madr_validation`.
    **rollback**: `git revert <commit>`.
   **done when**: distinct semantic commit routes valid/invalid MADR decisions through outcome core.

35. **`accept` migration** — **file** `src/ai_engineering/accept.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_accept_requires_named_owner_date_and_risk_evidence`.
    **rollback**: `git revert <commit>`.
   **done when**: dated risk acceptance requires named owner and evidence and cannot silently accept.

36. **`audit` migration** — **file** `src/ai_engineering/audit.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_audit_migration_recomputes_digest_and_returns_incomplete_when_blind`.
    **rollback**: `git revert <commit>`.
   **done when**: distinct semantic commit routes audit through evidence and outcome contracts.

37. **Hard `digest` to `report` rename** — **file** `src/ai_engineering/report.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_report_is_hard_rename_and_bare_report_refuses`.
    **rollback**: `git revert <commit>`.
   **done when**: hard-renames `digest.py` to `report.py`; only `report digest` is implemented, while bare `report` and `report issue` refuse as unimplemented P2.

38. **Hard `plan` to `exception` rename** — **file** `src/ai_engineering/exception.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_exception_is_hard_rename_without_plan_alias`.
    **rollback**: `git revert <commit>`.
   **done when**: hard-renames plan command/module to exception with no alias or compatibility shim.

39. **Uninstall command** — **file** `src/ai_engineering/uninstall.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_uninstall_is_explicit_and_returns_receipted_outcome`.
    **rollback**: `git revert <commit>`.
   **done when**: uninstall is explicit, receipt-aware, and refuses ambiguous/global mutation.

Fresh Block B review is a gate, not an approval source. It reproduced nine P1 boundary
defects. The CLI fact transport and update pin transaction are already distinct repair
commits. Tasks 39a–39d were the newly planned part of that ledger and are now committed. The
remaining `accept`, `exception` and `uninstall` findings stay atomic repairs inside their
original one-file product scopes under the block-review protocol above; they are Tasks 39n–39o,
39r and 39s below, where the `accept` finding is subsumed by the amended specification's
immutable record writer.

39a. **Replanned repository ceiling after measured Block B** — **file** `src/ai_engineering/contract.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_contracts.py::test_block_b_replanned_repo_ceiling_is_42807`.
    **rollback**: `git revert <commit>`.
   **done when**: hard-replaces the active 37,807 assertion with 42,807; records the committed 31,737-line base, 3,976-line remaining-task forecast, 2,500-line repair forecast, 38,213 evidence-based total, hard stop, and final zero-slack close; 37,807 remains history only.

39b. **Native no-replace spec transaction backend** — **file** `src/ai_engineering/spec_transaction.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_spec_transaction.py::test_native_spec_transaction_is_locked_staged_noreplace_and_alias_safe`.
    **rollback**: `git revert <commit>`.
   **done when**: a small stdlib backend provides non-blocking crash-safe writer locking, handle/fd-relative no-follow staging, bounded non-blocking regular-file reads, and atomic directory rename without replacement on Linux, macOS, and Windows; unsupported APIs or filesystems return `INCOMPLETE` before canonical mutation and no pathname cleanup API exists.

39c. **Spec authority transaction integration** — **file** `src/ai_engineering/spec.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_spec_command_publishes_only_from_unchanged_authority_snapshot`.
    **rollback**: `git revert <commit>`.
   **done when**: `spec new` locks the canonical writer, materializes and validates the exact Intent relation graph, stages only a noncanonical `pending-*` draft, revalidates every file and parent generation immediately before no-replace publication, returns truthful human/JSON facts, leaves no marker or pending on `PASS`, and never leaves a new canonical spec on `INCOMPLETE`; FIFO, alias, ABA, collision, timeout, unsupported backend, and exhausted ID paths fail closed.

39d. **Native spec transaction installed matrix** — **file** `.github/workflows/install-matrix.yml`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_quality_gate.py::test_install_matrix_executes_native_spec_transaction_on_every_supported_os`.
    **rollback**: `git revert <commit>`.
   **done when**: the installed wheel's exact Task 39b focal and native happy-path/collision controls execute on Linux, macOS, and Windows; Linux and macOS execute their real symlink/casing negative controls, Windows executes its real junction/reparse negative control, and no control selected for a runner may skip. A missing runner, fixture-construction failure, nonzero test result, or wheel/source mismatch is `INCOMPLETE`; this evidence grants no push, release, tag, or publication authority.

### Block B continued — immutable acceptance records (Tasks 39e–39u)

The amended specification replaces the embedded-YAML acceptance writer with immutable
published records. These tasks are the whole of that change plus the two outstanding Block B
ledger repairs and the missing executable human CLI contract. Every check below is an exact
future red check: the node or file is absent today, or its assertion fails for the stated
reason. `tests/test_acceptance.py` is the new focused test file; it does not exist yet, so
every node named in it is red for that reason until its Task creates it.

39e. **Intent rebind to the approved specification digest** — **file** `.ai/intent.md`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_intent.py::test_repository_dogfood_intent_is_canonical`.
    **rollback**: `git revert <commit>`.
   **done when**: the single relation's `target_digest` equals the SHA-256 of the committed approved `spec.md`, the lifecycle facts still say the specification is draft with P0 in progress, no authority is invented, and `intent.validate` returns `PASS` instead of `INTENT_RELATION_STALE`. This check is red now for exactly that code.

39f. **Closed risk-acceptance schema** — **file** `policy/risk-acceptance-v1.schema.json`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_acceptance.py::test_risk_acceptance_v1_schema_is_closed_and_exact`.
    **rollback**: `git revert <commit>`.
   **done when**: one JSON Schema 2020-12 document with `additionalProperties: false` requires exactly the seventeen specified top-level fields with their exact constants, patterns, enumerations, byte bounds and integer range, and a closed `evidence` object with only `path` and `content_digest`; no field is optional and no undeclared escape hatch exists.

39g. **Versioned valid and adversarial corpus** — **file** `tests/fixtures/risk-acceptance-v1.json`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_acceptance.py::test_acceptance_corpus_covers_valid_adversarial_and_privacy_cases`.
    **rollback**: `git revert <commit>`.
   **done when**: one versioned corpus carries the valid record; every record rejection the specification names, including unknown field, invalid UTF-8, control character, non-canonical JSON, path/ID/spec/digest disagreement, oversized value, duplicate ID, exhausted ordinal, cycle, fork, wrong `record_digest`, wrong `renews_digest`, third renewal and expiry before `accepted`; every legacy-block case, including valid, ID-less, wrong container type, unknown key, out-of-range and `once` `renewals`, and malformed date; and every privacy case, including secret, email address, IP address, phone-like identifier, personal-name ambiguity, POSIX home path, Windows drive path, UNC path, clean role and reason, missing Gitleaks and wrong-version Gitleaks.

39h. **Deterministic `acceptance_pii_v1`** — **file** `src/ai_engineering/acceptance_privacy.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_acceptance.py::test_acceptance_pii_v1_is_deterministic_and_fails_closed`.
    **rollback**: `git revert <commit>`.
   **done when**: the check is deterministic over candidate text, returns `FAIL` on a conclusive personal datum, `INCOMPLETE` on unsupported input or undecidable classification including personal-name ambiguity, and clean only when it actually decided; it records no candidate text outside its result and never reaches clean by exhausting a bound.

39i. **Deterministic `acceptance_machine_path_v1`** — **file** `src/ai_engineering/acceptance_privacy.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_acceptance.py::test_acceptance_machine_path_v1_rejects_posix_windows_and_unc_paths`.
    **rollback**: `git revert <commit>`.
   **done when**: POSIX home, Windows drive and UNC machine paths are `FAIL`, a normalized repository-relative path is clean, and unsupported or undecidable input is `INCOMPLETE`; it shares no mutable state with the PII check.

39j. **Exact Gitleaks 8.30.1 gate** — **file** `src/ai_engineering/acceptance_privacy.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_acceptance.py::test_gitleaks_gate_requires_exact_version_and_three_clean_results`.
    **rollback**: `git revert <commit>`.
   **done when**: the gate runs `gitleaks dir . --redact --no-banner --exit-code 1` inside the unpublished record directory, verifies exactly version 8.30.1, maps exit 1 to a conclusive `FAIL`, exit 0 to clean and absence, version drift or any other exit to `INCOMPLETE`, and lets publication proceed only when all three privacy results are clean; scanner output is never recorded outside `record.json`.

39k. **Bounded multi-component transaction home** — **file** `src/ai_engineering/spec_transaction.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_spec_transaction.py::test_transaction_home_is_a_bounded_anchored_multi_component_walk`.
    **rollback**: `git revert <commit>`.
   **done when**: the single shared native backend accepts a bounded repository-relative home of more than one component and opens and revalidates every component one exact entry at a time under the anchored root, keeping the existing symlink, mount, reparse, alias, spelling, device, hard-link, generation and `INCOMPLETE`/unsupported behaviour unchanged for the single-component home.
   **review-protocol obligations, not check conditions**: no second backend, copy, alias or compatibility path is created, and the module docstring states the module's real scope. The block reviewer verifies both; the focal node cannot see either.

39l. **Unified acceptance register reader** — **file** `src/ai_engineering/acceptance.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_acceptance.py::test_unified_reader_separates_integrity_from_binding_freshness`.
    **rollback**: `git revert <commit>`.
   **done when**: one reader validates canonical records and frozen legacy blocks, normalizes only in memory, enforces every stated bound of 1,000 spec directories, 99 records per spec, 1 MiB per `spec.md`, 64 KiB per `record.json`, 64 MiB in total and 100,000 bytes of evidence, evaluates record and chain integrity strictly before current-binding freshness, computes a legacy block digest over the exact stored byte span from the first backtick of its opening three-backtick `yaml` delimiter through the third backtick of its closing delimiter without rewriting or canonicalizing it, labels every displayed identity `stored legacy`, `derived legacy` or `canonical record`, returns `INCOMPLETE` rather than a partial or empty green for unreadable, malformed, duplicate, ambiguous, hard-linked, symlinked, reparse, mount-crossing, aliased or over-bound input, and returns no result that can change any other check's status — a matching live record leaves a `FAIL` or `INCOMPLETE` exactly as it was, and the focal node asserts that suppression prohibition directly.

39m. **Namespace ordinals and renewal chains** — **file** `src/ai_engineering/acceptance.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_acceptance.py::test_ordinals_and_renewal_chains_span_legacy_noncanonical_and_derived_ids`.
    **rollback**: `git revert <commit>`.
   **done when**: ordinal allocation snapshots every direct child whose leaf name extracts the same three-digit owner, fills historical gaps, reserves one ordinal per ID-less legacy block in stable `(home byte spelling, block byte offset)` order with a derived in-memory `R-<owner>-<NN>` that is never written back, refuses an undecidable leaf, a duplicate ID, an ID/owner mismatch and the exhausted `99` ceiling as `INCOMPLETE`, resolves repository-wide chains by exact `finding` to one head, and returns the conclusive `FAIL` for a requested third renewal.

39n. **Immutable acceptance publication** — **file** `src/ai_engineering/accept.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_accept_publishes_one_immutable_record_without_replacement`.
    **rollback**: `git revert <commit>`.
   **done when**: `ai-eng accept` never opens `spec.md` for write; it displays the exact finding, severity, authority role, expiry, justification, follow-up and digest-bound paths, requires the exact `ACCEPT <id> AS <authority_role>` response read from the OS controlling terminal, refuses the denied role tokens after NFKC case-folded tokenization, re-obtains the UTC date immediately after that response and returns `INCOMPLETE` when the expiry is then in the past, reopens every anchored source for the final bounded read, stages canonical JSON in an owned unpublished sibling, flushes that staged file and its directory before the rename, commits through the native exclusive no-replace rename as the sole commit point, treats reported rename success as a committed `PASS` with no fallible post-commit relabel, records no candidate text, scanner output or controlling-terminal device name anywhere outside `record.json`, and leaves neither a final nor a temporary entry on `INCOMPLETE`; no outcome claims respondent identity, source currentness, power-loss durability, tamper-proof storage or independent attestation.

39o. **Renewal, unified expiry view and single reader** — **file** `src/ai_engineering/accept.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_accept_renews_a_stale_head_without_altering_it`.
    **rollback**: `git revert <commit>`.
   **done when**: renewal requires an exact `--spec NNN` canonical target, shows the predecessor's complete old canonical bytes or exact legacy block digest together with the newly observed spec and evidence, binds `renews` and `renews_digest` to the unique repository-wide chain head including a derived legacy identity, increments `renewals` by exactly one, and leaves the predecessor byte-identical; an integrity-invalid head is refused rather than repaired by the renewal, an integrity-valid stale head stays renewable, and the expiry view judges only the unique head. The same commit deletes `accept.blocks`, `accept.renewals_of` and `accept.expired`, leaving `acceptance.py` as the only reader of acceptance bytes in the repository; `doctor` assertion 16 and `git-hooks/pre-push` consume that single reader and still fail closed on an expired, malformed or unreadable register.

39p. **Measured acceptance-wave repository ceiling** — **file** `src/ai_engineering/contract.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_contracts.py::test_acceptance_replanned_repo_ceiling_is_55807`.
    **rollback**: `git revert <commit>`.
   **done when**: hard-replaces `test_block_b_replanned_repo_ceiling_is_42807` and the active 42,807 assertion with 55,807; records the measured tree at this commit's parent as the new base, the four measured rates 789/284/393/1 with the commits they came from, the remaining forecast recomputed from that measured base, `17,807 + 38,000 = 55,807`, the resulting contingency, the hard stop, the re-plan requirement and the final zero-slack close; 42,807 remains history only. If the recomputed total from the measured base exceeds 55,807, this task does not land: work stops and another exact plan approval is required.

Task 39p is the last checkpoint of the early sub-block. The prefix 39e–39p then closes under
the sub-block review described above, and its bounded repairs land under the new ceiling,
before Task 39q starts.

39q. **Installed acceptance matrix** — **file** `.github/workflows/install-matrix.yml`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_quality_gate.py::test_install_matrix_executes_acceptance_publication_on_every_supported_os`.
    **rollback**: `git revert <commit>`.
   **done when**: every Task 39d native-transaction runner and control is preserved unchanged, and the installed wheel additionally executes the exact acceptance focal plus real happy-path, collision and privacy-refusal controls on Linux, macOS and Windows; Linux and macOS execute their real symlink and casing negative controls, Windows executes its real junction/reparse control, and no control selected for a runner may skip. A missing runner, fixture-construction failure, nonzero result or wheel/source mismatch is `INCOMPLETE`, and this evidence grants no push, release, tag or publication authority.

39r. **Exception grant repair** — **file** `src/ai_engineering/exception.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_exception_refuses_aliased_bypass_and_leaves_no_grant_after_incomplete`.
    **rollback**: `git revert <commit>`.
   **done when**: the grant store is reached only through an anchored root with no symlink, alias, reparse point or junction at or above `bypass.json`; an `INCOMPLETE` outcome leaves no active grant behind; and a grant cannot remain live without its observable evidence.
   **review-protocol obligation, not a check condition**: no suppression, alias or compatibility path is added. The repository has no executable suppression gate, so the block reviewer verifies it.

39s. **Uninstall ancestor repair** — **file** `src/ai_engineering/uninstall.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_uninstall_refuses_an_ancestor_redirected_global_mutation`.
    **rollback**: `git revert <commit>`.
   **done when**: no ancestor symlink, reparse point or junction can redirect a global mutation, foreign bytes in shared configuration files are preserved exactly, and an ownership, path or identity property this code cannot observe is `INCOMPLETE` rather than a removal.

39t. **Executable human CLI contract** — **file** `src/ai_engineering/ui.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_ui.py::test_ui_will_running_and_cure_contract_is_executable`.
    **rollback**: `git revert <commit>`.
   **done when**: the module renders a will-and-scope statement, a counted `RUNNING i/n` line whose `n` is the declared step count and whose `i` can never exceed it, and a cure line it refuses to render for any status other than `FAIL` or `INCOMPLETE`; every form keeps the existing plain, rich, JSON, `NO_COLOR`, `TERM=dumb`, non-TTY and reading-order parity, and no cure text may name a bypass.

39u. **Ten-verb will and progress integration** — **file** `src/ai_engineering/cli.py`, as a distinct semantic change and a distinct commit.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_cli_migration.py::test_every_verb_states_its_will_before_mutating_and_counts_its_steps`.
    **rollback**: `git revert <commit>`.
   **done when**: each of the ten canonical verbs states its will and scope before its first mutation, emits counted `RUNNING i/n` matching the steps it actually runs, and offers a cure only with `FAIL` or `INCOMPLETE`; a verb that mutates before stating its will, miscounts its steps, or offers a cure on any other status fails the check, and non-interactive JSON remains exactly one non-null object.

Block B then closes under the block-review protocol: freeze writes, run the consolidated
related suite named above, hand one fresh read-only reviewer the base
`e4c118bdc68b147df099cbc1c69c854b13685373`, every checkpoint commit and the accumulated
range, resolve the consolidated ledger in bounded atomic repairs, re-review those findings
once, then run `git diff --check` and `just check` once. Only then is Block B approved and
available to Block C.

The block hand-off additionally carries one consent-gated evidence step, which is not a Task
because it writes nothing and has no commit to revert. After separate explicit push consent
and only then, push the approved unchanged Block B HEAD and apply the exact `gh` queries in
“Final candidate and receipt sequence” to `install-matrix.yml` at that SHA: `headSha` must
equal the pushed SHA, `status` must be `completed`, `conclusion` must be `success`, and the
Linux, macOS and Windows jobs must each have executed their acceptance and native-transaction
controls with no skip. Missing consent, authentication, run or job is `INCOMPLETE`, and the
result is never simulated, inferred from the static workflow file, or claimed from a local
run. Withheld consent leaves Block B closed but unreceipted, which blocks nothing before
Task 53: it is Task 53's own exact-HEAD receipts that must prove the integrated system, and
Blocks C and D may proceed on the approved block review alone. This step grants no release,
tag or publication authority.

### Block C — enforcement and observable wiring (Tasks 40–44)

Block C cannot start until Block B is approved. Its result is observed guard, dispatcher,
wiring, and git-anchor liveness without converting telemetry into authority. The required
related suite is:
`uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_hooks.py tests/test_install.py tests/test_doctor.py`.

40. **Guard hard rename** — **file** `hooks/change_scope_guard.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_hooks.py::test_change_scope_guard_is_hard_rename_of_design_gate`.
    **rollback**: `git revert <commit>`.
   **done when**: hard-renames `design_gate` with dispatcher-visible guard class and no alias.

41. **Dispatcher chain** — **file** `hooks/chain.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_hooks.py::test_dispatcher_table_marks_blocking_hooks_as_guards_and_rejects_gaps`.
    **rollback**: `git revert <commit>`.
   **done when**: dispatcher enforces hook class declarations, chain continuity, and fail-closed blocking events.

42. **Wrapper cure** — **file** `hooks/_wrap.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_hooks.py::test_wrap_cures_plan_exception_naming_and_preserves_fail_closed_guard`.
    **rollback**: `git revert <commit>`.
   **done when**: distinct wrapper semantic change removes plan naming and preserves guard/telemetry failure contracts.

43. **Observable git-anchor liveness before persistence** — **file** `src/ai_engineering/wiring.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_install.py::test_wire_git_executes_the_configured_module_before_persisting_it`.
    **rollback**: `git revert <commit>`.
   **done when**: `wire_git` safely executes the exact command `[sys.executable, -m, ai_engineering.cli, --version]` before persisting `ai.eng`, and failure or timeout writes none of the three git-anchor keys.

44. **Doctor assertion 11 live git-anchor proof** — **file** `src/ai_engineering/doctor.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_doctor.py::test_assertion_11_rejects_a_live_interpreter_with_a_dead_ai_eng_module`.
    **rollback**: `git revert <commit>`.
   **done when**: assertion 11 executes no shell or arbitrary configured command: it requires `ai.eng` to decompose exactly to the current `sys.executable` plus `-m ai_engineering.cli`, safely executes the argument list for `audit --anchor` with a timeout and isolated `HOME`, and requires exit 0 plus exactly one valid footer; mismatch, dead module, timeout, or invalid footer is `INCOMPLETE` with the consented cure `ai-eng init --project`.

The `commit-msg` telemetry hook intentionally remains fail-open so it cannot block Git. Tasks 43–44 make anchor liveness observable at installation and diagnosis; they do not convert telemetry into a guard.

### Block D — candidate evidence and readiness (Tasks 45–52)

Block D cannot start until Block C is approved. Its result is the local/static candidate
evidence pack; it grants no release, push, tag, or publication authority. The required
related suite is:
`uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_quality_gate.py tests/test_readiness.py tests/test_p0_completeness.py`.

45. **Quality gate workflow** — **file** `.github/workflows/check.yml`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_quality_gate.py::test_check_workflow_marks_missing_or_skipped_evidence_incomplete`.
    **rollback**: `git revert <commit>`.
   **done when**: existing test/lint/type/coverage/mutation/SAST/dependency/action lanes remain, and missing/skipped results are `INCOMPLETE`, never silently green.

46. **Installed matrix workflow** — **file** `.github/workflows/install-matrix.yml`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_quality_gate.py::test_install_matrix_preserves_native_transaction_and_proves_head_wheel_renames_and_json`.
    **rollback**: `git revert <commit>`.
   **done when**: preserves every Task 39d native transaction runner/control and every Task 39q acceptance runner/control unchanged, then extends the installed-wheel matrix to prove inventory, hard renames, JSON and negative controls; unavailable auth/run is `INCOMPLETE`.

47. **Release provenance workflow** — **file** `.github/workflows/release.yml`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_quality_gate.py::test_release_workflow_retains_wheel_contents_provenance_and_head_sha_receipts`.
    **rollback**: `git revert <commit>`.
   **done when**: preserves wheel contents/provenance lanes and verifies static/local contracts; the release tag commit must be contained in `origin/main`, with no claimed observed release receipt.

48. **Readiness receipt verifier** — **file** `src/ai_engineering/readiness.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_readiness.py::test_readiness_requires_eight_executable_fresh_receipts_and_negative_controls`.
    **rollback**: `git revert <commit>`.
   **done when**: verifies executable receipts for CI/CD, logs, traces, uncaught errors, health/data age, independent external check, second path/digest recomputation, and security scans; stale/missing receipts are `INCOMPLETE`.

49. **Adversarial receipt runner** — **file** `tests/adversarial/run.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_readiness.py::test_adversarial_runner_records_denials_and_clean_control`.
    **rollback**: `git revert <commit>`.
   **done when**: actually executes attacks and clean controls and records separate receipts for required local commands.

50. **Doctor readiness integration** — **file** `src/ai_engineering/doctor.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_readiness.py::test_doctor_json_includes_readiness_receipt_status_and_age`.
    **rollback**: `git revert <commit>`.
   **done when**: distinct semantic commit exposes readiness receipt status/age in doctor JSON, with no claim beyond observed evidence.

51. **Breaking-change changelog** — **file** `CHANGELOG.md`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_contracts.py::test_changelog_names_all_p0_hard_renames_deletes_and_fail_closed_changes`.
    **rollback**: `git revert <commit>`.
   **done when**: documents hard renames/deletes, canonical homes, and fail-closed behavior in plain language.

52. **P0 completeness mapping** — **file** `tests/test_p0_completeness.py`.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_p0_completeness.py`.
    **rollback**: `git revert <commit>`.
   **done when**: one primary test maps every P0 requirement, rejects P1–P5 requirements and aliases, and runs inside `just check`.

MADRs 0005, 0006 and 0007 are still `proposed`, so P0 cannot close on them. Before Task 52a
starts, ask the human for the exact `authority_role`, `approval_ref` and `approved_at` value
of each record. A model never supplies one, a default is never substituted, and a missing
value is `INCOMPLETE`, which stops the task rather than inventing an approval.

52a. **MADR 0005 authority transition** — **file** `docs/adr/0005-intent-supersedes-0004.md`, as a distinct semantic change and a distinct commit.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py::test_intent_supersession_madr_is_accepted_with_named_authority`.
    **rollback**: `git revert <commit>`.
   **done when**: the status moves from `proposed` to `accepted` carrying exactly the three human-supplied values, the validator accepts the transition, and no other field of the record changes.

52b. **MADR 0006 authority transition** — **file** `docs/adr/0006-governed-mission.md`, as a distinct semantic change and a distinct commit.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py::test_mission_madr_is_accepted_with_named_authority`.
    **rollback**: `git revert <commit>`.
   **done when**: the same transition lands with its own three human-supplied values and the recorded alternatives, risks, consequences and owner are unchanged.

52c. **MADR 0007 authority transition** — **file** `docs/adr/0007-cli-contract.md`, as a distinct semantic change and a distinct commit.
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_madr.py::test_cli_madr_is_accepted_with_named_authority_and_no_accepted_risk`.
    **rollback**: `git revert <commit>`.
   **done when**: the same transition lands with its own three human-supplied values, its open risks remain open, and no risk is accepted by this record.

### Final cross-block integration and candidate (Task 53)

Task 53 cannot start until Blocks A–D are approved. Its reviewer is fresh to the final
candidate and treats the block reviews as evidence, not as a substitute for checking the
integrated system. The final review covers Spec 010 traceability, cross-block contracts,
authority and evidence flows, hard-renamed surfaces and removed aliases/homes, installed
wheel behavior, CI/readiness/provenance, exact budget closure, and exact-HEAD receipts.

53. **Final candidate: exact ceiling, record transition, and dogfood refresh** — **file** `specs/010-governed-agentic-engineering-foundation/spec.md`; **same atomic transaction also changes** `specs/004-solution-intent-home/spec.md`, `.ai/intent.md`, `src/ai_engineering/contract.py`, `tests/test_readiness.py`, and `tests/test_contracts.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_readiness.py::test_spec_010_004_intent_and_ceiling_transition_atomically`.
    **rollback**: `git revert <commit>`.
   **done when**: the last local candidate commit counts the final tree including its own readiness test and record changes, sets `REPO_CEILING` and its comment/assertion to that exact count with zero slack, sets spec010's final status and eight evidence records, supersedes spec004, requires MADRs 0005, 0006 and 0007 to be `accepted` with their named human authority rather than `proposed`, and refreshes `.ai/intent.md` with the current spec010 digest, current lifecycle facts, no invented authority, and product-validator `PASS`; the focused check proves only those static local finalization invariants and has no live-receipt dependency, so the candidate must pass local `just check` before push and the same suite in CI. The transition is accepted as done/shipped only when those static gates and, after separate push consent, the separate shell/readiness proof of exact own-HEAD check/install receipts both pass. Any missing authentication, live receipt, or gate is `INCOMPLETE` and the candidate is reverted before any shipped declaration, tag, or publication. No release receipt or publishing authority is implied. This final task is last.

## Deliberate omissions and deferred waves

- **P1 surfaces:** implementation waits for exact landed P0 Intent, MADR, capability, outcome, and evidence versions. Preserve foreign config bytes and report discovery/invocation/enforcement separately. OpenCode currently checks only `status===2`; `null` from spawn failure/timeout can pass. Add installed-artifact negative tests and fail closed in P1; `pi` and `zed` remain T3/`UNPROVEN`. No OpenCode edit is P0.
- **P2 craft/reporting:** accessibility polish, animation, image/import governance, restored specialist skills, and public `report issue` remain P2. P0 only implements local `report digest` and refuses issue/public submission.
- **P3 coordination:** no councils, leases, takeover, parallel writers, or merge groups until a separately approved compare-and-swap/race-proof plan. One writer remains mandatory.
- **P4 scanners/release:** native detectors, SARIF, SBOM/attestation, and tamper fixtures require a separate approved plan; P0 retains current lanes and verifies provenance contracts only.
- **P5 pilots:** external upgrades, human/no-human comparisons, measured pilots, model scores, URLs, deployment, and compliance claims require P0–P4 proof and consent.
- **No rename of the shared native backend:** `spec_transaction.py` now publishes acceptance records as well as specs, so its name is narrower than its job. A hard rename is still refused here because it would force `spec.py` — a second product home — into the same commit, which this plan's atomicity rule forbids. Task 39k instead states the module's real scope in its docstring, and the rename remains available to a later single-purpose task.
- **No acceptance preauthorization:** the specification defines no risk-acceptance preauthorization schema, so P0 has no policy path to authority. Every acceptance needs the controlling-terminal response; a flag, environment value, piped answer, model or reviewer never substitutes for it.
- **No Git-ref or service-backed acceptance transaction:** the rejected option 2 stays rejected. It is revisited only by a superseding spec with a measured need, never by an implementation choice.
- **No power-loss durability claim:** no supported runner executes a crash/recovery fixture in P0, so no record, outcome or document may claim durability across sudden power loss.
- **The `.ai/reports/` research HTML is not policy:** the process-optimization and evolution-proposal reports are historical research. The block-review protocol in this plan is the authoritative home of the optimized process, and no requirement enters implementation except through an approved spec and this plan.
- **Observed dogfooding liveness failure:** the current editable installation's `.pth` points to a deleted worktree, leaving a live interpreter with a dead `ai_engineering.cli` module while the persisted git anchor still looks configured. Tasks 43–44 add safe pre-persist and diagnostic execution proof. Do not repair or replace the global installation without separate explicit consent.

Each deferred wave requires its own exact spec/plan approval, atomic tasks, red checks, receipts, rollback, and observed evidence. Compatibility aliases, copied skill trees, silent network, automatic risk acceptance, and JSONL without a demonstrated consumer remain prohibited. The OpenCode `status===2`/`null` risk remains explicitly open until P1.

## Final candidate and receipt sequence

After Blocks A–D and their gates pass, Task 53 creates the last local candidate commit. A fresh final reviewer inspects that commit and the complete Task 17–53 range against the final cross-block scope above. Any finding makes the candidate `INCOMPLETE`: revert Task 53, repair the responsible earlier Task or block atomically, repeat that bounded block review/gate, and create a new Task 53 candidate whose exact line count includes every repair. The final review must be clean before push consent is requested.

Nothing says Task 53 runs after receipts: its own immutable candidate SHA is the subject the receipts must prove. Before any push, record that SHA and run Task 53's focused static check, `git diff --check`, `just check`, `uv run python tests/adversarial/run.py`, `just mutate`, and the exact static release-workflow check from Task 47. The focused test has no network or live-receipt dependency; its static invariants therefore run locally and inside the candidate's CI. Failure is `INCOMPLETE` and the candidate is reverted.

Only with separate push consent, push that unchanged candidate and capture its exact-HEAD check and installed-matrix receipts with:
```
sha=$(git rev-parse HEAD)
id=$(gh run list --repo arcasilesgroup/ai-engineering --workflow check.yml --commit "$sha" --limit 1 --json databaseId --jq '.[0].databaseId // ""'); test -n "$id"; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json headSha --jq '.headSha')" = "$sha"; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json status --jq '.status')" = completed; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json conclusion --jq '.conclusion')" = success
id=$(gh run list --repo arcasilesgroup/ai-engineering --workflow install-matrix.yml --commit "$sha" --limit 1 --json databaseId --jq '.[0].databaseId // ""'); test -n "$id"; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json headSha --jq '.headSha')" = "$sha"; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json status --jq '.status')" = completed; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json conclusion --jq '.conclusion')" = success
```
Each workflow must have exact `headSha == "$sha"`, `status == completed`, and `conclusion == success`; otherwise `INCOMPLETE`. Empty output or unavailable authentication is `INCOMPLETE`. Do not query release HEAD runs. These shell queries are the separate live readiness proof; they are not simulated by or prerequisites of the focused pytest node. Task 53 is done, and its shipped transition becomes an accepted claim, only when the static focused check, every local final command, candidate CI, and both live exact-HEAD workflow proofs pass. Any failure requires `git revert <candidate-commit>` before declaring shipped, tagging, or publishing. Release work is limited to local/static workflow/provenance checks; it does not require or claim an observed release receipt. Any later tag commit must be contained in `origin/main`, and tagging and publishing require separate explicit consent.
