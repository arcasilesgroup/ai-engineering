"""Focused integration checks for the ten canonical CLI verb migrations."""

from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from ai_engineering import capability, cli, doctor, init, intent, outcome, skeletons, update, wiring

ROOT = Path(__file__).parents[1]
INTENT_FIXTURE = ROOT / "tests" / "fixtures" / "intent-v1.json"


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(home / ".ai-engineering"))
    return home


def _repository(tmp_path: Path, *, governed: bool = True) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, capture_output=True)
    if not governed:
        return root

    corpus = json.loads(INTENT_FIXTURE.read_text(encoding="utf-8"))
    materialized = deepcopy(corpus["base"])
    for file in materialized["repository"]["files"]:
        target = root / file["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file["content"], encoding="utf-8")
    assert skeletons.seed_intent(root, materialized["intent"]).outcome == "PASS"
    return root


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_init_writes_only_canonical_homes_and_receipt(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    sentinel = tmp_path / "outside-canonical-homes.txt"
    sentinel.write_bytes(b"foreign sentinel stays byte-identical\n")
    foreign = {
        "AGENTS.md": b"user-owned agents\n",
        "CONSTITUTION.md": b"user-owned constitution\n",
        "justfile": b"user-owned recipe:\n\t@true\n",
    }
    for name, body in foreign.items():
        (root / name).write_bytes(body)
    intent_bytes = (root / ".ai" / "intent.md").read_bytes()

    observed: list[str] = []
    real_capability_validate = capability.validate
    real_intent_validate = intent.validate

    def validate_capabilities():
        observed.append("capabilities")
        assert not (root / ".ai" / "config.toml").exists()
        return real_capability_validate()

    def validate_intent(source, repository):
        observed.append("intent")
        assert source == root / ".ai" / "intent.md"
        assert repository == root
        assert not (root / ".ai" / "config.toml").exists()
        return real_intent_validate(source, repository)

    def no_skill_preflight(*args, **kwargs):
        raise AssertionError("init invocation is its own bounded install authority")

    monkeypatch.setattr(capability, "validate", validate_capabilities)
    monkeypatch.setattr(intent, "validate", validate_intent)
    monkeypatch.setattr(capability, "preflight", no_skill_preflight)

    result = init.main(["--no-global", "--project", str(root), "-y"])

    assert type(result) is outcome.Result
    assert result.outcome == "WARN"
    assert observed == ["capabilities", "intent"]
    assert sentinel.read_bytes() == b"foreign sentinel stays byte-identical\n"
    assert (root / ".ai" / "intent.md").read_bytes() == intent_bytes
    for name, body in foreign.items():
        assert (root / name).read_bytes() == body

    expected_managed = {
        root / ".ai" / ".gitignore",
        root / ".ai" / "config.toml",
        root / ".github" / "workflows" / "check.yml",
        root / "CLAUDE.md",
        root / "justfile",
        root / "specs" / ".gitkeep",
    }
    assert init.managed_paths(root) == frozenset(expected_managed)

    receipt = wiring.receipt()
    project_rows = [row for row in receipt["wrote"] if row["kind"] == "project"]
    assert {Path(row["path"]) for row in project_rows} == expected_managed - {root / "justfile"}
    assert [row for row in receipt["wrote"] if row["kind"] == "repo"] == [
        {"path": str(root), "kind": "repo", "how": ""}
    ]
    assert Path(wiring.receipt_path()).is_relative_to(isolated_home)


@pytest.mark.parametrize("broken", ["missing", "invalid"])
def test_init_keeps_missing_or_invalid_intent_incomplete_after_bounded_install(
    tmp_path: Path,
    isolated_home: Path,
    broken: str,
) -> None:
    root = _repository(tmp_path, governed=False)
    if broken == "invalid":
        target = root / ".ai" / "intent.md"
        target.parent.mkdir()
        target.write_bytes(b'{"user_owned":"invalid and unchanged"}\n')
    sentinel = tmp_path / "outside-install-scope"
    sentinel.write_bytes(b"outside bytes\n")
    intent_before = (root / ".ai" / "intent.md").read_bytes() if broken == "invalid" else None

    result = init.main(["--no-global", "--project", str(root), "-y"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert sentinel.read_bytes() == b"outside bytes\n"
    if intent_before is not None:
        assert (root / ".ai" / "intent.md").read_bytes() == intent_before
    expected = set(init.managed_paths(root)) | {root / name for name in init.PROTECTED}
    assert all(path.is_file() for path in expected)
    project_rows = [row for row in wiring.receipt()["wrote"] if row["kind"] == "project"]
    assert {Path(row["path"]) for row in project_rows} == set(init.managed_paths(root))


def test_init_dry_run_is_exact_and_root_symlinks_fail_closed(
    tmp_path: Path,
    isolated_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repository(tmp_path)
    before = _snapshot(root)

    preview = init.main(["--no-global", "--project", str(root), "--dry-run", "-y"])

    assert type(preview) is outcome.Result
    assert preview.outcome == "WOULD_CHANGE"
    after = _snapshot(root)
    assert after == before
    assert not wiring.receipt_path().exists()
    rendered = capsys.readouterr().err
    for planned in (*init.managed_paths(root), root / "AGENTS.md", root / "CONSTITUTION.md"):
        assert planned.name in rendered

    alias = tmp_path / "repository-alias"
    alias.symlink_to(root, target_is_directory=True)
    refused = init.main(["--no-global", "--project", str(alias), "-y"])
    assert type(refused) is outcome.Result
    assert refused.outcome == "INCOMPLETE"
    assert _snapshot(root) == before


def test_init_invalid_capability_declaration_blocks_skill_install(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = tmp_path / "outside-skill-policy"
    sentinel.write_bytes(b"foreign\n")

    monkeypatch.setattr(
        capability,
        "validate",
        lambda: intent.Validation(
            "INCOMPLETE", "CAPABILITY_MANIFEST_INVALID", "capability manifest is invalid"
        ),
    )

    def no_install(*args, **kwargs):
        raise AssertionError("invalid declarations must stop before skill installation")

    monkeypatch.setattr(wiring, "install_skills", no_install)
    result = init.main(["--global", "--no-project", "-y"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert sentinel.read_bytes() == b"foreign\n"
    assert not (isolated_home / ".ai-engineering").exists()


def test_init_malformed_receipt_and_path_collision_fail_before_project_writes(
    tmp_path: Path,
    isolated_home: Path,
) -> None:
    root = _repository(tmp_path)
    receipt = wiring.receipt_path()
    receipt.parent.mkdir(parents=True)
    current_partial = json.dumps(
        {"version": init.__version__, "wrote": [{"path": "x", "kind": "project"}]}
    ).encode()
    for malformed_bytes in (b'{"partial":', b"[]", current_partial):
        receipt.write_bytes(malformed_bytes)
        before = _snapshot(root)
        malformed = init.main(["--no-global", "--project", str(root), "-y"])
        assert malformed.outcome == "INCOMPLETE"
        assert _snapshot(root) == before
        assert receipt.read_bytes() == malformed_bytes
        receipt.unlink()

    collision = root / "AGENTS.md"
    collision.mkdir()
    before = _snapshot(root)
    refused = init.main(["--no-global", "--project", str(root), "-y"])
    assert refused.outcome == "INCOMPLETE"
    assert _snapshot(root) == before
    assert collision.is_dir()


def test_doctor_migration_reports_all_contract_states(
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unknown(root):
        raise doctor.Undecidable("the check could not decide")

    def unreadable(root):
        raise wiring.Unreadable("foreign state could not be read")

    cases = (
        (
            "PASS",
            [(1, "The context", "passing assertion", True, lambda root: None)],
            [
                "  PIN  wheel = pinned  OK",
                "  T3   stub             ADVISES   instructions cannot deny",
            ],
        ),
        (
            "WARN",
            [(1, "The context", "bounded warning assertion", True, lambda root: None)],
            ["  T2   stub             UNPROVEN  no denial has executed here"],
        ),
        (
            "FAIL",
            [(2, "The wiring", "conclusive assertion", True, lambda root: "violation ran")],
            ["  PIN  wheel = pinned  OK"],
        ),
        (
            "INCOMPLETE",
            [
                (3, "The controls", "unknown assertion", True, unknown),
                (4, "The controls", "unreadable assertion", True, unreadable),
            ],
            ["  PIN  wheel = pinned  OK"],
        ),
    )
    monkeypatch.setattr(doctor.paths, "repo_root", lambda start=None: None)
    panel_titles = {
        "PASS": "OK",
        "WARN": "WARN",
        "FAIL": "FAILED",
        "INCOMPLETE": "INCOMPLETE",
    }
    for expected, checks, coverage in cases:
        monkeypatch.setattr(doctor, "CHECKS", checks)
        monkeypatch.setattr(doctor, "coverage", lambda root, lines=coverage: lines)

        result = doctor.main([])

        assert type(result) is outcome.Result
        assert result.outcome == expected
        rendered = capsys.readouterr().out
        assert f"╭─ {panel_titles[expected]} ─" in rendered
        if expected != "PASS":
            assert "╭─ OK ─" not in rendered
        assert all(line in rendered for line in coverage)
        for _, _, title, _, _ in checks:
            assert title in rendered
        if expected == "FAIL":
            assert "violation ran" in rendered
            assert doctor.FIXES[2] in rendered
        if expected == "INCOMPLETE":
            assert "the check could not decide" in rendered
            assert "foreign state could not be read" in rendered

    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [(1, "The context", "coverage boundary assertion", True, lambda root: None)],
    )

    def unreadable_coverage(root):
        raise wiring.Unreadable("coverage state could not be read")

    monkeypatch.setattr(doctor, "coverage", unreadable_coverage)
    unavailable = doctor.main([])
    assert type(unavailable) is outcome.Result
    assert unavailable.outcome == "INCOMPLETE"
    unavailable_output = capsys.readouterr().out
    assert "coverage state could not be read" in unavailable_output
    assert "╭─ INCOMPLETE ─" in unavailable_output
    assert "╭─ OK ─" not in unavailable_output

    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [(1, "The context", "captured child assertion", True, lambda root: None)],
    )
    monkeypatch.setattr(
        doctor,
        "coverage",
        lambda root: ["  T2   stub             UNPROVEN  no denial has executed here"],
    )
    assert cli.main(["--json", "doctor"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["outcome"] == "WARN"
    assert captured.out.count("\n") == 1
    assert "captured child assertion" not in captured.out
    assert captured.err == ""


def test_update_is_explicit_non_auto_and_returns_outcome(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repository(tmp_path)
    pin = root / ".ai" / "config.toml"
    pin.write_text(skeletons.CONFIG_TOML.format(version=update.__version__), encoding="utf-8")
    foreign = root / "justfile"
    foreign.write_bytes(b"foreign committed recipe:\n\t@true\n")
    sentinel = tmp_path / "outside-update-scope"
    sentinel.write_bytes(b"foreign sentinel\n")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Task32",
            "-c",
            "user.email=task32@example.invalid",
            "commit",
            "-m",
            "governed fixture",
        ],
        check=True,
        capture_output=True,
    )
    monkeypatch.chdir(root)
    monkeypatch.setattr(update, "migrations", lambda pinned, target: [])
    before = pin.read_bytes()

    class Input:
        def __init__(self, terminal: bool):
            self.terminal = terminal

        def isatty(self) -> bool:
            return self.terminal

    monkeypatch.setattr(update.sys, "stdin", Input(False))
    unattended = update.main(["--to", "9.9.9"])
    assert type(unattended) is outcome.Result
    assert unattended.outcome == "INCOMPLETE"
    assert pin.read_bytes() == before

    monkeypatch.setattr(update.sys, "stdin", Input(True))
    monkeypatch.setattr("builtins.input", lambda _: "n")
    declined = update.main(["--to", "9.9.9"])
    assert type(declined) is outcome.Result
    assert declined.outcome == "CANCELLED"
    assert pin.read_bytes() == before
    capsys.readouterr()

    def no_prompt(_: str) -> str:
        raise AssertionError("an explicit dry run must never prompt")

    monkeypatch.setattr("builtins.input", no_prompt)
    preview = update.main(["--to", "9.9.9", "--dry-run"])
    assert type(preview) is outcome.Result
    assert preview.outcome == "WOULD_CHANGE"
    assert pin.read_bytes() == before
    preview_output = capsys.readouterr().out
    assert f"{update.__version__} → 9.9.9" in preview_output
    assert ".ai/config.toml" in preview_output
    assert "0 migration(s)" in preview_output
    assert "no guard entry of ours is recorded" in preview_output

    opaque_step = Path("migrations/legacy..current/opaque.py")
    monkeypatch.setattr(update, "migrations", lambda pinned, target: [opaque_step])
    unbounded_preview = update.main(["--to", "9.9.9", "--dry-run"])
    assert type(unbounded_preview) is outcome.Result
    assert unbounded_preview.outcome == "INCOMPLETE"
    assert pin.read_bytes() == before
    monkeypatch.setattr(update, "migrations", lambda pinned, target: [])

    real_run = update.subprocess.run

    def status_cannot_decide(command, **kwargs):
        if command[:4] == ["git", "-C", str(root), "status"]:
            return subprocess.CompletedProcess(command, 128, "", "git status failed")
        return real_run(command, **kwargs)

    monkeypatch.setattr(update.subprocess, "run", status_cannot_decide)
    undecidable = update.main(["--to", "9.9.9", "--dry-run"])
    assert type(undecidable) is outcome.Result
    assert undecidable.outcome == "INCOMPLETE"
    assert pin.read_bytes() == before
    monkeypatch.setattr(update.subprocess, "run", real_run)

    monkeypatch.setattr("builtins.input", lambda _: "Y ")
    changed = update.main(["--to", "9.9.9"])
    assert type(changed) is outcome.Result
    assert changed.outcome == "PASS"
    assert 'version = "9.9.9"' in pin.read_text(encoding="utf-8")
    assert foreign.read_bytes() == b"foreign committed recipe:\n\t@true\n"
    assert sentinel.read_bytes() == b"foreign sentinel\n"
