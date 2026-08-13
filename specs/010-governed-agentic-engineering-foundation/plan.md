# Plan: governed agentic engineering foundation — P0 atomic execution

## Approval and atomicity gate

No further implementation starts until a human explicitly approves **this exact `spec.md` and this exact `plan.md`**, explicitly including the SHA-256 digest of each file; any edit to either digest invalidates approval and requires re-approval. Tasks 1–9 are committed history implemented under the previous exact approval. That approved plan digest, `0bb0c7f2424a74a7bef22f128f2b29fac4f6752a487aa99196316cc26c0f5579`, is invalidated by the observed Task 9 dependency and budget facts: the committed repository tree now measures 21,188 lines, leaving only 1,119 of the provisional ceiling for 44 remaining implementation tasks, and finalizing spec010 would stale the dogfood `.ai/intent.md`. No Task 10 or later implementation may start until a human approves the new exact plan digest. The reply is the gate; no `approval.md` is created. There is exactly one repository writer before P3. Every implementation and every review is delegated; writers run sequentially, and a fresh read-only reviewer reviews each diff. No global initialization, installation, network mutation, publishing, tagging, or deployment runs without separate explicit consent. Each task is one atomic commit. A task may change exactly **one primary production, policy, documentation, or workflow file**, plus only its focused supporting test/fixture file(s); it may not change a second product home. Revisiting a primary file is allowed only for a named, distinct semantic change and a distinct commit. The sole exception is the final transition: one semantic transaction updates primary spec010, its predecessor spec004, the dogfood `.ai/intent.md`, and `src/ai_engineering/contract.py`, plus their focused readiness and contract tests, to avoid either a stale record or an intermediate line ceiling; spec010 remains the named primary. Rollback for every task is `git revert <commit>`.

The checks for committed Tasks 1–9 are historical evidence. Every check for unstarted Tasks 10–53 is an exact future red check: run it with `uv`, using the named `path::node`; it is red now because the node/file is absent or its assertion fails, and becomes green only after that task. No broad `-k`, placeholder node, or invented green result is acceptable. P0 may verify release workflow/provenance contracts but cannot claim a release; spec 010 remains draft and boxes unticked until the final candidate proves its own exact-HEAD receipts. Remote checks select the current `HEAD` SHA and return `INCOMPLETE` when authentication or a run is unavailable. Publishing/tag authority is always a separate human decision.

Task 1 records a provisional maximum of **17,807 + 4,500 = 22,307 lines** in `contract.py`. Exceeding 22,307 stops work and requires an approved re-plan; it is not permission to raise the ceiling. The final candidate transaction measures the committed tree and removes slack.

The observed first nine tasks added 3,381 lines, or about 376 lines per task. Applying that observed rate to the 44 remaining implementation tasks forecasts 16,544 more lines. Task 10 therefore re-plans the P0 maximum to **17,807 + 20,000 = 37,807 lines**. Exceeding 37,807 is still a hard stop requiring another approved re-plan, never permission to raise the ceiling; the final candidate transaction still removes all slack.

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

After Tasks 10–52 and their reviews pass, Task 53 creates and reviews the last local candidate commit. Nothing says Task 53 runs after receipts: its own immutable candidate SHA is the subject the receipts must prove. Before any push, record that SHA and run Task 53's focused static check, `git diff --check`, `just check`, `uv run python tests/adversarial/run.py`, `just mutate`, and the exact static release-workflow check from Task 47. The focused test has no network or live-receipt dependency; its static invariants therefore run locally and inside the candidate's CI. Failure is `INCOMPLETE` and the candidate is reverted.

Only with separate push consent, push that unchanged candidate and capture its exact-HEAD check and installed-matrix receipts with:
```
sha=$(git rev-parse HEAD)
id=$(gh run list --repo arcasilesgroup/ai-engineering --workflow check.yml --commit "$sha" --limit 1 --json databaseId --jq '.[0].databaseId // ""'); test -n "$id"; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json headSha --jq '.headSha')" = "$sha"; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json status --jq '.status')" = completed; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json conclusion --jq '.conclusion')" = success
id=$(gh run list --repo arcasilesgroup/ai-engineering --workflow install-matrix.yml --commit "$sha" --limit 1 --json databaseId --jq '.[0].databaseId // ""'); test -n "$id"; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json headSha --jq '.headSha')" = "$sha"; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json status --jq '.status')" = completed; test "$(gh run view "$id" --repo arcasilesgroup/ai-engineering --json conclusion --jq '.conclusion')" = success
```
Each workflow must have exact `headSha == "$sha"`, `status == completed`, and `conclusion == success`; otherwise `INCOMPLETE`. Empty output or unavailable authentication is `INCOMPLETE`. Do not query release HEAD runs. These shell queries are the separate live readiness proof; they are not simulated by or prerequisites of the focused pytest node. Task 53 is done, and its shipped transition becomes an accepted claim, only when the static focused check, every local final command, candidate CI, and both live exact-HEAD workflow proofs pass. Any failure requires `git revert <candidate-commit>` before declaring shipped, tagging, or publishing. Release work is limited to local/static workflow/provenance checks; it does not require or claim an observed release receipt. Any later tag commit must be contained in `origin/main`, and tagging and publishing require separate explicit consent.
