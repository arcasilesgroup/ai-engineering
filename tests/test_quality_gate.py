from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path

import pytest
import quality_gate

ROOT = Path(__file__).resolve().parents[1]


def _child_block(lines: list[str], header: str) -> list[str]:
    """Return the strictly more-indented YAML lines below one exact header."""
    position = lines.index(header)
    indentation = len(header) - len(header.lstrip())
    block = []
    for line in lines[position + 1 :]:
        if line and len(line) - len(line.lstrip()) <= indentation:
            break
        block.append(line)
    return block


def _matrix_controls(lines: list[str], key: str) -> dict[str, tuple[str, ...]]:
    """The exact control names one matrix key selects, per operating system.

    The reader stops at the next key rather than running to the end of the row, because a
    row now carries two lists and a reader that swallowed both would report the union as
    each — which is the shape that lets a control be listed and never selected.
    """

    matrix = _child_block(lines, "      matrix:")
    included = _child_block(matrix, "        include:")
    rows: dict[str, tuple[str, ...]] = {}
    operating_system = ""
    controls: list[str] = []
    reading_controls = False

    def finish() -> None:
        if operating_system:
            assert operating_system not in rows
            rows[operating_system] = tuple(controls)

    for line in included:
        stripped = line.strip()
        if stripped.startswith("- os: "):
            finish()
            operating_system = stripped.removeprefix("- os: ")
            controls = []
            reading_controls = False
        elif stripped.endswith(":") or stripped.endswith(": >-") or ": " in stripped:
            # Any key ends the block, not only another folded one. A scalar key added after
            # a controls list would otherwise be read as one more control name.
            reading_controls = stripped == f"{key}: >-"
        elif reading_controls and stripped:
            controls.extend(stripped.split())
    finish()
    return rows


def _native_matrix(lines: list[str]) -> dict[str, tuple[str, ...]]:
    return _matrix_controls(lines, "native-controls")


def _named_step(lines: list[str], name: str) -> list[str]:
    return _child_block(lines, f"      - name: {name}")


def _raw_digest(lines: list[str]) -> str:
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def test_live_gate_is_resolved_from_the_project_before_its_conditions_are_read(monkeypatch):
    replies = iter(
        [
            {"qualityGate": {"id": 144658, "name": "the assigned gate"}},
            {"conditions": [{"metric": "new_coverage", "op": "LT", "error": "80"}]},
        ]
    )
    urls = []

    def answer(request, timeout):
        urls.append(request.full_url)
        return io.BytesIO(json.dumps(next(replies)).encode())

    monkeypatch.setattr(quality_gate.urllib.request, "urlopen", answer)
    assert quality_gate.live("group_project", "group", "secret") == {"new_coverage": ("LT", 80.0)}
    assert urls == [
        "https://sonarcloud.io/api/qualitygates/get_by_project?project=group_project&organization=group",
        "https://sonarcloud.io/api/qualitygates/show?id=144658&organization=group",
    ]


def _assert_install_matrix_contract(workflow: str) -> None:
    lines = workflow.splitlines()
    common = (
        "test_native_spec_transaction_is_locked_staged_noreplace_and_alias_safe",
        "test_native_publish_collision_preserves_foreign_final_and_owned_pending",
    )
    posix_alias = "test_posix_root_and_pending_aliases_are_never_write_targets"
    assert _native_matrix(lines) == {
        "ubuntu-latest": (*common, posix_alias),
        "macos-latest": (
            *common,
            posix_alias,
            "test_posix_walk_rejects_case_alias_spelling_when_filesystem_resolves_it",
        ),
        "windows-latest": (
            *common,
            "test_windows_publish_closes_child_consumes_pending_and_rejects_junction",
        ),
    }
    # The acceptance register, on the same three runners and by the same rule: what the
    # installed wheel does, not what the checkout can be made to do. Every runner takes the
    # portable controls; the symlink and hard-link ones are POSIX, and Windows takes the
    # junction control instead — so no runner is handed a control it can only skip.
    portable = (
        "test_risk_acceptance_v1_schema_is_closed_and_exact",
        "test_acceptance_corpus_covers_valid_adversarial_and_privacy_cases",
        "test_acceptance_pii_v1_is_deterministic_and_fails_closed",
        "test_acceptance_machine_path_v1_rejects_posix_windows_and_unc_paths",
        "test_gitleaks_gate_requires_exact_version_and_three_clean_results",
        "test_unified_reader_separates_integrity_from_binding_freshness",
        "test_unified_reader_reads_frozen_legacy_history_without_rewriting_it",
    )
    posix_only = (
        "test_unified_reader_refuses_rather_than_returning_a_partial_register",
        "test_the_register_refuses_every_way_it_was_shown_to_go_quiet",
    )
    chains = (
        "test_ordinals_and_renewal_chains_span_legacy_noncanonical_and_derived_ids",
        "test_id_less_legacy_blocks_receive_stable_derived_identities",
        "test_renewal_chains_refuse_forks_cycles_and_a_third_renewal",
        "test_the_expiry_view_judges_only_the_unique_head",
    )
    assert _matrix_controls(lines, "acceptance-controls") == {
        "ubuntu-latest": (*portable, *posix_only, *chains),
        "macos-latest": (*portable, *posix_only, *chains),
        "windows-latest": (
            *portable,
            *chains,
            "test_a_junction_under_specs_is_refused_rather_than_followed",
        ),
    }

    assert "    runs-on: ${{ matrix.os }}" in lines
    matrix = ["      matrix:", *_child_block(lines, "      matrix:")]
    assert _raw_digest(matrix) == "6e808fa55acc4ae554951b5aafe731f66d914d1f0cedff252020f56fccd8e7ff"

    # Task 39d's runner is pinned by digest so the acceptance work cannot quietly weaken it.
    native_step = _named_step(lines, "native transaction comes only from the installed wheel")
    assert _raw_digest(native_step) == (
        "b81028e7c88d58dd70c2148f572d913e3cfba4cde5754fb311e97f4704bafb98"
    )
    acceptance_step = _named_step(
        lines, "acceptance publication comes only from the installed wheel"
    )
    assert _raw_digest(acceptance_step) == (
        "71453f9c11662280b748a823e97d22b6f46815292bb04b8c5b1e4462aa75b458"
    )

    smoke = _child_block(lines, "  smoke:")
    aggregate = _child_block(lines, "  install-smoke:")
    for job in (smoke, aggregate):
        assert not any("continue-on-error:" in line for line in job)
    assert [line for line in smoke if line.strip().startswith("if:")] == [
        "        if: runner.os == 'Linux'"
    ]
    assert [line for line in aggregate if line.strip().startswith("if:")] == ["    if: always()"]

    aggregate_text = "\n".join(aggregate)
    assert "needs: [smoke]" in aggregate_text
    assert "RESULT: ${{ needs.smoke.result }}" in aggregate_text
    aggregate_step = _named_step(lines, "all three platforms, or none")
    aggregate_run = [
        line.strip() for line in _child_block(aggregate_step, "        run: |") if line.strip()
    ]
    assert aggregate_run == ['echo "smoke: $RESULT"', 'test "$RESULT" = "success"']


