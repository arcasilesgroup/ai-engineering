"""Unit tests for deterministic release-readiness verdicts."""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.release.readiness import evaluate_release_readiness
from ai_engineering.verify.scoring import FindingSeverity, SpecialistResult, VerifyScore


class _Runner:
    def __init__(self, *, fail: str | None = None) -> None:
        self.fail = fail
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[bool, str]:
        del cwd, timeout
        self.calls.append(cmd)
        cmd_text = " ".join(cmd)
        if self.fail and self.fail in cmd_text:
            return False, f"{self.fail} failed"
        return True, f"{cmd_text} passed"


def _seed_release_project(root: Path, *, changelog: bool = True) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname="demo"\nversion="0.4.0"\n',
        encoding="utf-8",
    )
    if changelog:
        (root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [Unreleased]\n\n- ready\n", encoding="utf-8"
        )


def _platform_score(*findings: tuple[FindingSeverity, str, str, str]) -> VerifyScore:
    score = VerifyScore(mode="platform")
    specialists: dict[str, SpecialistResult] = {}
    for severity, specialist_name, category, message in findings:
        specialist = specialists.setdefault(
            specialist_name,
            SpecialistResult(name=specialist_name, label=specialist_name.title(), runner="fake"),
        )
        specialist.add(severity, category, message)
    for specialist in specialists.values():
        score.include_specialist(specialist)
    return score


def test_release_readiness_go_when_every_dimension_passes(tmp_path: Path, monkeypatch) -> None:
    _seed_release_project(tmp_path)
    monkeypatch.setattr(
        "ai_engineering.release.readiness.verify_platform", lambda _root: _platform_score()
    )

    report = evaluate_release_readiness(tmp_path, "0.5.0", command_runner=_Runner())

    payload = report.to_dict()
    assert payload["verdict"] == "GO"
    assert payload["conditions"] == []
    assert payload["dimensions"]["security"]["status"] == "PASS"
    assert payload["dimensions"]["tests"]["status"] == "PASS"
    assert payload["dimensions"]["packaging"]["status"] == "PASS"
    assert Path(str(payload["artifact_path"])).is_file()
    json.loads(Path(str(payload["artifact_path"])).read_text(encoding="utf-8"))


def test_release_readiness_no_go_for_blocker_or_critical_security(
    tmp_path: Path, monkeypatch
) -> None:
    _seed_release_project(tmp_path)
    monkeypatch.setattr(
        "ai_engineering.release.readiness.verify_platform",
        lambda _root: _platform_score(
            (FindingSeverity.CRITICAL, "security", "dependency", "CVE blocks release")
        ),
    )

    report = evaluate_release_readiness(tmp_path, "0.5.0", command_runner=_Runner())

    assert report.verdict == "NO-GO"
    assert report.to_dict()["dimensions"]["security"]["status"] == "FAIL"


def test_release_readiness_no_go_for_failed_tests_package_or_missing_changelog(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "ai_engineering.release.readiness.verify_platform", lambda _root: _platform_score()
    )

    tests_project = tmp_path / "tests"
    tests_project.mkdir()
    _seed_release_project(tests_project)
    test_report = evaluate_release_readiness(
        tests_project, "0.5.0", command_runner=_Runner(fail="pytest")
    )
    assert test_report.verdict == "NO-GO"
    assert test_report.to_dict()["dimensions"]["tests"]["status"] == "FAIL"

    package_project = tmp_path / "package"
    package_project.mkdir()
    _seed_release_project(package_project)
    package_report = evaluate_release_readiness(
        package_project, "0.5.0", command_runner=_Runner(fail="build")
    )
    assert package_report.verdict == "NO-GO"
    assert package_report.to_dict()["dimensions"]["packaging"]["status"] == "FAIL"

    changelog_project = tmp_path / "changelog"
    changelog_project.mkdir()
    _seed_release_project(changelog_project, changelog=False)
    docs_report = evaluate_release_readiness(changelog_project, "0.5.0", command_runner=_Runner())
    assert docs_report.verdict == "NO-GO"
    assert docs_report.to_dict()["dimensions"]["docs"]["status"] == "FAIL"


def test_release_readiness_conditional_go_for_accepted_or_advisory_findings(
    tmp_path: Path, monkeypatch
) -> None:
    _seed_release_project(tmp_path)
    monkeypatch.setattr(
        "ai_engineering.release.readiness.verify_platform",
        lambda _root: _platform_score(
            (
                FindingSeverity.INFO,
                "security",
                "dependency",
                "accepted via D-143-09: advisory CVE until upstream patch",
            ),
            (FindingSeverity.MINOR, "quality", "lint", "advisory lint drift"),
        ),
    )

    report = evaluate_release_readiness(tmp_path, "0.5.0", command_runner=_Runner())

    payload = report.to_dict()
    assert payload["verdict"] == "CONDITIONAL GO"
    assert any("D-143-09" in condition for condition in payload["conditions"])
    assert payload["dimensions"]["security"]["status"] == "CONDITIONAL"
