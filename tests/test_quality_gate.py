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


def _native_matrix(lines: list[str]) -> dict[str, tuple[str, ...]]:
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
        elif stripped == "native-controls: >-":
            reading_controls = True
        elif reading_controls and stripped:
            controls.extend(stripped.split())
    finish()
    return rows


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
    assert "    runs-on: ${{ matrix.os }}" in lines
    matrix = ["      matrix:", *_child_block(lines, "      matrix:")]
    assert _raw_digest(matrix) == "24b4fef0b01e5143ceee6d56a702014cebe3e00683ef458d452414a75bee73a5"

    native_step = _named_step(lines, "native transaction comes only from the installed wheel")
    assert _raw_digest(native_step) == (
        "ee7b8e1a10b1c9da9a6810b0711c4d653af5348e80c3e46bfb1d265dd5838b5d"
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