def test_install_matrix_executes_native_spec_transaction_on_every_supported_os():
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    _assert_install_matrix_contract(workflow)


def test_install_matrix_executes_the_hooks_template_on_every_supported_os():
    """D-024-01's deployable half. The wheel is the deployable artefact, and the install
    matrix is the only thing that runs a stranger's install on Linux, macOS and Windows in
    one job. The opt-in hooks template must be exercised there with assertions on its real
    effects — the template directory, the global key — inside the step every platform runs,
    not merely named beside it."""

    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    _assert_install_matrix_contract(workflow)
    lines = workflow.splitlines()
    step = _named_step(lines, "zero to a green doctor, in a repository it has never seen")
    block = "\n".join(step)
    # The exercise may not live in a step a single platform can skip: it sits inside the
    # step the matrix runs on every OS, and it asserts the real effects — the template
    # directory written by the installed wheel, and the global key pointing at it.
    assert "machine_config" in block or "hooks-template" in block
    assert "ai-eng init --hooks-template" in block
    assert "init.templateDir" in block
    assert block.index("ai-eng init --hooks-template") < block.index("ai-eng doctor || true")


def test_no_spanish_in_docs():
    """D-024-04: the record and the rule agree. The project is English-first for open
    source, and the two artifacts this decision owns — the hand-written `docs/tools.md`
    and the generator's own template — must not carry Spanish UI text. The rendered page
    also shows the operator's data (historical blocked rows, spec titles) which is not
    this generator's language and is deliberately preserved as history."""

    tools = (ROOT / "docs" / "tools.md").read_text(encoding="utf-8", errors="replace")
    generator = (ROOT / "src" / "ai_engineering" / "solution_intent.py").read_text(
        encoding="utf-8", errors="replace"
    )
    markers = ("Guía rápida", "Decisiones que atan", "De un vistazo", "cuatro cosas", "escribe")
    for name, body in (("tools.md", tools), ("solution_intent.py", generator)):
        hits = [marker for marker in markers if marker in body]
        assert not hits, f"{name} still carries Spanish UI text: {hits}"


def test_install_matrix_executes_acceptance_publication_on_every_supported_os():
    """Every acceptance control the wheel owes, on all three runners, from the wheel.

    The register decides whether a known risk may stay. Proving it against the checkout
    proves the checkout; what a stranger installs is the wheel, so the controls run against
    an isolated environment holding only that wheel, after its bytes are proved identical to
    the source they were built from. A skip is a failure, so a control that cannot run on a
    runner is not selected for it — it is replaced by one that can.
    """

    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    _assert_install_matrix_contract(workflow)
    lines = workflow.splitlines()
    step = _named_step(lines, "acceptance publication comes only from the installed wheel")
    body = "\n".join(step)

    # The wheel is the subject, and the schema and corpus that travel with the checkout are
    # proved identical to the ones it ships before a single control runs.
    for shipped in (
        "ai_engineering/acceptance.py",
        "ai_engineering/acceptance_privacy.py",
        "ai_engineering/accept.py",
        "ai_engineering/policy/risk-acceptance-v1.schema.json",
    ):
        assert shipped in body, shipped
    assert "built wheel differs from checkout" in body
    assert "installed acceptance register differs from the built wheel" in body
    assert "acceptance register imported from the checkout" in body
    assert "acceptance register is outside the isolated environment" in body

    # Missing input is INCOMPLETE, never an empty pass.
    assert "acceptance fixture is missing" in body
    assert "acceptance controls are missing" in body
    assert "expected exactly one wheel" in body

    # A skip is a failure: the runner counts them and every selected control must pass.
    assert "if report.skipped:" in body
    assert 'if hasattr(report, "wasxfail"):' in body
    assert "selected acceptance controls did not pass:" in body
    assert "set -euo pipefail" in body

    # And it grants nothing: no push, tag, release or install outside its own environment.
    for forbidden in ("gh ", "git push", "git tag", "twine", "uv publish"):
        assert forbidden not in body, forbidden


