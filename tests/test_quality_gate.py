from __future__ import annotations

import hashlib
import io
import json
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
        "ee7b8e1a10b1c9da9a6810b0711c4d653af5348e80c3e46bfb1d265dd5838b5d"
    )
    acceptance_step = _named_step(
        lines, "acceptance publication comes only from the installed wheel"
    )
    assert _raw_digest(acceptance_step) == (
        "7196bcf318d43219fc4dc8cbf5e1ecc55a57657dddd338198599249a6f87f0e3"
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
    for lane in ("check", "suite", "mutation", "typecheck", "sonar", "snyk"):
        assert f"{lane}=${{{{ needs.{lane}.result }}}}" in text, lane
    assert "needs: [check, suite, mutation, typecheck, sonar, snyk]" in text
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
        ("needs: [check, suite, mutation, typecheck, sonar, snyk]", ""),
        ("evidence: ${{ steps.scan.outputs.evidence || 'unavailable' }}", ""),
        ("check=${{ needs.check.result }}", ""),
        ("test -s coverage.xml", ""),
        ("re-home the branch to this repository to get the evidence.", ""),
        # The one that cannot be tested by deletion: waiving a lane is something added.
        ("    name: CI Result", "    name: CI Result\n    continue-on-error: true"),
        # And the fork branch turning back into a warning that falls through to green.
        (
            '            exit 1\n          fi\n          echo "six jobs',
            '            fi\n          echo "six jobs',
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

    # Unchanged, byte for byte. A task that extends a matrix must not edit what it extends.
    assert _raw_digest(
        _named_step(lines, "native transaction comes only from the installed wheel")
    ) == ("ee7b8e1a10b1c9da9a6810b0711c4d653af5348e80c3e46bfb1d265dd5838b5d")
    assert (
        _raw_digest(
            _named_step(lines, "acceptance publication comes only from the installed wheel")
        )
        == "7196bcf318d43219fc4dc8cbf5e1ecc55a57657dddd338198599249a6f87f0e3"
    )

    surface = _named_step(lines, "the ten verbs, the hard renames and one JSON object")
    assert _raw_digest(surface) == (
        "9e769bc187bf61da8409f59016ead282da9642099a9ab87f44a2a6bdf41c7597"
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
    assert "design_gate" in body and "the old guard name survives" in body

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
        "ai_engineering/hooks/change_scope_guard.py",
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
PINNED_ENGINES = ("gitleaks", "trivy", "semgrep", "mypy")


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
    by this because it was never named."""

    workflow = _check_workflow()
    lines = workflow.splitlines()
    downloads = [index for index, line in enumerate(lines) if "curl -sSfL -o" in line]

    assert downloads, "the workflow downloads nothing, so this test proves nothing"
    for index in downloads:
        target = lines[index].split("-o", 1)[1].split()[0]
        following = lines[index + 1] if index + 1 < len(lines) else ""
        assert "sha256sum -c" in following, (
            f"{target} is downloaded on line {index + 1} and its bytes are never checked"
        )
