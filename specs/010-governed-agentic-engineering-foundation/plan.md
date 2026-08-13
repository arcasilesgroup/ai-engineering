# Plan: governed agentic engineering foundation — P0 atomic execution

## Approval and atomicity gate

No further implementation starts until a human explicitly approves **this exact `spec.md` and this exact `plan.md`**, explicitly including the SHA-256 digest of each file; any edit to either digest invalidates approval and requires re-approval. Tasks 1–16 are committed history implemented under earlier exact approvals. The plan digest `27089d780a82e070b3cfc3a62ebc9a6158bdde626214cbe9dd1c5a5d97794bbd` is invalidated only because the human requested a different execution cadence: atomic Task checkpoints remain, but review and the full gate move from every Task to capability-block closure. No Task 17 or later implementation may start until the human approves the new exact plan digest. The reply is the gate; no `approval.md` is created.

There is exactly one repository writer before P3. One delegated writer executes the Tasks in a block sequentially; a fresh independent read-only reviewer reviews the closed block before any later block may consume it. No global initialization, installation, network mutation, publishing, tagging, or deployment runs without separate explicit consent. Each Task remains one atomic commit. A Task may change exactly **one primary production, policy, documentation, or workflow file**, plus only its focused supporting test/fixture file(s); it may not change a second product home. Revisiting a primary file is allowed only for a named, distinct semantic change and a distinct commit. A block-review repair may revisit the affected Task's primary file only to resolve a named ledger finding; it remains an atomic commit inside that Task's original scope, and a finding never authorizes a second product home or broader behavior. The sole exception is the final transition: one semantic transaction updates primary spec010, its predecessor spec004, the dogfood `.ai/intent.md`, and `src/ai_engineering/contract.py`, plus their focused readiness and contract tests, to avoid either a stale record or an intermediate line ceiling; spec010 remains the named primary. Rollback for every Task and repair commit is `git revert <commit>`.

The checks for committed Tasks 1–16 are historical evidence. Every check for unstarted Tasks 17–53 is an exact future red check: run it with `uv`, using the named `path::node`; it is red now because the node/file is absent or its assertion fails, and becomes green only after that Task. No broad `-k`, placeholder node, or invented green result is acceptable. P0 may verify release workflow/provenance contracts but cannot claim a release; spec 010 remains draft and boxes unticked until the final candidate proves its own exact-HEAD receipts. Remote checks select the current `HEAD` SHA and return `INCOMPLETE` when authentication or a run is unavailable. Publishing/tag authority is always a separate human decision.

Any Task 17 bytes written before this cadence amendment remain inert, preserved outside the
worktree, and are not a checkpoint. After exact approval, Task 17 starts from the clean
Task 16 HEAD: observe its named red check there, restore only its authorized two-file diff,
verify the green checkpoint controls below, and then create its UNREVIEWED commit.

Task 1 records a provisional maximum of **17,807 + 4,500 = 22,307 lines** in `contract.py`. Exceeding 22,307 stops work and requires an approved re-plan; it is not permission to raise the ceiling. The final candidate transaction measures the committed tree and removes slack.

The observed first nine tasks added 3,381 lines, or about 376 lines per task. Applying that observed rate to the 44 remaining implementation tasks forecasts 16,544 more lines. Task 10 therefore re-plans the P0 maximum to **17,807 + 20,000 = 37,807 lines**. Exceeding 37,807 is still a hard stop requiring another approved re-plan, never permission to raise the ceiling; the final candidate transaction still removes all slack.

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

Absent an evidenced early boundary, the remaining cadence is exactly four block-review
starts plus one final cross-block review, rather than one review start for each of the 37
remaining Tasks.

The committed tree after Task 16 measures 24,207 lines, leaving 13,600 under `REPO_CEILING`. Every block gate observes the executable ceiling. Reaching or exceeding 37,807 stops work and requires another exact approved re-plan; batching is never permission to raise or bypass it.

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
over the governed foundations. The required related suite is:
`uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_hooks.py tests/test_ui.py tests/test_cli_migration.py`.

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
   **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_quality_gate.py::test_install_matrix_uses_head_sha_and_proves_installed_wheel_renames_and_json`.
    **rollback**: `git revert <commit>`.
   **done when**: installed-wheel matrix proves inventory, hard renames, JSON and negative controls; unavailable auth/run is `INCOMPLETE`.

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

### Final cross-block integration and candidate (Task 53)

Task 53 cannot start until Blocks A–D are approved. Its reviewer is fresh to the final
candidate and treats the block reviews as evidence, not as a substitute for checking the
integrated system. The final review covers Spec 010 traceability, cross-block contracts,
authority and evidence flows, hard-renamed surfaces and removed aliases/homes, installed
wheel behavior, CI/readiness/provenance, exact budget closure, and exact-HEAD receipts.

53. **Final candidate: exact ceiling, record transition, and dogfood refresh** — **file** `specs/010-governed-agentic-engineering-foundation/spec.md`; **same atomic transaction also changes** `specs/004-solution-intent-home/spec.md`, `.ai/intent.md`, `src/ai_engineering/contract.py`, `tests/test_readiness.py`, and `tests/test_contracts.py`.
    **check**: `uv run --with pytest==9.1.1 --with 'rich>=13,<16' --with 'questionary>=2,<3' pytest -q tests/test_readiness.py::test_spec_010_004_intent_and_ceiling_transition_atomically`.
    **rollback**: `git revert <commit>`.
   **done when**: the last local candidate commit counts the final tree including its own readiness test and record changes, sets `REPO_CEILING` and its comment/assertion to that exact count with zero slack, sets spec010's final status and eight evidence records, supersedes spec004, and refreshes `.ai/intent.md` with the current spec010 digest, current lifecycle facts, no invented authority, and product-validator `PASS`; the focused check proves only those static local finalization invariants and has no live-receipt dependency, so the candidate must pass local `just check` before push and the same suite in CI. The transition is accepted as done/shipped only when those static gates and, after separate push consent, the separate shell/readiness proof of exact own-HEAD check/install receipts both pass. Any missing authentication, live receipt, or gate is `INCOMPLETE` and the candidate is reverted before any shipped declaration, tag, or publication. No release receipt or publishing authority is implied. This final task is last.

## Deliberate omissions and deferred waves

- **P1 surfaces:** implementation waits for exact landed P0 Intent, MADR, capability, outcome, and evidence versions. Preserve foreign config bytes and report discovery/invocation/enforcement separately. OpenCode currently checks only `status===2`; `null` from spawn failure/timeout can pass. Add installed-artifact negative tests and fail closed in P1; `pi` and `zed` remain T3/`UNPROVEN`. No OpenCode edit is P0.
- **P2 craft/reporting:** accessibility polish, animation, image/import governance, restored specialist skills, and public `report issue` remain P2. P0 only implements local `report digest` and refuses issue/public submission.
- **P3 coordination:** no councils, leases, takeover, parallel writers, or merge groups until a separately approved compare-and-swap/race-proof plan. One writer remains mandatory.
- **P4 scanners/release:** native detectors, SARIF, SBOM/attestation, and tamper fixtures require a separate approved plan; P0 retains current lanes and verifies provenance contracts only.
- **P5 pilots:** external upgrades, human/no-human comparisons, measured pilots, model scores, URLs, deployment, and compliance claims require P0–P4 proof and consent.
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