@pytest.mark.parametrize(
    "bypass",
    ["exit 0", "return 0", "set +e", "trap 'exit 0' EXIT"],
)
def test_install_matrix_contract_rejects_early_success_after_strict_shell(bypass):
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    mutated = workflow.replace(
        "          set -euo pipefail\n",
        f"          set -euo pipefail\n          {bypass}\n",
        1,
    )
    assert mutated != workflow
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


@pytest.mark.parametrize(
    ("original", "neutralized"),
    [
        ("          import os\n", "          import os\n          raise SystemExit(0)\n"),
        (
            '          print(f"installed native transaction: {module}")',
            "          sys.exit(0)",
        ),
        (
            '          print(f"installed native transaction: {module}")',
            "          os._exit(0)",
        ),
    ],
)
def test_install_matrix_contract_rejects_early_success_inside_native_runner(original, neutralized):
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    mutated = workflow.replace(original, neutralized, 1)
    assert mutated != workflow
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


@pytest.mark.parametrize(
    ("original", "neutralized"),
    [
        (
            "if source.read_bytes() != packaged:",
            "if source.read_bytes() == packaged:",
        ),
        (
            'if hasattr(report, "wasxfail"):',
            "if False:",
        ),
    ],
)
def test_install_matrix_contract_rejects_provenance_and_xfail_neutralization(original, neutralized):
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    mutated = workflow.replace(original, neutralized, 1)
    assert mutated != workflow
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


def test_install_matrix_contract_rejects_outcome_observer_neutralization():
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    mutated = workflow.replace(
        "                      self.rejected.append(report.nodeid)\n"
        '                  if hasattr(report, "wasxfail"):',
        "                      self.rejected.append(report.nodeid)\n"
        "                  self.rejected.clear()\n"
        '                  if hasattr(report, "wasxfail"):',
        1,
    )
    assert mutated != workflow
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


def test_install_matrix_contract_rejects_smoke_job_soft_fail():
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    mutated = workflow.replace("  smoke:\n", "  smoke:\n    continue-on-error: true\n", 1)
    assert mutated != workflow
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


def test_install_matrix_contract_rejects_aggregate_job_soft_fail():
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    mutated = workflow.replace(
        "  install-smoke:\n",
        "  install-smoke:\n    continue-on-error: true\n",
        1,
    )
    assert mutated != workflow
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


@pytest.mark.parametrize("condition", ["    if: false\n", ""])
def test_install_matrix_contract_requires_exact_aggregate_always_condition(condition):
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    mutated = workflow.replace("    if: always()\n", condition, 1)
    assert mutated != workflow
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


@pytest.mark.parametrize(
    ("step", "control"),
    [
        ("build the wheel", "continue-on-error: true"),
        ("build the wheel", "if: false"),
        ("all three platforms, or none", "continue-on-error: true"),
        ("all three platforms, or none", "if: false"),
    ],
)
def test_install_matrix_contract_rejects_step_soft_fail_or_skip_across_jobs(step, control):
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    anchor = f"      - name: {step}\n"
    mutated = workflow.replace(anchor, f"{anchor}        {control}\n", 1)
    assert mutated != workflow
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


def test_install_matrix_contract_rejects_invalid_native_step_indentation():
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    lines = workflow.splitlines()
    header = "      - name: native transaction comes only from the installed wheel"
    start = lines.index(header) + 1
    finish = next(
        index
        for index in range(start, len(lines))
        if lines[index] and len(lines[index]) - len(lines[index].lstrip()) <= 6
    )
    for index in range(start, finish):
        if lines[index]:
            lines[index] = f"  {lines[index]}"
    mutated = "\n".join(lines) + "\n"
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


def test_install_matrix_contract_rejects_invalid_native_matrix_indentation():
    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    lines = workflow.splitlines()
    start = lines.index("        include:") + 1
    finish = lines.index("    runs-on: ${{ matrix.os }}", start)
    for index in range(start, finish):
        line = lines[index]
        if line.strip() == "native-controls: >-" or line.strip().startswith("test_"):
            lines[index] = f"  {line}"
    mutated = "\n".join(lines) + "\n"
    with pytest.raises(AssertionError):
        _assert_install_matrix_contract(mutated)


def _check_workflow() -> str:
    return (ROOT / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")


def _ci_result_contract(workflow: str) -> None:
    """Every assertion the check workflow has to satisfy, in one place.

    In one place because the mutation test below has to run these and not a copy of some
    of them: it held four re-typed assertions of its own, so the other eight could be
    deleted from the real contract and nothing noticed."""

    lines = workflow.splitlines()

    # The lanes the plan requires, still present and still needed by the aggregate.
    aggregate = _child_block(lines, "  ci-result:")
    text = "\n".join(aggregate)
    for lane in ("check", "suite", "guards", "typecheck", "platforms", "sonar", "snyk", "recap"):
        assert f"{lane}=${{{{ needs.{lane}.result }}}}" in text, lane
    assert "needs: [check, suite, guards, typecheck, platforms, sonar, snyk, recap]" in text
    assert "if: always()" in text

    # A skipped job is a failure, which is what makes a deleted or renamed lane visible.
    assert '[ "${pair##*=}" = "success" ] || failed=1' in text

    # And a lane that reported no evidence is INCOMPLETE rather than a silent pass —
    # everywhere, including a fork, where the absence is nobody's fault and blocks anyway.
    assert "SNYK_EVIDENCE: ${{ needs.snyk.outputs.evidence }}" in text
    assert 'if [ "${SNYK_EVIDENCE:-unavailable}" != "ran" ]; then' in text
    assert 'if [ "$FORK" = "true" ]; then' in text
    assert "CI Result INCOMPLETE" in text
    assert "re-home the branch to this repository to get the evidence." in text
    assert "SAST evidence is missing on a run that should have had it." in text
    assert text.count("exit 1") == 2

    # The job has to declare the output, or the aggregate reads an empty string forever and
    # the branch above can never fire.
    snyk = "\n".join(_child_block(lines, "  snyk:"))
    assert "evidence: ${{ steps.scan.outputs.evidence || 'unavailable' }}" in snyk
    assert 'echo "evidence=ran" >> "$GITHUB_OUTPUT"' in snyk
    assert 'echo "evidence=unavailable" >> "$GITHUB_OUTPUT"' in snyk

    # No lane may be waived by a flag that turns its failure into a pass.
    assert "continue-on-error" not in workflow

    # The coverage artifact still has to exist, or Sonar reports zero and calls it a pass.
    assert "test -s coverage.xml" in workflow


def test_check_workflow_marks_missing_or_skipped_evidence_incomplete():
    """Every lane still runs, and a lane that ran without observing anything says so.

    A job result is `success` when the job exited zero. It is `success` when the job's
    credentials were withheld and it scanned nothing, too — and that shape of green is the
    one this product exists to refuse. So the aggregate reads what a lane reports it
    observed, not only how it exited, and missing evidence is `INCOMPLETE` out loud.

    A fork pull request is the one case where the absence is nobody's fault and no code on
    the branch can cure it: GitHub withholds the secret. It is named separately and it
    still blocks, because the alternative is a pull request that merges on the strength of
    a scan nobody ran. The cure is to re-home the branch, not to lower the bar.
    """

    _ci_result_contract(_check_workflow())


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ('if [ "${SNYK_EVIDENCE:-unavailable}" != "ran" ]; then', ""),
        ("SNYK_EVIDENCE: ${{ needs.snyk.outputs.evidence }}", ""),
        ('echo "evidence=ran" >> "$GITHUB_OUTPUT"', ""),
        ('echo "evidence=unavailable" >> "$GITHUB_OUTPUT"', ""),
        ('[ "${pair##*=}" = "success" ] || failed=1', ""),
        ("needs: [check, suite, guards, typecheck, platforms, sonar, snyk, recap]", ""),
        ("evidence: ${{ steps.scan.outputs.evidence || 'unavailable' }}", ""),
        ("check=${{ needs.check.result }}", ""),
        ("platforms=${{ needs.platforms.result }}", ""),
        ("test -s coverage.xml", ""),
        ("re-home the branch to this repository to get the evidence.", ""),
        # The one that cannot be tested by deletion: waiving a lane is something added.
        ("    name: CI Result", "    name: CI Result\n    continue-on-error: true"),
        # And the fork branch turning back into a warning that falls through to green.
        (
            '            exit 1\n          fi\n          echo "$ran jobs',
            '            fi\n          echo "$ran jobs',
        ),
    ],
)
def test_check_workflow_contract_notices_a_removed_evidence_gate(before, after):
    """Each assertion in the contract must be load-bearing. A contract that still passes
    with its subject deleted is a contract that was reading something else."""

    mutated = _check_workflow().replace(before, after, 1)
    assert mutated != _check_workflow(), before
    with pytest.raises(AssertionError):
        _ci_result_contract(mutated)


def test_install_matrix_preserves_native_transaction_and_proves_head_wheel_renames_and_json():
    """The surface a stranger types, proved from the artifact they installed.

    Everything before this task proved a mechanism — a rename, a transaction, a register.
    This proves the thing a person actually meets: ten verbs, the old spellings gone, and
    one JSON object with an empty stderr. From the wheel, because the checkout can be made
    to say anything and is not what anybody installs.

    It is also the first place the earlier runners could have been quietly weakened, so both
    are pinned by digest and this test fails if either moves by a byte.
    """

    workflow = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    _assert_install_matrix_contract(workflow)
    lines = workflow.splitlines()

    # Both moved, once, and for a reason that was never about the matrix: actionlint had
    # never run on this file — `just check` failed earlier in the recipe every time, so the
    # step after it never executed — and its first run reported SC2086 on the two lines that
    # word-split a variable into arguments on purpose. The splitting is wanted; `read -ra`
    # says so, and a suppression would have said nothing. Two pins that read "unchanged,
    # byte for byte" moving in one commit is exactly what these pins are for: the edit is
    # visible, and this comment is the review it forces.
    assert _raw_digest(
        _named_step(lines, "native transaction comes only from the installed wheel")
    ) == ("b81028e7c88d58dd70c2148f572d913e3cfba4cde5754fb311e97f4704bafb98")
    assert (
        _raw_digest(
            _named_step(lines, "acceptance publication comes only from the installed wheel")
        )
        == "71453f9c11662280b748a823e97d22b6f46815292bb04b8c5b1e4462aa75b458"
    )

    # This one has moved twice, and each move carries its reason rather than a new number.
    #
    # First: the step counted verbs with a regex that required each description to start with
    # a capital letter; two of the ten open with their own subcommands, so it counted eight
    # and failed a wheel that was right — on all three operating systems, the first time that
    # branch ever reached CI.
    #
    # Second: `ai-eng decide --help | grep -q -- --madr` required a flag that was deleted
    # with the half of the verb that wrote into the specification. The line is now the shape
    # the two hard renames beside it already use — the old spelling must refuse — and `--why`
    # is asked the same way. This is the line that caught the deletion, and it could only be
    # caught here: `install-matrix.yml` is not part of `just check`, so the local gate never
    # sees the surface a stranger installs.
    #
    # The pin is what made both edits a reviewable act instead of a quiet one, which is the
    # whole reason it is here.
    surface = _named_step(lines, "the ten verbs, the hard renames and one JSON object")
    assert _raw_digest(surface) == (
        "57f38b8117fb7e96f73343cc44a2ed4f816896c777f24c6bc7efa99aaec0c6a4"
    )
    body = "\n".join(surface)

    # The inventory, and its size, so a verb added or lost is visible rather than implied.
    for verb in (
        "init",
        "doctor",
        "update",
        "spec",
        "decide",
        "accept",
        "audit",
        "report",
        "exception",
        "uninstall",
    ):
        assert verb in body, verb
    assert 'test "$listed" = "10"' in body

    # Every hard rename, proved from the side that matters: the old spelling must refuse.
    for gone in ("ai-eng plan --skip x", "ai-eng digest", "ai-eng decide --adr x"):
        assert f"! {gone}" in body, gone
    # The tombstone list, not one name: `design_gate` was renamed and the guard it was
    # renamed to has since been deleted, so what the wheel must prove is that no spelling of
    # a removed guard survives in it — and that the guards which remain are actually there,
    # which is the half a probe asking only about absence can never answer.
    for gone in ("design_gate", "change_scope_guard", "claim_scope_guard"):
        assert gone in body, gone
    assert "a deleted guard survives in the wheel" in body
    assert "the guards are not in the wheel" in body

    # One object, nothing on stderr, and it has to parse.
    assert "json mode wrote to stderr" in body
    assert "more than one line" in body
    assert "schema_version" in body

    # And the whole step fails closed: strict shell, no `|| true` on an assertion.
    assert "set -euo pipefail" in body


def test_release_workflow_retains_wheel_contents_provenance_and_head_sha_receipts():
    """What a release may claim, and what it may not.

    A tag can be pushed from any commit on any branch, including one nobody reviewed, and
    afterwards the only record is a version number. So the tagged commit must be one the
    default branch already contains, asked of git rather than trusted from whoever tagged.

    The wheel contents lane stays, and grows: every artifact this wave added has to be in
    the thing that ships, and every hard-renamed file has to be absent from it. A rename is
    only hard if the old file is gone from the artifact a stranger installs.

    And nothing here claims a release was observed. This workflow builds, proves and
    publishes; whether the world received it is a receipt somebody else has to fetch.
    """

    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    # The commit a tag names has to be one main already holds.
    assert "git merge-base --is-ancestor" in workflow
    assert "refs/remotes/origin/main" in workflow
    assert "fetch-depth: 0" in workflow
    assert "origin/main does not contain" in workflow

    # The tag and the package still have to agree, and the wheel still has to carry the
    # product rather than a subset of it.
    assert 'test "$tag" = "$pkg"' in workflow
    for shipped in (
        "ai_engineering/hooks/chain.py",
        "ai_engineering/policy/iocs.yml",
        "ai_engineering/git-hooks/pre-push",
        "ai_engineering/skills/ai-spec/SKILL.md",
        "ai_engineering/hooks/self_protect.py",
        "ai_engineering/policy/risk-acceptance-v1.schema.json",
        "ai_engineering/acceptance.py",
        "ai_engineering/acceptance_privacy.py",
    ):
        assert shipped in workflow, shipped
    assert "the wheel still carries a hard-renamed file" in workflow

    # Provenance is attested and the publish is a separate job, so a build cannot publish
    # itself by accident.
    assert "actions/attest-build-provenance" in workflow
    assert "pypa/gh-action-pypi-publish" in workflow
    assert "id-token: write" in workflow or "attestations: write" in workflow

    # And no lane claims an observed release. P0 verifies contracts; a receipt is fetched,
    # never asserted, and asserting one here would be the green nobody earned.
    for claimed in ("release verified", "published successfully", "receipt confirmed"):
        assert claimed not in workflow.lower(), claimed
    assert "continue-on-error" not in workflow


# Both sides of the gate, and the one place each of them says which engine it trusts. CI
# downloads an exact release; `just security` runs whatever is on the machine — and a
# scanner whose version we did not test is one whose answer we cannot read, in either
# direction: a local green from an older engine, or a local red CI cannot reproduce.
PINNED_ENGINES = ("gitleaks", "trivy", "semgrep", "mypy", "sm")


def _justfile() -> str:
    return (ROOT / "justfile").read_text(encoding="utf-8")


def _pins(body: str, pattern: str) -> dict[str, str]:
    import re

    return {name: version for name, version in re.findall(pattern, body)}


def test_the_two_sides_of_the_gate_pin_the_same_engine_versions():
    """EP-045. CI pins five engines and `just security` pinned one, so the two could drift
    apart silently — and the first anybody would know is a pull request that fails on a
    finding nobody can reproduce locally, or worse, passes locally on an engine that no
    longer looks for it."""

    import re

    recipe = _justfile()
    workflow = _check_workflow()

    declared = _pins(recipe, r'(\w+)_version := "([0-9][^"]*)"')
    declared["semgrep"] = re.search(r'semgrep := "semgrep==([^"]+)"', recipe).group(1)
    declared["mypy"] = re.search(r'mypy := "mypy==([^"]+)"', recipe).group(1)
    declared["sm"] = re.search(r'^sm := "([^"]+)"', recipe, re.M).group(1)
    in_ci = _pins(workflow, r"(\w+)_VERSION: \"([^\"]+)\"".replace("\\", ""))
    in_ci = {name.lower(): version for name, version in in_ci.items()}

    for engine in PINNED_ENGINES:
        assert engine in declared, f"`just security` does not pin {engine}"
        if engine in in_ci:
            assert declared[engine] == in_ci[engine], (
                f"{engine} is {declared[engine]} for `just` and {in_ci[engine]} in CI"
            )


def test_the_security_recipe_refuses_an_engine_it_did_not_pin():
    """The pin is only a pin if something reads it. Each engine is asked its version before
    it is trusted, and the recipe stops rather than reporting what an untested scanner
    happened to say."""

    recipe = _justfile()
    security = recipe.split("\nsecurity:", 1)[1].split("\n\n", 1)[0]

    for engine in ("gitleaks", "trivy"):
        assert f"{{{{{engine}_version}}}}" in security, f"{engine} runs unpinned"
    assert security.count("exit 1") >= 2, "a version mismatch does not stop the recipe"


def test_every_downloaded_engine_has_its_bytes_checked():
    """D-014-05. The version says which release we asked for; the checksum says the bytes we
    got are that release.

    actionlint was the only download whose bytes were checked, on a workflow that also pulls
    the two engines whose entire job is to find things — so a mirror, a cache or a
    compromised release could have handed either of them a binary that finds nothing, and
    the gate would have gone green having scanned with it.

    Read from the file rather than from a list here: a sixth download added later is caught
    by this because it was never named.

    Two spellings, because the rule is about the bytes and not about the coreutils. macOS
    runners have `shasum` and not `sha256sum`, so the `platforms` lane checks its download
    with `shasum -a 256 -c` — the same verification, from the tool that machine has. Both
    still have to sit on the line immediately after the download, which is what stops a
    check drifting away from the thing it checks."""

    checkers = ("sha256sum -c", "shasum -a 256 -c")
    workflow = _check_workflow()
    lines = workflow.splitlines()
    downloads = [index for index, line in enumerate(lines) if "curl -sSfL -o" in line]

    assert downloads, "the workflow downloads nothing, so this test proves nothing"
    for index in downloads:
        target = lines[index].split("-o", 1)[1].split()[0]
        following = lines[index + 1] if index + 1 < len(lines) else ""
        assert any(one in following for one in checkers), (
            f"{target} is downloaded on line {index + 1} and its bytes are never checked"
        )


def test_no_workflow_carries_an_expression_with_nothing_in_it():
    """A workflow that does not start is not a workflow that fails.

    Measured on 2026-08-16: a comment inside a `run:` block quoted the syntax of a GitHub
    expression, in a sentence explaining why the value beside it travels through the
    environment instead. The runner reads a `run:` block for expressions and does not care
    that this one is inside a `#`, so the file became invalid — and an invalid workflow does
    not produce a failing job. It produces a run with no jobs at all, named after the file,
    while every job it contains silently never happens. On a pull request that reads as one
    lane missing, which is the shape `CI Result` exists to catch and could not, because
    `CI Result` is one of the jobs that never ran.

    actionlint says this in one line and lives in CI, inside the very job that could not
    start. So the narrow half of it runs here too, in the suite, on every machine.
    """

    empty = re.compile(r"\$\{\{\s*\}\}")
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        body = path.read_text(encoding="utf-8")
        assert empty.search(body) is None, (
            f"{path.name} holds an expression with nothing inside it: the runner parses it "
            f"wherever it appears, including inside a comment, and refuses the whole file"
        )


# The recipes `just check` runs, and whether anything has ever shown each one saying
# no. Four are controlled by their own readers' fixtures: `test` is red fixtures end to end,
# `security` has one per INCOMPLETE code plus a tamper fixture, `register` mutates the
# register and asserts the refusal, and `counts` fired today when prose and the registry
# disagreed. Two are controlled below by planting a violation and running the real engine.
# Two are not, and the reason is recorded rather than left to be discovered.
GATE_CONTROLS = {
    "build": "a wheel that fails to build takes minutes to construct and proves the "
    "packaging tool works, not that this gate does",
    "lint": "executed below",
    "typecheck": "executed below",
    "test": "the suite is negative fixtures end to end",
    "cover": "a run under the floor needs a full coverage pass; the floor itself is "
    "asserted by tests/test_contracts.py",
    "security": "one fixture per INCOMPLETE code, plus the rules-tamper fixture",
    "sbom": "tests/test_sbom.py builds a wheel, hashes it, and asserts the document names "
    "that digest — plus the release job re-checks the same equality against what `uv build` "
    "wrote, so the recipe failing here and the release failing there are one fact",
    "register": "tests/test_pilot_register.py mutates the register and asserts each refusal",
    "skilleval": "tests/test_skill_eval.py mutates the corpus once per routing rule and "
    "asserts the harness refuses each one",
    "evals": "tests/test_evals_harness.py plants a defect pack whose graded key lives "
    "outside the tree, asserts recall/precision over the three tiers, a clean control "
    "staying quiet, and an in-tree key being refused — one per B-029-1 rule",
    "counts": "test_the_counts_this_repository_states_about_itself_are_the_counts_it_has",
    "council": "test_council_counts_recomputes_and_refuses_a_total_it_cannot_reproduce "
    "plants four files the script must refuse — a total nine higher than the entries "
    "beneath it, a missing heading, a missing totals section and one total absent — and "
    "test_the_critic_step_refuses_every_declared_state_that_did_not_run plants the "
    "declared-section refusals: an empty heading that never said `none`, the template "
    "prompt under a declared round, a malformed or decorated `ran:` line and a grill "
    "question without its answer, because this recipe's whole value is refusing a "
    "number the run wrote about itself",
    "lenses": "tests/test_review_lenses.py plants the case the requirement is about — a "
    "stylesheet with no movement in it — and asserts it routes to frontend and not to motion, "
    "plus the inverse, plus a lens file with no row and a row with two rules",
    "intent-page": "tests/test_solution_intent.py is five refusals and one pass — a page "
    "somebody edited, a record that moved, a field rendered and not hashed, a number that "
    "disagrees with the gate that enforces it, and a tree git cannot list — because this "
    "recipe's whole value is the page it refuses to call fresh",
    "map": "tests/test_skill_map.py walks the tree and refuses a template hole nobody "
    "declared or a real target hidden behind one — the two failure modes the recipe's "
    "`sm scan` and `ai_engineering.skillmap` exist to catch",
    "ran": "and its second half prints the commits carrying no receipt, with a case holding "
    "the inversion that would have made that report exactly backwards — a present trailer "
    "splitting its own line. tests/test_ran_receipt.py is a table of unusable receipts and four "
    "named "
    "refusals — a file edited after the run, a file added after it, and two argument shapes "
    "— because this recipe's whole value is when it writes nothing",
}


def test_every_recipe_the_gate_runs_is_named_here_with_its_control_or_its_reason():
    """EP-060. The adversarial suite has a clean control for each of ten attacked guards.
    The eight recipes `just check` runs had none, and no reason was recorded for the gap —
    which is the half of the requirement that was never argued rather than never built.

    A control that only ever runs against input that passes has never been seen saying no,
    and this repository's whole position is that such a check is indistinguishable from one
    that cannot. Six of the eight are controlled; two carry a written reason, which rule 12
    is explicit is the honest answer when a judgement cannot fail closed cheaply."""

    recipes = (ROOT / "justfile").read_text(encoding="utf-8")
    line = next(one for one in recipes.splitlines() if one.startswith("check:"))
    ordered = line.removeprefix("check:").split()

    assert ordered, "the gate runs nothing, so this proves nothing"
    assert set(ordered) == set(GATE_CONTROLS), (
        f"the gate runs {sorted(set(ordered) ^ set(GATE_CONTROLS))} and this table does not: "
        f"a recipe added without a control or a reason is a check nobody has seen fail"
    )
    for name in ordered:
        assert GATE_CONTROLS[name].strip(), f"{name} carries neither a control nor a reason"

    # `EP-060` asks for a clean control in each gate recipe, and the honest half of that is
    # how many are arguments rather than controls. It was six controlled and two argued when
    # the requirement was measured; the table has grown since and nothing was counting, so
    # the ratio could have drifted the wrong way one recipe at a time. `lint` and `typecheck`
    # say "executed below" and mean it — the case under this one plants a defect and reads
    # each of them refusing — so `build` is the only recipe held by a reason alone.
    argued = [name for name, why in GATE_CONTROLS.items() if why == "executed below"]
    assert set(argued) == {"lint", "typecheck"}, (
        f"{argued} defer to a control below this case. Each one that does must be executed "
        "there, and the case that executes them names exactly these two"
    )
    reasons = [name for name in ordered if name == "build"]
    assert len(reasons) == 1
    assert len(ordered) - len(reasons) >= 12, (
        f"{len(reasons)} of {len(ordered)} recipes are held by a reason alone. That is "
        "allowed and it is the number worth watching: a gate whose recipes are mostly "
        "argued is a gate mostly nobody has seen refuse"
    )


def test_the_linter_and_the_type_checker_are_shown_saying_no(tmp_path):
    """The two controls that are cheap to execute, executed. Planted first and then found,
    which is the shape every scan in this repository owes: a run that finds nothing and a
    run that looked at nothing print the same result."""

    import subprocess

    planted = tmp_path / "planted.py"
    planted.write_text("import os\n\n\ndef f(x: int) -> str:\n    return x\n", encoding="utf-8")

    lint = subprocess.run(
        ["uv", "run", "--with", "ruff==0.16.2", "ruff", "check", str(planted)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert lint.returncode != 0, lint.stdout
    assert "F401" in lint.stdout, lint.stdout  # the unused import it was planted for

    types = subprocess.run(
        ["uv", "run", "--with", "mypy==2.3.0", "mypy", "--no-error-summary", str(planted)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert types.returncode != 0, types.stdout
    assert "return-value" in types.stdout, types.stdout


def test_no_child_of_the_mutation_runner_leaves_bytecode_behind() -> None:
    """Every half runs over a tree with one mutant in it, so a half that writes bytecode
    caches the mutant.

    Python decides a cached file is still good from the source's size and its modification
    time in whole seconds. A one-token flip is the same length — `==` for `!=`, `Exception`
    for `BaseException` — so a mutant written and taken out again inside the same second
    leaves a cache that validates against the restored original. Source correct, `git diff`
    empty, `digest()` in agreement, and the interpreter still running the mutant.

    It happened on 2026-08-20: `import chain` exited 0 out of a worktree git called clean,
    because the cached `if __name__ == "__main__"` had been flipped, and no test in the suite
    could run. A byte-identical clone was green, which is what proved the source innocent.

    Executed, not read. A half that imports one module is spent through `killer` exactly as a
    real half is, and this fails if a `.pyc` appears — so it survives any rewrite of how the
    environment is passed, and fails the moment somebody stops passing it.
    """

    import tempfile

    import mutation

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "shaped_like_a_mutant.py").write_text("VALUE = 1\n", encoding="utf-8")
        half, line = mutation.killer(
            (
                (
                    "one import",
                    ("-c", f"import sys; sys.path.insert(0, {tmp!r}); import shaped_like_a_mutant"),
                ),
            )
        )
        assert half == "", f"the half meant to pass went red on {line}"
        assert not list(Path(tmp).rglob("*.pyc")), (
            "a child of the mutation runner wrote bytecode. Over a mutated tree that cache "
            "outlives the restore and the interpreter goes on running the mutant, with git "
            "reporting a clean tree"
        )


def test_the_mutation_runner_spends_the_cheap_suite_first() -> None:
    """A mutant is killed when either half goes red, so the order of the two halves cannot
    change a verdict — only the bill. The adversarial run is thirteen seconds and pytest is
    over two minutes; running pytest first means every killed mutant pays the expensive half
    before the cheap one has had a chance to answer.

    Executed rather than read. This used to assert an AST shape — two `quiet` calls inside a
    `BoolOp` — and an AST shape is a thing a correct rewrite breaks while a wrong one can
    satisfy: the docstring had already promised this behaviour above a line that did the
    opposite, and then the shape assertion outlived the function it described. So the claim
    is run instead. Two fake halves, the first of which fails; if the runner spends the
    second, the marker exists and this fails.
    """

    import tempfile

    import mutation

    costs = [name for name, _ in mutation.HALVES]
    assert costs == ["guard tests", "adversarial", "the suite"], (
        f"the halves are no longer in cost order ({costs}), so a mutant the cheapest one "
        "settles pays a dearer one first"
    )

    with tempfile.TemporaryDirectory() as tmp:
        marker = Path(tmp) / "the-second-half-ran"
        half, line = mutation.killer(
            (
                ("first", ("-c", "import sys; sys.stderr.write('FAILED on purpose'); sys.exit(1)")),
                ("second", ("-c", f"open({str(marker)!r}, 'w').close()")),
            )
        )
        assert half == "first", half
        assert "FAILED on purpose" in line, line
        assert not marker.exists(), (
            "the expensive half ran after the cheap one had already said no, so the saving "
            "this order exists for is gone and nothing was red"
        )
