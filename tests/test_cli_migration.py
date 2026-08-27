"""Focused integration checks for the ten canonical CLI verb migrations."""

from __future__ import annotations

import builtins
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from ai_engineering import (
    accept,
    acceptance,
    acceptance_privacy,
    audit,
    capability,
    cli,
    decide,
    doctor,
    init,
    intent,
    madr,
    outcome,
    paths,
    skeletons,
    spec,
    spec_transaction,
    uninstall,
    update,
    wiring,
)

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
    (root / ".ai").mkdir(mode=0o700)
    (root / ".ai" / "intent.md").write_bytes(
        (
            json.dumps(
                materialized["intent"],
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )
    return root


def _confirmed(monkeypatch: pytest.MonkeyPatch, *, scanner: object = None) -> None:
    """Stand in for the two boundaries a test process cannot own: the OS controlling
    terminal and the pinned secret scanner.

    Neither is assumed away. Every test that uses this first proves the real terminal
    boundary refuses without it, and the scanner is executed for real by the installed
    matrix on Linux, macOS and Windows.
    """

    monkeypatch.setattr(accept, "controlling_terminal_response", lambda expected: True)
    verdict = scanner or acceptance_privacy.CLEAN
    monkeypatch.setattr(accept.acceptance_privacy, "gitleaks_v1", lambda directory: verdict)


def _published(root: Path, slug: str) -> dict:
    found = sorted((root / "specs" / slug).glob("acceptance-r-*/record.json"))
    assert len(found) == 1, found
    return json.loads(found[0].read_text(encoding="utf-8"))


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _activate_intent(root: Path) -> dict:
    home = root / ".ai" / "intent.md"
    record = json.loads(home.read_bytes())
    record["lifecycle"] = {
        "status": "active",
        "transitions": [
            {
                "from": "draft",
                "to": "active",
                "changed_at": "2026-08-14T10:00:00Z",
                "authority_role": "repository maintainer",
                "approval_ref": "change-request-17",
            }
        ],
        "approval": {
            "authority_role": "repository maintainer",
            "approval_ref": "change-request-17",
            "approved_at": "2026-08-14T10:00:00Z",
        },
    }
    home.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert intent.validate(home, root).outcome == "PASS"
    return record


def _transitive_intent_graph(
    root: Path,
    *,
    depth: int = 1,
    malformed: bool = False,
) -> tuple[dict, list[Path]]:
    record = _activate_intent(root)
    relation = root / record["relations"][0]["path"]
    adrs = [root / "docs" / "adr" / f"{number:04d}-linked.md" for number in range(1, depth + 1)]
    first = adrs[0].relative_to(root).as_posix()
    declared = f"{first},,{first}" if malformed else first
    relation_bytes = (
        f'---\nid: "010"\nstatus: draft\nrelations: {declared}\n---\n\n# Governed foundation\n'
    ).encode()
    relation.write_bytes(relation_bytes)
    for index, target in enumerate(adrs):
        target.parent.mkdir(parents=True, exist_ok=True)
        linked = (
            f"relations: {adrs[index + 1].relative_to(root).as_posix()}\n"
            if index + 1 < len(adrs)
            else "relations: []\n"
        )
        target.write_text(
            f'---\nid: "{index + 1:04d}"\ntype: adr\nstatus: proposed\n{linked}---\n\n# Linked\n',
            encoding="utf-8",
        )
    record["relations"][0]["target_digest"] = f"sha256:{sha256(relation_bytes).hexdigest()}"
    (root / ".ai" / "intent.md").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return record, adrs


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
        monkeypatch.setattr(doctor, "coverage", lambda root, lines=coverage, **_: lines)

        result = doctor.main([])

        assert type(result) is outcome.Execution
        assert result.outcome == expected
        assert result.checks
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

    def unreadable_coverage(root, **_):
        raise wiring.Unreadable("coverage state could not be read")

    monkeypatch.setattr(doctor, "coverage", unreadable_coverage)
    unavailable = doctor.main([])
    assert type(unavailable) is outcome.Execution
    assert unavailable.outcome == "INCOMPLETE"
    assert any(fact.id == "coverage" for fact in unavailable.checks)
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
        lambda root, **_: ["  T2   stub             UNPROVEN  no denial has executed here"],
    )
    assert cli.main(["--json", "doctor"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["outcome"] == "WARN"
    assert captured.out.count("\n") == 1
    assert any(
        fact["summary"] == "captured child assertion" and fact["status"] == "PASS"
        for fact in payload["checks"]
    )
    assert "\x1b[" not in captured.out
    assert captured.err == ""


def test_update_dry_run_never_reports_the_outcome_of_work_it_did_not_do(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`update --dry-run` on an already-pinned repository returned PASS — "the requested
    operation and all applicable checks completed" — for a run that deliberately did
    nothing. The already-pinned branch sits above the dry-run branch and returns before it.

    A dry run may report `WOULD_CHANGE`, which reads "a complete dry run derived exact
    changes and made none". The empty set is an exact set; what distinguishes the word is
    that the derivation was complete, not that it found something. PASS is the one word a
    dry run may never say, because it asserts an end state nobody moved to."""

    root = _repository(tmp_path)
    (root / ".ai" / "config.toml").write_text(
        skeletons.CONFIG_TOML.format(version=update.__version__), encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@x.invalid",
            "commit",
            "-m",
            "pinned fixture",
        ],
        check=True,
        capture_output=True,
    )
    monkeypatch.chdir(root)
    result = update.main(["--to", update.__version__, "--dry-run"])
    assert result.outcome != "PASS", f"a dry run claimed a completed operation: {result}"
    assert result == outcome.result("WOULD_CHANGE"), result


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


def test_spec_command_enforces_intent_and_authority(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repository(tmp_path)
    monkeypatch.chdir(root)
    home = root / ".ai" / "intent.md"
    original_intent = home.read_bytes()
    existing_spec = root / "specs" / "010-governed-foundation" / "spec.md"
    existing_bytes = existing_spec.read_bytes()
    sentinel = tmp_path / "outside-spec-scope"
    sentinel.write_bytes(b"foreign sentinel\n")

    unapproved = spec.main(["new", "unapproved", "--ref", "reviewer-said-pass"])
    assert type(unapproved) is outcome.Execution
    assert unapproved.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-unapproved").exists()

    home.write_bytes(b'{"metadata":"is not governed intent authority"}\n')
    invalid = spec.main(["new", "invalid-intent"])
    assert type(invalid) is outcome.Execution
    assert invalid.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-invalid-intent").exists()

    record = json.loads(original_intent)

    def activate(role: str) -> None:
        record["lifecycle"] = {
            "status": "active",
            "transitions": [
                {
                    "from": "draft",
                    "to": "active",
                    "changed_at": "2026-08-14T10:00:00Z",
                    "authority_role": role,
                    "approval_ref": "change-request-17",
                }
            ],
            "approval": {
                "authority_role": role,
                "approval_ref": "change-request-17",
                "approved_at": "2026-08-14T10:00:00Z",
            },
        }
        home.write_text(
            json.dumps(record, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        assert intent.validate(home, root).outcome == "PASS"

    activate("release manager")
    misattributed = spec.main(["new", "approval-must-match-owner"])
    assert type(misattributed) is outcome.Execution
    assert misattributed.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-approval-must-match-owner").exists()

    activate("repository maintainer")
    record["lifecycle"]["transitions"][-1]["authority_role"] = "AI reviewer"
    home.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert intent.validate(home, root).outcome == "PASS"
    reviewer_transition = spec.main(["new", "reviewer-transition-is-not-authority"])
    assert type(reviewer_transition) is outcome.Execution
    assert reviewer_transition.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-reviewer-transition-is-not-authority").exists()

    record["ownership"]["accountable_role"] = "AI reviewer"
    activate("AI reviewer")
    reviewer = spec.main(["new", "reviewer-is-not-authority"])
    assert type(reviewer) is outcome.Execution
    assert reviewer.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-reviewer-is-not-authority").exists()

    record["ownership"]["accountable_role"] = "repository maintainer"
    activate("repository maintainer")
    stable_validate = intent.validate

    def changed_after_validation(source: Path, repository: Path) -> intent.Validation:
        validation = stable_validate(source, repository)
        changed = json.loads(home.read_bytes())
        changed["relations"][0]["target_digest"] = f"sha256:{'0' * 64}"
        home.write_text(json.dumps(changed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return validation

    monkeypatch.setattr(intent, "validate", changed_after_validation)
    changed = spec.main(["new", "intent-changed-after-validation"])
    assert type(changed) is outcome.Execution
    assert changed.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-intent-changed-after-validation").exists()

    monkeypatch.setattr(intent, "validate", stable_validate)
    activate("repository maintainer")
    approved = spec.main(["new", "approved-change", "--ref", "owner/repo#45"])
    assert type(approved) is outcome.Execution
    assert approved.outcome == "PASS"
    created = root / "specs" / "011-approved-change" / "spec.md"
    assert created.is_file()
    assert 'ai-eng decide "<title>"' in created.read_text(encoding="utf-8")
    assert "--adr" not in created.read_text(encoding="utf-8")
    # And not the flag either: `--madr` was hard-deleted when the verb's other half went,
    # so a template still offering it teaches a command that now errors.
    assert "--madr" not in created.read_text(encoding="utf-8")
    assert existing_spec.read_bytes() == existing_bytes
    assert sentinel.read_bytes() == b"foreign sentinel\n"

    listed = spec.main(["list"])
    assert type(listed) is outcome.Result
    assert listed.outcome == "PASS"
    shown = spec.main(["show", "011"])
    assert type(shown) is outcome.Result
    assert shown.outcome == "PASS"
    absent = spec.main(["show", "999"])
    assert type(absent) is outcome.Result
    assert absent.outcome == "INCOMPLETE"
    with pytest.raises(SystemExit) as invalid_cli:
        spec.main(["new", "../outside-spec-scope"])
    assert invalid_cli.value.code == outcome.invalid_cli_exit()
    assert "reviewer-said-pass" not in capsys.readouterr().out


def test_spec_command_publishes_only_from_unchanged_authority_snapshot(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    home = root / ".ai" / "intent.md"
    record = json.loads(home.read_bytes())
    record["lifecycle"] = {
        "status": "active",
        "transitions": [
            {
                "from": "draft",
                "to": "active",
                "changed_at": "2026-08-14T10:00:00Z",
                "authority_role": "repository maintainer",
                "approval_ref": "change-request-17",
            }
        ],
        "approval": {
            "authority_role": "repository maintainer",
            "approval_ref": "change-request-17",
            "approved_at": "2026-08-14T10:00:00Z",
        },
    }
    home.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    relation = root / record["relations"][0]["path"]
    relation_before = relation.read_bytes()
    stable_validate = intent.validate
    materialized_calls = 0

    def change_relation_after_first_snapshot(source, repository):
        nonlocal materialized_calls
        validation = stable_validate(source, repository)
        if isinstance(source, dict):
            materialized_calls += 1
            if materialized_calls == 1:
                relation.write_bytes(relation_before + b"\nchanged after authority snapshot\n")
        return validation

    monkeypatch.setattr(intent, "validate", change_relation_after_first_snapshot)

    result = spec.main(["new", "snapshot-bound"])

    assert type(result) is outcome.Execution
    assert result.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-snapshot-bound").exists()
    pending = root / "specs" / "pending-011-snapshot-bound"
    assert (pending / "spec.md").is_file()
    assert any("pending-011-snapshot-bound" in item for item in result.remaining)
    assert relation.read_bytes() != relation_before


def test_spec_late_result_construction_cannot_open_authority_window(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    record = _activate_intent(root)
    relation = root / record["relations"][0]["path"]
    before = relation.read_bytes()
    real_fact = outcome.fact
    changed = False

    def late_fact(identifier, status, summary, detail=None):
        nonlocal changed
        if identifier == "spec-created" and not changed:
            changed = True
            relation.write_bytes(before + b"late authority change\n")
        return real_fact(identifier, status, summary, detail)

    monkeypatch.setattr(outcome, "fact", late_fact)

    result = spec.main(["new", "late-result-window"])

    assert type(result) is outcome.Execution
    assert result.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-late-result-window").exists()
    assert (root / "specs" / "pending-011-late-result-window" / "spec.md").is_file()


@pytest.mark.parametrize("after_create", [False, True])
def test_spec_stage_failure_reports_only_a_possible_pending_path(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    after_create: bool,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    _activate_intent(root)
    real_writer = spec.spec_transaction.writer

    @contextmanager
    def failed_writer(*args, **kwargs):
        with real_writer(*args, **kwargs) as active:

            class Writer:
                def __getattr__(self, name):
                    return getattr(active, name)

                def stage(self, *stage_args, **stage_kwargs):
                    if after_create:
                        active.stage(*stage_args, **stage_kwargs)
                    raise spec.spec_transaction.Unsafe("injected stage failure")

            yield Writer()

    monkeypatch.setattr(spec.spec_transaction, "writer", failed_writer)

    result = spec.main(["new", "uncertain-stage"])

    assert type(result) is outcome.Execution
    assert result.outcome == "INCOMPLETE"
    assert result.changes == ()
    possible = "specs/pending-011-uncertain-stage/spec.md"
    assert any(f"If {possible} exists" in item for item in result.remaining)
    assert any(fact.detail == possible for fact in result.checks)
    assert (root / possible).is_file() is after_create
    assert not (root / "specs" / "011-uncertain-stage").exists()


def test_spec_materializes_valid_transitive_relation_graph(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid_home = tmp_path / "valid"
    valid_home.mkdir()
    valid_root = _repository(valid_home)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: valid_root)
    _valid_record, valid_adrs = _transitive_intent_graph(valid_root)
    assert intent.validate(valid_root / ".ai" / "intent.md", valid_root).outcome == "PASS"

    valid = spec.main(["new", "transitive-valid"])

    assert type(valid) is outcome.Execution and valid.outcome == "PASS"
    assert valid_adrs[0].read_text(encoding="utf-8").endswith("# Linked\n")

    disabled_home = tmp_path / "disabled"
    disabled_home.mkdir()
    disabled_root = _repository(disabled_home)
    _transitive_intent_graph(disabled_root)
    with monkeypatch.context() as disabled_patch:
        disabled_patch.setattr(paths, "repo_root", lambda start=None: disabled_root)
        disabled_patch.setattr(spec, "_document_relations", lambda content: [])

        disabled = spec.main(["new", "transitive-disabled"])

    assert type(disabled) is outcome.Execution and disabled.outcome == "INCOMPLETE"
    assert not (disabled_root / "specs" / "011-transitive-disabled").exists()

    changed_home = tmp_path / "changed"
    changed_home.mkdir()
    changed_root = _repository(changed_home)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: changed_root)
    _changed_record, changed_adrs = _transitive_intent_graph(changed_root)
    real_writer = spec.spec_transaction.writer

    @contextmanager
    def changed_writer(*args, **kwargs):
        with real_writer(*args, **kwargs) as active:

            class Writer:
                def __getattr__(self, name):
                    return getattr(active, name)

                def stage(self, *stage_args, **stage_kwargs):
                    pending = active.stage(*stage_args, **stage_kwargs)
                    changed_adrs[0].write_bytes(changed_adrs[0].read_bytes() + b"changed\n")
                    return pending

            yield Writer()

    monkeypatch.setattr(spec.spec_transaction, "writer", changed_writer)

    changed = spec.main(["new", "transitive-changed"])

    assert type(changed) is outcome.Execution and changed.outcome == "INCOMPLETE"
    assert not (changed_root / "specs" / "011-transitive-changed").exists()


@pytest.mark.parametrize(("malformed", "depth"), [(True, 1), (False, 128)])
def test_spec_transitive_relation_malformed_or_over_bound_is_incomplete(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    malformed: bool,
    depth: int,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    _transitive_intent_graph(root, depth=depth, malformed=malformed)

    result = spec.main(["new", "transitive-refusal"])

    assert type(result) is outcome.Execution and result.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-transitive-refusal").exists()


@pytest.mark.parametrize("changed", ["file", "directory", "intent", "namespace"])
def test_spec_command_detects_post_stage_aba_and_preserves_named_pending(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed: str,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    record = _activate_intent(root)
    home = root / ".ai" / "intent.md"
    relation = root / record["relations"][0]["path"]
    relation_bytes = relation.read_bytes()
    intent_bytes = home.read_bytes()
    real_writer = spec.spec_transaction.writer

    @contextmanager
    def changed_writer(*args, **kwargs):
        with real_writer(*args, **kwargs) as active:

            class Writer:
                def __getattr__(self, name):
                    return getattr(active, name)

                def stage(self, *stage_args, **stage_kwargs):
                    pending = active.stage(*stage_args, **stage_kwargs)
                    if changed == "file":
                        relation.write_bytes(relation_bytes + b"changed\n")
                        relation.write_bytes(relation_bytes)
                    elif changed == "directory":
                        shutil.rmtree(relation.parent)
                        relation.parent.mkdir()
                        relation.write_bytes(relation_bytes)
                    elif changed == "intent":
                        altered = json.loads(intent_bytes)
                        altered["relations"] = []
                        home.write_text(json.dumps(altered) + "\n", encoding="utf-8")
                        home.write_bytes(intent_bytes)
                    else:
                        foreign = root / "specs" / "foreign-namespace-entry"
                        foreign.mkdir()
                        foreign.rmdir()
                    return pending

            yield Writer()

    monkeypatch.setattr(spec.spec_transaction, "writer", changed_writer)

    result = spec.main(["new", f"aba-{changed}"])

    assert type(result) is outcome.Execution
    assert result.outcome == "INCOMPLETE"
    assert not (root / "specs" / f"011-aba-{changed}").exists()
    pending = root / "specs" / f"pending-011-aba-{changed}" / "spec.md"
    assert pending.is_file()
    assert any(pending.parent.name in item for item in result.remaining)
    assert relation.read_bytes() == relation_bytes
    assert home.read_bytes() == intent_bytes
    assert all("pending-" not in row for row in spec.listing(root, True))
    assert spec.target(root) == relation


def test_spec_success_has_exact_facts_and_json_and_pending_is_not_canonical(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    _activate_intent(root)
    before = {path.relative_to(root) for path in root.rglob("*")}

    result = spec.main(["new", "exact-tree", "--ref", "owner/repo#45"])

    assert type(result) is outcome.Execution
    assert result.outcome == "PASS"
    assert [fact.id for fact in result.changes] == ["spec-created"]
    assert result.changes[0].detail == "specs/011-exact-tree/spec.md"
    assert {fact.id for fact in result.checks} == {
        "intent-authority",
        "authority-snapshot",
        "spec-publication",
    }
    after = {path.relative_to(root) for path in root.rglob("*")}
    assert after - before == {
        Path("specs/011-exact-tree"),
        Path("specs/011-exact-tree/spec.md"),
    }
    assert not any(path.name.startswith("pending-") for path in (root / "specs").iterdir())
    capsys.readouterr()

    assert cli.main(["--json", "spec", "new", "machine-tree"]) == 0
    rendered = capsys.readouterr()
    assert rendered.err == "" and rendered.out.count("\n") == 1
    payload = json.loads(rendered.out)
    assert payload["outcome"] == "PASS"
    assert payload["changes"] == [
        {
            "id": "spec-created",
            "status": "APPLIED",
            "summary": "Created governed spec",
            "detail": "specs/012-machine-tree/spec.md",
            # `detail` is what was observed; `cure` is what to do about it, and a change
            # that applied cleanly has nothing to do about it. The key is present and null
            # rather than absent, so a consumer reads one shape for every fact.
            "cure": None,
        }
    ]
    assert payload["remaining"] == [] and payload["error"] is None


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO contract")
def test_spec_relation_fifo_and_specs_alias_fail_closed_without_external_writes(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    record = _activate_intent(root)
    relation = root / record["relations"][0]["path"]
    relation.unlink()
    os.mkfifo(relation)

    started = time.monotonic()
    fifo = spec.main(["new", "fifo-refusal"])

    assert time.monotonic() - started < 2
    assert type(fifo) is outcome.Execution and fifo.outcome == "INCOMPLETE"
    assert not (root / "specs" / "011-fifo-refusal").exists()

    alias_case = tmp_path / "alias-case"
    alias_case.mkdir()
    alias_root = _repository(alias_case)
    _activate_intent(alias_root)
    external = tmp_path / "external-specs"
    external.mkdir()
    sentinel = external / "sentinel"
    sentinel.write_bytes(b"foreign bytes\n")
    shutil.rmtree(alias_root / "specs")
    (alias_root / "specs").symlink_to(external, target_is_directory=True)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: alias_root)

    aliased = spec.main(["new", "alias-refusal"])

    assert type(aliased) is outcome.Execution and aliased.outcome == "INCOMPLETE"
    assert sentinel.read_bytes() == b"foreign bytes\n"
    assert list(external.iterdir()) == [sentinel]


def test_spec_prior_pending_consumes_id_and_exhaustion_is_incomplete(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    _activate_intent(root)
    prior = root / "specs" / "pending-011-prior" / "spec.md"
    prior.parent.mkdir()
    prior.write_bytes(b"prior pending bytes\n")

    created = spec.main(["new", "after-pending"])

    assert type(created) is outcome.Execution and created.outcome == "PASS"
    assert (root / "specs" / "012-after-pending" / "spec.md").is_file()
    assert prior.read_bytes() == b"prior pending bytes\n"

    (root / "specs" / "999-exhausted").mkdir()
    exhausted = spec.main(["new", "cannot-wrap"])
    assert type(exhausted) is outcome.Execution and exhausted.outcome == "INCOMPLETE"
    assert not (root / "specs" / "1000-cannot-wrap").exists()


@pytest.mark.parametrize(
    ("failure", "code", "after_stage"),
    [
        (spec.spec_transaction.Busy("busy"), "SPEC_TRANSACTION_BUSY", False),
        (
            spec.spec_transaction.Collision("collision"),
            "SPEC_PUBLICATION_COLLISION",
            True,
        ),
        (
            spec.spec_transaction.Unsupported("unsupported"),
            "SPEC_TRANSACTION_UNSUPPORTED",
            True,
        ),
    ],
)
def test_spec_transaction_failures_are_truthful_and_never_canonical(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: spec.spec_transaction.TransactionError,
    code: str,
    after_stage: bool,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    _activate_intent(root)
    real_writer = spec.spec_transaction.writer

    @contextmanager
    def failed_writer(*args, **kwargs):
        if not after_stage:
            raise failure
        with real_writer(*args, **kwargs) as active:

            class Writer:
                def __getattr__(self, name):
                    return getattr(active, name)

                def publish(self, pending, final):
                    raise failure

            yield Writer()

    monkeypatch.setattr(spec.spec_transaction, "writer", failed_writer)

    exit_code = cli.main(["--json", "spec", "new", "transaction-refusal"])

    assert exit_code == 1
    rendered = capsys.readouterr()
    assert rendered.err == "" and rendered.out.count("\n") == 1
    payload = json.loads(rendered.out)
    assert payload["outcome"] == "INCOMPLETE"
    assert payload["error"]["code"] == code
    assert not (root / "specs" / "011-transaction-refusal").exists()
    pending = root / "specs" / "pending-011-transaction-refusal" / "spec.md"
    assert pending.is_file() is after_stage
    if after_stage:
        assert any("pending-011-transaction-refusal" in item for item in payload["remaining"])


@pytest.mark.parametrize("ambiguous", ["1st-attempt", "010-duplicate-id"])
def test_spec_ambiguous_namespace_fails_closed_without_touching_foreign_entry(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    ambiguous: str,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    _activate_intent(root)
    foreign = root / "specs" / ambiguous
    foreign.mkdir()
    sentinel = foreign / "foreign"
    sentinel.write_bytes(b"foreign bytes\n")

    result = spec.main(["new", "ambiguous-refusal"])

    assert type(result) is outcome.Execution and result.outcome == "INCOMPLETE"
    assert sentinel.read_bytes() == b"foreign bytes\n"
    assert not (root / "specs" / "011-ambiguous-refusal").exists()


def test_concurrent_spec_processes_never_share_a_numeric_id(
    tmp_path: Path,
    isolated_home: Path,
) -> None:
    root = _repository(tmp_path)
    _activate_intent(root)
    command = (
        "import sys; from ai_engineering import spec; "
        "raise SystemExit(spec.main(['new', sys.argv[1]]).exit_code)"
    )
    # The real tree, when something told us where it is: inside the mutation sandbox
    # `ROOT` is the instrumented copy, and a child importing it dies on a config it
    # cannot find from a throwaway working directory.
    source = os.environ.get("AI_ENG_REAL_SRC") or str(ROOT / "src")
    environment = {**os.environ, "PYTHONPATH": source}
    slugs = ["parallel-one", "parallel-two", "parallel-three"]
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", command, slug],
            cwd=root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for slug in slugs
    ]
    for process in processes:
        process.communicate(timeout=10)
    for slug in slugs:
        if not list((root / "specs").glob(f"[0-9][0-9][0-9]-{slug}")):
            completed = subprocess.run(
                [sys.executable, "-c", command, slug],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            assert completed.returncode == 0

    created = sorted(
        path.name
        for path in (root / "specs").iterdir()
        if any(path.name.endswith(slug) for slug in slugs)
    )
    assert len(created) == 3
    assert len({name[:3] for name in created}) == 3
    assert {name[:3] for name in created} == {"011", "012", "013"}


def test_decide_returns_canonical_outcome_after_madr_validation(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repository(tmp_path)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=role",
            "-c",
            "user.email=role@example.invalid",
            "commit",
            "-m",
            "baseline",
        ],
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    specification = root / "specs" / "010-governed-foundation" / "spec.md"
    granted = "\n## Decisions\n\n- [X] **D-010-01 — Keep authority outside the proposal**\n"
    specification.write_text(specification.read_text(encoding="utf-8") + granted, encoding="utf-8")
    spec_bytes = specification.read_bytes()
    sentinel = tmp_path / "outside-decision-scope"
    sentinel.write_bytes(b"foreign sentinel\n")

    created = decide.main(["Keep authority outside the proposal"])
    assert type(created) is outcome.Result
    assert created.outcome == "PASS"
    proposal = root / "docs" / "adr" / "0001-keep-authority-outside-the-proposal.md"
    proposal_bytes = proposal.read_bytes()
    assert madr.validate(root).outcome == "PASS"
    assert b'status: "proposed"' in proposal_bytes
    assert b"authority_role:" not in proposal_bytes
    assert "this record grants no authority" in capsys.readouterr().out
    assert specification.read_bytes() == spec_bytes
    assert sentinel.read_bytes() == b"foreign sentinel\n"

    orphan = decide.main(["Reject an orphan", "--supersede", "9999"])
    assert type(orphan) is outcome.Result
    assert orphan.outcome == "INCOMPLETE"
    assert not (root / "docs" / "adr" / "0002-reject-an-orphan.md").exists()
    assert proposal.read_bytes() == proposal_bytes
    assert specification.read_bytes() == spec_bytes

    duplicate = root / "docs" / "adr" / "0009-duplicate.md"
    duplicate.write_bytes(proposal_bytes)
    before_names = sorted(path.name for path in proposal.parent.iterdir())
    invalid_graph = decide.main(["Do not write through ambiguity"])
    assert type(invalid_graph) is outcome.Result
    assert invalid_graph.outcome == "INCOMPLETE"
    assert sorted(path.name for path in proposal.parent.iterdir()) == before_names
    assert proposal.read_bytes() == proposal_bytes
    assert duplicate.read_bytes() == proposal_bytes
    assert specification.read_bytes() == spec_bytes
    assert sentinel.read_bytes() == b"foreign sentinel\n"

    listed = decide.main(["--list"])
    assert type(listed) is outcome.Result
    assert listed.outcome == "PASS"
    with pytest.raises(SystemExit) as invalid_cli:
        decide.main(["Compatibility must stay deleted", "--mad"])
    assert invalid_cli.value.code == outcome.invalid_cli_exit()


def test_accept_requires_named_owner_date_and_risk_evidence(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    target = root / "specs" / "010-governed-foundation" / "spec.md"
    target_bytes = target.read_bytes()
    foreign = root / "specs" / "011-foreign" / "spec.md"
    foreign.parent.mkdir()
    foreign.write_bytes(b"foreign spec bytes\n")
    sentinel = tmp_path / "outside-risk-scope"
    sentinel.write_bytes(b"foreign sentinel\n")
    proof = root / "proof" / "risk-f-1.txt"
    proof.parent.mkdir()
    proof_bytes = b"executed local check receipt\n"
    proof.write_bytes(proof_bytes)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    base = [
        "--finding",
        "F-1",
        "--expires",
        tomorrow,
        "--by",
        "repository maintainer",
        "--justification",
        "the bounded mitigation is verified",
        "--spec",
        "010",
    ]

    with pytest.raises(SystemExit) as missing_evidence:
        accept.main(base)
    assert missing_evidence.value.code == outcome.invalid_cli_exit()
    assert target.read_bytes() == target_bytes

    unaccountable = accept.main([*base, "--by", "AI reviewer", "--evidence", "proof/risk-f-1.txt"])
    assert type(unaccountable) is outcome.Result
    assert unaccountable.outcome == "INCOMPLETE"
    assert target.read_bytes() == target_bytes

    ambiguous_owner = accept.main([*base, "--by", "unassigned", "--evidence", "proof/risk-f-1.txt"])
    assert type(ambiguous_owner) is outcome.Result
    assert ambiguous_owner.outcome == "INCOMPLETE"
    assert target.read_bytes() == target_bytes

    missing = accept.main([*base, "--evidence", "proof/missing.txt"])
    assert type(missing) is outcome.Result
    assert missing.outcome == "INCOMPLETE"
    assert target.read_bytes() == target_bytes

    stale = accept.main(
        [
            *base,
            "--expires",
            yesterday,
            "--evidence",
            "proof/risk-f-1.txt",
        ]
    )
    assert type(stale) is outcome.Result
    assert stale.outcome == "INCOMPLETE"
    assert target.read_bytes() == target_bytes

    invalid_date = [*base, "--expires", "2026-02-30", "--evidence", "proof/risk-f-1.txt"]
    with pytest.raises(SystemExit) as invalid_cli:
        accept.main(invalid_date)
    assert invalid_cli.value.code == outcome.invalid_cli_exit()
    assert target.read_bytes() == target_bytes

    # No controlling terminal is available to a test process, so the real boundary refuses
    # here — which is itself the check that a flag or a pipe cannot stand in for it.
    unconfirmed = accept.main([*base, "--evidence", "proof/risk-f-1.txt"])
    assert type(unconfirmed) is outcome.Result
    assert unconfirmed.outcome == "INCOMPLETE"
    assert target.read_bytes() == target_bytes
    assert not list((root / "specs" / "010-governed-foundation").glob("acceptance-*"))

    _confirmed(monkeypatch)
    accepted = accept.main([*base, "--evidence", "proof/risk-f-1.txt"])
    assert type(accepted) is outcome.Execution
    assert accepted.outcome == "PASS"
    assert accepted.changes[0].status == "APPLIED"
    record = _published(root, "010-governed-foundation")
    assert record["authority_role"] == "repository maintainer"
    # The UTC date, which is what the record stores: a person east of Greenwich
    # confirming just after midnight is not accepting on tomorrow's date.
    assert record["accepted"] == datetime.now(UTC).date().isoformat()
    assert record["expires"] == tomorrow
    assert record["evidence"] == {
        "path": "proof/risk-f-1.txt",
        "content_digest": f"sha256:{sha256(proof_bytes).hexdigest()}",
    }
    assert proof.read_bytes() == proof_bytes
    # The spec it cites, a neighbouring spec and a file outside the repository are all
    # byte-identical: an acceptance publishes, it never rewrites.
    assert target.read_bytes() == target_bytes
    assert foreign.read_bytes() == b"foreign spec bytes\n"
    assert sentinel.read_bytes() == b"foreign sentinel\n"


def test_audit_migration_recomputes_digest_and_returns_incomplete_when_blind(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    emit = paths.load("_emit")
    claim = root / ".ai" / "audit-claim.json"
    claim.write_text(json.dumps({"outcome": "PASS", "digest": "stored metadata"}))
    event = {
        "ts": "2026-08-14T00:00:00Z",
        "cls": "allowed",
        "name": "governed-check",
        "session": "audit-test",
        "seq": 1,
        "prev": "",
        "data": {"outcome": "PASS", "claim": str(claim.relative_to(root))},
    }
    event["hash"] = emit.digest(event)
    chain = emit.chain_path(root)
    chain.parent.mkdir(parents=True, exist_ok=True)
    original_chain = (json.dumps(event, sort_keys=True) + "\n").encode()
    chain.write_bytes(original_chain)

    passed = audit.main(["verify"])
    assert type(passed) is outcome.Result
    assert passed.outcome == "PASS"

    tampered = deepcopy(event)
    tampered["data"] = {"outcome": "PASS", "claim": "reviewer says intact"}
    chain.write_text(json.dumps(tampered, sort_keys=True) + "\n", encoding="utf-8")
    broken = audit.main(["verify"])
    assert type(broken) is outcome.Result
    assert broken.outcome == "FAIL"

    chain.unlink()
    blind_chain = audit.main(["verify"])
    assert type(blind_chain) is outcome.Result
    assert blind_chain.outcome == "INCOMPLETE"

    chain.write_bytes(original_chain)

    intent_record = json.loads((root / ".ai" / "intent.md").read_text(encoding="utf-8"))
    relation = root / intent_record["relations"][0]["path"]
    relation.write_bytes(relation.read_bytes() + b"\nchanged after stored PASS metadata\n")
    stale_evidence = audit.main(["verify"])
    assert type(stale_evidence) is outcome.Result
    assert stale_evidence.outcome == "INCOMPLETE"

    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    blind_root = audit.main(["verify"])
    assert type(blind_root) is outcome.Result
    assert blind_root.outcome == "INCOMPLETE"

    with pytest.raises(SystemExit) as invalid_cli:
        audit.main(["replay", "--anchors"])
    assert invalid_cli.value.code == outcome.invalid_cli_exit()


def test_report_is_hard_rename_and_bare_report_refuses(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    legacy = ROOT / "src" / "ai_engineering" / "digest.py"
    canonical = ROOT / "src" / "ai_engineering" / "report.py"
    assert not legacy.exists()
    assert canonical.is_file()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ai_engineering.digest")
    report_command = importlib.import_module("ai_engineering.report")

    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    sentinel = tmp_path / "outside-report-scope"
    sentinel.write_bytes(b"foreign sentinel\n")
    before = _snapshot(root)
    product_home = isolated_home / ".ai-engineering"

    refused = report_command.main([])
    assert type(refused) is outcome.Result
    assert refused.outcome == "INCOMPLETE"
    refusal = capsys.readouterr()
    assert "P2" in refusal.err and "not implemented" in refusal.err

    # `issue` is implemented now, and its refusal moved to the only honest place for a
    # missing field: invalid usage, before anything is built. It never infers a value and
    # never drafts half a payload, which is EP-236 read at the one command that can send.
    with pytest.raises(SystemExit) as incomplete_issue:
        report_command.main(["issue"])
    assert incomplete_issue.value.code == outcome.invalid_cli_exit()
    assert _snapshot(root) == before
    assert sentinel.read_bytes() == b"foreign sentinel\n"
    assert not product_home.exists()
    with pytest.raises(SystemExit) as future_surface:
        report_command.main(["issue", "draft"])
    assert future_surface.value.code == outcome.invalid_cli_exit()

    monkeypatch.setattr(report_command.doctor, "events", lambda repository, **_: [])
    monkeypatch.setattr(report_command.doctor, "coverage", lambda repository, **_: [])
    rendered = report_command.main(["digest"])
    assert type(rendered) is outcome.Execution
    assert rendered.outcome == "PASS"
    assert rendered.checks and rendered.changes
    assert (product_home / "cache" / "digest.json").is_file()

    capsys.readouterr()
    assert cli.main(["report", "digest", "--json"]) == 0
    machine = capsys.readouterr()
    assert machine.err == "" and machine.out.count("\n") == 1
    payload = json.loads(machine.out)
    assert payload["command"] == "report"
    assert payload["outcome"] == "PASS"


def test_exception_is_hard_rename_without_plan_alias(
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    legacy = ROOT / "src" / "ai_engineering" / "plan.py"
    canonical = ROOT / "src" / "ai_engineering" / "exception.py"
    assert not legacy.exists()
    assert canonical.is_file()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ai_engineering.plan")
    exception_command = importlib.import_module("ai_engineering.exception")

    grant_path = isolated_home / ".ai-engineering" / "cache" / "bypass.json"
    monkeypatch.setattr(
        exception_command.sys,
        "stdin",
        type("NoKeyboard", (), {"isatty": staticmethod(lambda: False)})(),
    )
    blind = exception_command.main(["--skip", "reviewer metadata says proceed"])
    assert type(blind) is outcome.Result
    assert blind.outcome == "INCOMPLETE"
    assert "no keyboard" in capsys.readouterr().out
    assert not grant_path.exists()

    assert cli.main(["exception", "--skip", "reviewer metadata says proceed", "--json"]) == 1
    machine = capsys.readouterr()
    assert machine.err == "" and machine.out.count("\n") == 1
    payload = json.loads(machine.out)
    assert payload["command"] == "exception"
    assert payload["outcome"] == "INCOMPLETE"
    assert not grant_path.exists()

    monkeypatch.setattr(
        exception_command.sys,
        "stdin",
        type("Keyboard", (), {"isatty": staticmethod(lambda: True)})(),
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": "no")
    declined = exception_command.main(["--skip", "human declined"])
    assert type(declined) is outcome.Result
    assert declined.outcome == "CANCELLED"
    assert not grant_path.exists()

    events: list[tuple[str, str, dict[str, str]]] = []

    emitter = paths.load("_emit")
    real_emit = emitter.emit

    def record(name: str, cls: str, **data: str) -> None:
        # The grant is already on disk and already correct when the concession is recorded,
        # and the real emitter still runs — a stub that swallowed the event would leave the
        # command unable to find its own record, which is now a reason to withdraw.
        written = json.loads(grant_path.read_text(encoding="utf-8"))
        assert written["guard"] == name
        assert written["reason"] == data["reason"]
        events.append((name, cls, data))
        real_emit(name, cls, **data)

    monkeypatch.setattr(emitter, "emit", record)
    monkeypatch.setattr("builtins.input", lambda prompt="": "yes")
    monkeypatch.setattr(exception_command.time, "time", lambda: 1_000.0)
    granted = exception_command.main(["--skip", "bounded human exception", "--guard", "loop_guard"])
    assert type(granted) is outcome.Result
    assert granted.outcome == "PASS"
    assert json.loads(grant_path.read_text(encoding="utf-8")) == {
        "guard": "loop_guard",
        "reason": "bounded human exception",
        "expires": 1_000.0 + exception_command.WINDOW_SECONDS,
    }
    assert events == [
        (
            "loop_guard",
            "bypassed",
            {"reason": "bounded human exception", "granted": "by a person"},
        )
    ]

    grant_path.unlink()
    events.clear()
    # A write that reports success and stores nothing. Nothing is granted, nothing is
    # recorded as granted, and no file is left behind for a guard to honour.
    monkeypatch.setattr(exception_command.os, "write", lambda descriptor, body: len(body))
    unproven = exception_command.main(["--skip", "write did not land"])
    assert type(unproven) is outcome.Result
    assert unproven.outcome == "INCOMPLETE"
    assert events == []
    assert not grant_path.exists()
    monkeypatch.setattr(exception_command.os, "write", os.write)

    with pytest.raises(SystemExit) as invalid_guard:
        exception_command.main(["--skip", "invalid", "--guard", "not_a_guard"])
    assert invalid_guard.value.code == outcome.invalid_cli_exit()


def test_a_preview_needs_no_keyboard_and_a_removal_still_does(
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--dry-run` removes nothing, so the keyboard gate had no business refusing it.

    Behind that gate the flag was inert for every script, CI job and agent — most of what a
    preview exists for — and the suite could not see it, because the one test that drives
    `--dry-run` sets `isatty` to True before it runs. An independent reviewer found it by
    running the verb from a pipe. What must not move with it is removal: `-y` arriving from
    a script is exactly what the gate was put there to stop, so it is asked again lower down
    and both halves are held here.
    """

    monkeypatch.setattr(
        uninstall.sys, "stdin", type("Pipe", (), {"isatty": staticmethod(lambda: False)})()
    )

    uninstall.main(["--dry-run"])
    said = capsys.readouterr().out
    assert "keyboard" not in said, "a preview was refused for having no keyboard"

    removal = uninstall.main(["-y"])
    assert removal.outcome == "INCOMPLETE"
    assert "keyboard" in capsys.readouterr().out, "-y from a script was not stopped"


def test_every_refusal_this_verb_can_print_says_what_and_says_nothing_was_removed(
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """One hundred and thirty mutants of `uninstall.main` survived the last measurement, and
    almost every one is a sentence in this list.

    A verb that deletes files owes two things in every refusal: what stopped it, and that
    nothing was removed. The second is the load-bearing half — a message naming a cause and
    leaving somebody unsure whether half their configuration is gone is worse than no message
    — and it is exactly the half a test asserting only `outcome == "INCOMPLETE"` cannot see.

    Each block is compared whole and in order. `in` would let a message keep its keyword and
    lose its meaning, which is how a refusal becomes a string nobody can act on.
    """

    def piped(answer: bool) -> None:
        monkeypatch.setattr(
            uninstall.sys,
            "stdin",
            type("Pipe", (), {"isatty": staticmethod(lambda: answer)})(),
        )

    def lines() -> list[str]:
        return [one for one in capsys.readouterr().out.splitlines() if one.strip()]

    # No keyboard, and this is not a dry run.
    piped(False)
    assert uninstall.main(["-y"]).outcome == "INCOMPLETE"
    assert lines() == ["  INCOMPLETE: uninstall requires a person at a keyboard. Nothing removed."]

    # A receipt that is not there at all. `isolated_home` has never been installed into.
    piped(True)
    assert uninstall.main([]).outcome == "INCOMPLETE"
    assert lines() == [
        "  INCOMPLETE: the install receipt is missing, partial, corrupt or ambiguous.",
        "  Nothing removed. Repair or migrate the receipt, then run uninstall again.",
    ]

    # A receipt that is present and unreadable answers with the same two lines, because from
    # here the two are one fact: nothing here can say what was installed.
    receipt = wiring.receipt_path()
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text("{not json", encoding="utf-8")
    assert uninstall.main([]).outcome == "INCOMPLETE"
    assert lines()[0] == (
        "  INCOMPLETE: the install receipt is missing, partial, corrupt or ambiguous."
    )

    # `--project` outside a repository. A different refusal, with a different cure, and the
    # difference matters: this one is repairable by walking into the right directory.
    receipt.write_text(json.dumps({"version": "0", "wrote": []}), encoding="utf-8")
    monkeypatch.setattr(uninstall.paths, "repo_root", lambda: None)
    monkeypatch.setattr(uninstall, "receipt_state", lambda: ({"version": "x"}, []))
    assert uninstall.main(["--project"]).outcome == "INCOMPLETE"
    assert lines() == [
        "  INCOMPLETE: --project requires the repository that will be unwired.",
        "  Nothing removed. Run this from inside the intended repository.",
    ]

    # And with a receipt naming nothing, there is nothing to remove — which is READY and not
    # a refusal. A verb that reported INCOMPLETE over an empty receipt would be calling a
    # clean machine a broken one.
    assert uninstall.main([]).outcome == "READY"
    assert lines() == [
        "  0 things are recorded here, and 0 of them will be removed:",
        f"  Kept, always: {', '.join(uninstall.KEEPS)}",
        "  Nothing to remove.",
    ]


def test_a_recorded_target_this_run_cannot_place_stops_everything(
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The undecided branch, which is the most dangerous one in the verb.

    A receipt row whose destination cannot be resolved is not a row to skip: skipping it
    would mean removing everything around it and leaving one thing behind with nothing
    recording that it stayed. So the whole run stops, and the message names each row rather
    than counting them — a person has to know which target to look at.
    """

    monkeypatch.setattr(
        uninstall.sys, "stdin", type("Tty", (), {"isatty": staticmethod(lambda: True)})()
    )
    row = {"kind": "guard", "path": "~/.somewhere/settings.json", "how": "json"}
    monkeypatch.setattr(uninstall, "receipt_state", lambda: ({"version": "x"}, [row]))
    monkeypatch.setattr(
        uninstall, "fate", lambda one, root: f"{uninstall.UNDECIDED} it cannot be placed"
    )
    monkeypatch.setattr(uninstall, "canonical", lambda one, root: None)

    result = uninstall.main([])
    said = [one for one in capsys.readouterr().out.splitlines() if one.strip()]

    assert result.outcome == "INCOMPLETE"
    assert said[0] == "  INCOMPLETE: 1 recorded targets could not be undone:"
    assert said[1] == "    guard    ~/.somewhere/settings.json  ·  it cannot be placed"
    assert said[2] == (
        "  Nothing removed. A destination this run cannot place is not one it may touch."
    )
    assert len(said) == 3


def test_uninstall_is_explicit_and_returns_receipted_outcome(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt_path = wiring.receipt_path()
    product_home = isolated_home / ".ai-engineering"
    sentinel = tmp_path / "outside-uninstall-scope"
    sentinel.write_bytes(b"foreign sentinel\n")

    monkeypatch.setattr(
        uninstall.sys,
        "stdin",
        type("Keyboard", (), {"isatty": staticmethod(lambda: True)})(),
    )
    missing = uninstall.main(["-y"])
    assert type(missing) is outcome.Result
    assert missing.outcome == "INCOMPLETE"
    assert not receipt_path.exists()
    assert sentinel.read_bytes() == b"foreign sentinel\n"

    surface = next(row for row in wiring.table()["surface"] if row["id"] == "claude-code")
    settings = wiring.expand(surface["settings"])
    wiring.json_claude(settings)
    installed = json.loads(settings.read_text(encoding="utf-8"))
    installed["foreign"] = {"theme": "user-owned"}
    wiring.write_json(settings, installed)
    row = {"path": surface["settings"], "kind": "guard", "how": surface["writer"]}
    wiring.record([row])
    receipt = wiring.receipt()
    receipt_bytes = receipt_path.read_bytes()
    settings_bytes = settings.read_bytes()

    monkeypatch.setattr(
        uninstall.sys,
        "stdin",
        type("NoKeyboard", (), {"isatty": staticmethod(lambda: False)})(),
    )
    blind = uninstall.main(["-y"])
    assert type(blind) is outcome.Result
    assert blind.outcome == "INCOMPLETE"
    assert receipt_path.read_bytes() == receipt_bytes
    assert settings.read_bytes() == settings_bytes

    monkeypatch.setattr(
        uninstall.sys,
        "stdin",
        type("Keyboard", (), {"isatty": staticmethod(lambda: True)})(),
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": "no")
    declined = uninstall.main([])
    assert type(declined) is outcome.Result
    assert declined.outcome == "CANCELLED"
    assert receipt_path.read_bytes() == receipt_bytes
    assert settings.read_bytes() == settings_bytes

    def corrupt_receipt_before_consent(prompt: str = "") -> str:
        receipt_path.write_text("{ torn", encoding="utf-8")
        return "yes"

    monkeypatch.setattr("builtins.input", corrupt_receipt_before_consent)
    raced = uninstall.main([])
    assert type(raced) is outcome.Result
    assert raced.outcome == "INCOMPLETE"
    assert receipt_path.read_text(encoding="utf-8") == "{ torn"
    assert settings.read_bytes() == settings_bytes
    receipt_path.write_bytes(receipt_bytes)

    preview = uninstall.main(["--dry-run", "-y"])
    assert type(preview) is outcome.Result
    assert preview.outcome == "WOULD_CHANGE"
    assert receipt_path.read_bytes() == receipt_bytes
    assert settings.read_bytes() == settings_bytes

    for invalid_receipt in (
        b'{"wrote":[{"path":"partial"}]}\n',
        b'{"wrote": [not json]\n',
        b"[]\n",
    ):
        receipt_path.write_bytes(invalid_receipt)
        refused = uninstall.main(["-y"])
        assert type(refused) is outcome.Result
        assert refused.outcome == "INCOMPLETE"
        assert receipt_path.read_bytes() == invalid_receipt
        assert settings.read_bytes() == settings_bytes
    receipt_path.write_bytes(receipt_bytes)

    wiring.write_json(settings, {"foreign": {"theme": "user-owned"}})
    mismatched = settings.read_bytes()
    refused = uninstall.main(["-y"])
    assert type(refused) is outcome.Result
    assert refused.outcome == "INCOMPLETE"
    assert settings.read_bytes() == mismatched
    assert receipt_path.read_bytes() == receipt_bytes
    settings.write_bytes(settings_bytes)

    removed = uninstall.main(["-y"])
    assert type(removed) is outcome.Result
    assert removed.outcome == "PASS"
    remaining_settings = json.loads(settings.read_text(encoding="utf-8"))
    assert remaining_settings["foreign"] == {"theme": "user-owned"}
    assert wiring.SIGNATURE not in json.dumps(remaining_settings)
    remaining_receipt = wiring.receipt()
    assert remaining_receipt["wrote"] == []
    for field in ("machine_id", "version", "python", "hooks"):
        assert remaining_receipt[field] == receipt[field]
    assert sentinel.read_bytes() == b"foreign sentinel\n"
    assert product_home.is_dir()

    skill_root = wiring.expand(surface["skills"])
    blind_skill = skill_root / "ai-spec" / "SKILL.md"
    blind_skill.parent.mkdir(parents=True, exist_ok=True)
    blind_skill.write_bytes(b"ownership cannot be recomputed\n")
    wiring.record([{"path": str(skill_root), "kind": "link", "how": "copy"}])
    blind_receipt = receipt_path.read_bytes()
    with monkeypatch.context() as missing_source:
        missing_source.setattr(uninstall.paths, "skills", lambda: tmp_path / "missing-skills")
        unproven = uninstall.main(["-y"])
    assert type(unproven) is outcome.Result
    assert unproven.outcome == "INCOMPLETE"
    assert blind_skill.read_bytes() == b"ownership cannot be recomputed\n"
    assert receipt_path.read_bytes() == blind_receipt

    shutil.rmtree(blind_skill.parent)
    shutil.copytree(paths.skills() / "ai-spec", blind_skill.parent)
    exact_skill = blind_skill.read_bytes()
    aliased_home = tmp_path / "aliased-product-home"
    product_home.rename(aliased_home)
    product_home.symlink_to(aliased_home, target_is_directory=True)
    aliased_receipt = receipt_path.read_bytes()
    ambiguous = uninstall.main(["-y"])
    assert type(ambiguous) is outcome.Result
    assert ambiguous.outcome == "INCOMPLETE"
    assert blind_skill.read_bytes() == exact_skill
    assert receipt_path.read_bytes() == aliased_receipt

    with pytest.raises(SystemExit) as invalid_cli:
        uninstall.main(["--force"])
    assert invalid_cli.value.code == outcome.invalid_cli_exit()


def test_cli_json_transports_real_facts_and_keeps_invalid_usage_one_object(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report_command = importlib.import_module("ai_engineering.report")
    _confirmed(monkeypatch)

    def unknown(root):
        raise doctor.Undecidable("the executed check could not decide")

    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [
            (1, "The test", "executed pass", True, lambda root: None),
            (2, "The test", "executed unknown", True, unknown),
        ],
    )
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: ["  T2   focal  BLOCKS  executed"])
    # The root this run reports on, named rather than inherited. Without it the surface block
    # is empty wherever there is no repository — which is exactly the mutation harness, whose
    # sandbox is a copied tree with no history — so this test asserted twenty-four rows in
    # every environment that happened to be a checkout and zero in the one that runs it most.
    monkeypatch.setattr(paths, "repo_root", lambda start=None: tmp_path)
    assert cli.main(["doctor", "--json"]) == 1
    doctor_output = capsys.readouterr()
    assert doctor_output.err == "" and doctor_output.out.count("\n") == 1
    doctor_payload = json.loads(doctor_output.out)
    reported = [(row["id"], row["status"]) for row in doctor_payload["checks"]]
    # Twenty-four of them are the surface block: eight surfaces, three states each, every
    # one printed even where nothing is receipted. They are counted rather than listed
    # because listing them here would move this test's subject from the JSON envelope to
    # the surface table, and the table has its own tests.
    surfaces = [row for row in reported if row[0].startswith("surface-")]
    assert len(surfaces) == 24
    assert {status for _, status in surfaces} == {"INCOMPLETE", "PASS"}
    assert [row for row in reported if not row[0].startswith("surface-")] == [
        ("assertion-1", "PASS"),
        ("assertion-2", "INCOMPLETE"),
        ("coverage-1", "PASS"),
        # This repository declares no production-ready boxes, so the one honest thing to
        # transport about them is that they are unproven. A doctor that omitted the row
        # entirely would read, to anything counting statuses, as a run with nothing left
        # to prove.
        ("readiness", "INCOMPLETE"),
    ]

    today = date.today().isoformat()
    monkeypatch.setattr(
        report_command.doctor,
        "events",
        lambda root: [
            {
                "ts": today,
                "session": "opaque-session",
                "name": "loop_guard",
                "cls": "blocked",
                "data": {"reason": "bounded loop"},
            },
            {
                "ts": today,
                "session": "opaque-session",
                "name": "doctor",
                "cls": "command",
                "data": {},
            },
        ],
    )
    monkeypatch.setattr(
        report_command.doctor,
        "coverage",
        lambda root, **_: ["  T2   focal  BLOCKS  executed"],
    )
    assert cli.main(["report", "digest", "--json"]) == 0
    report_output = capsys.readouterr()
    assert report_output.err == "" and report_output.out.count("\n") == 1
    report_payload = json.loads(report_output.out)
    report_ids = {row["id"] for row in report_payload["checks"]}
    assert {"sessions", "blocked", "bypassed", "commands", "errors", "coverage-1"} <= report_ids
    assert report_payload["changes"] == [
        {
            "id": "digest-read-receipt",
            "status": "APPLIED",
            "summary": "Updated the local digest read receipt",
            "detail": None,
            "cure": None,
        }
    ]

    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    proof = root / "proof" / "executed.txt"
    proof.parent.mkdir()
    proof.write_bytes(b"executed acceptance evidence\n")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    accept_args = [
        "accept",
        "--finding",
        "F-JSON",
        "--expires",
        tomorrow,
        "--by",
        "repository maintainer",
        "--justification",
        "bounded risk",
        "--evidence",
        "proof/executed.txt",
        "--spec",
        "010",
        "--json",
    ]
    assert cli.main(accept_args) == 0
    accepted_output = capsys.readouterr()
    assert accepted_output.err == "" and accepted_output.out.count("\n") == 1
    accepted_payload = json.loads(accepted_output.out)
    assert accepted_payload["changes"]
    assert accepted_payload["changes"][0]["status"] == "APPLIED"
    assert _published(root, "010-governed-foundation")["finding"] == "F-JSON"

    for argv, command, code in (
        (["--json"], "ai-eng", 2),
        (["--json", "unknown"], "invalid", 2),
        (["update", "--bogus", "--json"], "update", 2),
        (["--json", "--help"], "help", 0),
        (["--json", "--version"], "version", 0),
        (["update", "--help", "--json"], "update", 0),
        (["--json", "--json"], "ai-eng", 2),
    ):
        assert cli.main(argv) == code
        rendered = capsys.readouterr()
        assert rendered.err == "" and rendered.out.count("\n") == 1
        payload = json.loads(rendered.out)
        assert payload["command"] == command
        if code == 2:
            assert payload["error"]["code"] == "INVALID_CLI"
        else:
            assert payload["error"] is None


def test_accept_publishes_one_immutable_record_without_replacement(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole acceptance contract, at the boundary where it is either true or theatre.

    One immutable record appears at a name nothing else held, the spec it cites is
    byte-identical afterwards, the exact response has to arrive through the controlling
    terminal, and every refusal leaves the tree exactly as it was found — no final entry and
    no staged one. What it never claims is who answered.
    """

    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    slug = "010-governed-foundation"
    home = root / "specs" / slug
    target = home / "spec.md"
    target_bytes = target.read_bytes()
    proof = root / "proof" / "risk.txt"
    proof.parent.mkdir()
    proof_bytes = b"executed local check receipt\n"
    proof.write_bytes(proof_bytes)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    base = [
        "--finding",
        "the native rename cannot prove power-loss durability",
        "--expires",
        tomorrow,
        "--by",
        "repository maintainer",
        "--justification",
        "no supported runner executes a crash and recovery fixture",
        "--evidence",
        "proof/risk.txt",
        "--spec",
        "010",
    ]

    # The controlling terminal, for real. `isatty`, a flag and piped standard input are all
    # things a script supplies, so none of them can satisfy this.
    monkeypatch.setattr("sys.stdin", io.StringIO("ACCEPT R-010-01 AS repository maintainer\n"))
    assert accept.main(base) == outcome.result("INCOMPLETE")
    assert target.read_bytes() == target_bytes
    assert not list(home.glob("acceptance-*")) and not list(home.glob("pending-*"))

    # The exact bytes, compared against the exact challenge, read from the device itself.
    answers: dict[str, str] = {}
    real_open = builtins.open

    def device(name, *args, **kwargs):
        if name in ("/dev/tty", "CONIN$"):
            return io.StringIO(answers["line"])
        return real_open(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", device)
    answers["line"] = "ACCEPT R-010-01 AS repository maintainer"
    assert accept.controlling_terminal_response("ACCEPT R-010-01 AS repository maintainer")
    for wrong in (
        "ACCEPT R-010-01 AS repository maintainers",
        "ACCEPT R-010-02 AS repository maintainer",
        "accept R-010-01 AS repository maintainer",
        " ACCEPT R-010-01 AS repository maintainer",
        "",
    ):
        answers["line"] = wrong
        assert not accept.controlling_terminal_response(
            "ACCEPT R-010-01 AS repository maintainer"
        ), wrong
    monkeypatch.undo()
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    # A role no one can be held to is refused before anything is displayed.
    _confirmed(monkeypatch)
    for denied in ("AI reviewer", "the agent", "TBD"):
        assert accept.main([*base, "--by", denied]) == outcome.result("INCOMPLETE")
    assert not list(home.glob("acceptance-*"))

    # A privacy refusal happens before the commit point and leaves nothing staged.
    _confirmed(monkeypatch, scanner=acceptance_privacy.Verdict("FAIL", "X", "a secret was found"))
    assert accept.main(base) == outcome.result("FAIL")
    assert not list(home.glob("acceptance-*")) and not list(home.glob("pending-*"))
    assert target.read_bytes() == target_bytes

    # The one committed publication.
    _confirmed(monkeypatch)
    accepted = accept.main(base)
    assert type(accepted) is outcome.Execution
    assert accepted.outcome == "PASS"
    published = home / "acceptance-r-010-01" / "record.json"
    assert [path.name for path in sorted(home.glob("acceptance-*"))] == ["acceptance-r-010-01"]
    assert not list(home.glob("pending-*"))
    assert target.read_bytes() == target_bytes

    record = json.loads(published.read_text(encoding="utf-8"))
    assert record["spec_digest"] == "sha256:" + sha256(target_bytes).hexdigest()
    assert record["evidence"]["content_digest"] == "sha256:" + sha256(proof_bytes).hexdigest()
    assert record["record_digest"] == acceptance.record_digest(
        {name: value for name, value in record.items() if name != "record_digest"}
    )
    # Canonical bytes, exactly as the schema declares them.
    assert published.read_bytes() == acceptance.canonical_bytes(record)
    # The register reads it back, and reads it as one record with no history behind it.
    register = acceptance.read(root)
    assert register.outcome == "PASS"
    assert [entry.id for entry in register.entries] == ["R-010-01"]
    assert register.entries[0].provenance == acceptance.CANONICAL_RECORD

    # Nothing anywhere claims who answered, or that the record survives power loss.
    rendered = json.dumps(accepted.as_dict() if hasattr(accepted, "as_dict") else {})
    for never in ("identity", "durab", "tamper", "attest"):
        assert never not in rendered.lower()

    # A second writer that finds the final name taken loses without touching the winner.
    # The name has to appear between the inventory and the rename, or the register refuses
    # first and the exclusive rename is never reached — which is how this leg once passed
    # without exercising the primitive it was written for.
    original = spec_transaction._publish_noreplace
    winner = {}

    def raced(kind, source_fd, pending_name, home_fd, final_name):
        os.mkdir(final_name, dir_fd=home_fd)
        winner["name"] = final_name
        return original(kind, source_fd, pending_name, home_fd, final_name)

    monkeypatch.setattr(spec_transaction, "_publish_noreplace", raced)
    assert accept.main(base) == outcome.result("INCOMPLETE")
    assert winner["name"] == "acceptance-r-010-02"
    # The name the other writer took is still exactly what that writer left there.
    assert list((home / winner["name"]).iterdir()) == []
    assert published.read_bytes() == acceptance.canonical_bytes(record)
    assert not list(home.glob("pending-*"))


def test_accept_renews_a_stale_head_without_altering_it(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Renewal, and the one cure a stale record has.

    A record whose spec has moved on is not corrupt: it is exactly what somebody signed, and
    what has changed is the world around it. So it keeps its bytes, keeps its place, blocks
    green, and stays renewable — and the renewal binds the newly observed bytes rather than
    editing the old record to match them. A record that fails its own integrity check gets
    none of that: a renewal is a new decision, never a repair.
    """

    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    slug = "010-governed-foundation"
    home = root / "specs" / slug
    spec_md = home / "spec.md"
    proof = root / "proof" / "risk.txt"
    proof.parent.mkdir()
    proof.write_bytes(b"executed local check receipt\n")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    finding = "the native rename cannot prove power-loss durability"
    base = [
        "--finding",
        finding,
        "--expires",
        tomorrow,
        "--by",
        "repository maintainer",
        "--justification",
        "no supported runner executes a crash and recovery fixture",
        "--evidence",
        "proof/risk.txt",
        "--spec",
        "010",
    ]

    _confirmed(monkeypatch)
    assert accept.main(base).outcome == "PASS"
    first = json.loads((home / "acceptance-r-010-01" / "record.json").read_bytes())
    first_bytes = (home / "acceptance-r-010-01" / "record.json").read_bytes()

    # The world moves: the spec it was bound to is edited by somebody else.
    spec_md.write_text("# Governed foundation, edited after the decision\n", encoding="utf-8")
    moved = spec_md.read_bytes()

    # Integrity still passes; the binding does not; the record is still the head.
    assert acceptance.read(root).outcome == "PASS"
    stale = acceptance.current(root)
    assert stale.outcome == "INCOMPLETE" and stale.code == "ACCEPTANCE_BINDING_STALE"
    assert acceptance.head_of(acceptance.read(root).entries, finding).id == "R-010-01"

    # And it is renewable. The new record binds what is there now.
    assert accept.main(base).outcome == "PASS"
    renewal = json.loads((home / "acceptance-r-010-02" / "record.json").read_bytes())
    assert renewal["renews"] == "R-010-01"
    assert renewal["renewals"] == first["renewals"] + 1
    assert renewal["renews_digest"] == "sha256:" + sha256(first_bytes).hexdigest()
    assert renewal["spec_digest"] == "sha256:" + sha256(moved).hexdigest()
    # The predecessor is untouched, bytes for bytes.
    assert (home / "acceptance-r-010-01" / "record.json").read_bytes() == first_bytes
    # And the register is whole again, because the head is now bound to current bytes.
    assert acceptance.current(root).outcome == "PASS"

    # Only the head is judged for expiry: the record it renewed is history, not a live risk.
    assert accept.expired(root) == []

    # A head that fails its own integrity check is refused, and a renewal never repairs it.
    corrupt = dict(renewal, record_digest="sha256:" + "9" * 64)
    (home / "acceptance-r-010-02" / "record.json").write_bytes(acceptance.canonical_bytes(corrupt))
    assert accept.main(base) == outcome.result("INCOMPLETE")
    assert not list(home.glob("acceptance-r-010-03"))
    assert not list(home.glob("pending-*"))
    with pytest.raises(ValueError):
        accept.expired(root)


def test_accept_renews_a_derived_legacy_head_into_a_canonical_home(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """History is renewable without being rewritten.

    A block an earlier version embedded in a spec has no identity of its own. It is given a
    deterministic one in memory so a renewal can name it, and that name is never written
    back: the historical bytes end the day exactly as they started it.
    """

    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    slug = "010-governed-foundation"
    home = root / "specs" / slug
    spec_md = home / "spec.md"
    spec_md.write_text(
        spec_md.read_text(encoding="utf-8")
        + "\n```yaml\nfinding: the historical finding\nexpires: '2030-01-01'\n```\n",
        encoding="utf-8",
    )
    before = spec_md.read_bytes()
    proof = root / "proof" / "risk.txt"
    proof.parent.mkdir()
    proof.write_bytes(b"executed local check receipt\n")

    register = acceptance.read(root)
    assert register.outcome == "PASS"
    head = acceptance.head_of(register.entries, "the historical finding")
    assert head.provenance == acceptance.DERIVED_LEGACY
    assert head.id == "R-010-01"

    _confirmed(monkeypatch)
    assert (
        accept.main(
            [
                "--finding",
                "the historical finding",
                "--expires",
                (date.today() + timedelta(days=1)).isoformat(),
                "--by",
                "repository maintainer",
                "--justification",
                "the mitigation is still in place",
                "--evidence",
                "proof/risk.txt",
                "--spec",
                "010",
            ]
        ).outcome
        == "PASS"
    )

    renewal = json.loads((home / "acceptance-r-010-02" / "record.json").read_bytes())
    assert renewal["renews"] == "R-010-01"
    assert renewal["renewals"] == 1
    assert renewal["renews_digest"] == head.digest
    # The derived identity was never written into the historical block.
    assert spec_md.read_bytes() == before
    assert b"R-010-01" not in before


def test_a_publication_that_fails_leaves_no_staged_entry(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The failure the first review of this wave could not see.

    Every path between staging and the commit point leaves a `pending-` directory behind if
    nothing removes it, and a leftover wedges that ordinal for good: the next attempt
    allocates the same name and cannot create it. So the tree stays exactly as it was found,
    and the retry succeeds — which is the part that proves the cleanup was real.
    """

    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    slug = "010-governed-foundation"
    home = root / "specs" / slug
    proof = root / "proof" / "risk.txt"
    proof.parent.mkdir()
    proof.write_bytes(b"executed local check receipt\n")
    base = [
        "--finding",
        "a bounded finding",
        "--expires",
        (date.today() + timedelta(days=1)).isoformat(),
        "--by",
        "repository maintainer",
        "--justification",
        "the mitigation is in place",
        "--evidence",
        "proof/risk.txt",
        "--spec",
        "010",
    ]
    _confirmed(monkeypatch)

    # 1. The real no-replace race: the final name appears between the inventory and the
    #    rename, so the rename refuses and the loser publishes nothing.
    original = spec_transaction._publish_noreplace

    def raced(kind, source_fd, pending_name, home_fd, final_name):
        os.mkdir(final_name, dir_fd=home_fd)
        return original(kind, source_fd, pending_name, home_fd, final_name)

    monkeypatch.setattr(spec_transaction, "_publish_noreplace", raced)
    assert accept.main(base) == outcome.result("INCOMPLETE")
    assert not list(home.glob("pending-*"))

    # 2. A backend that cannot promise the primitive at all.
    def unsupported(*arguments):
        raise spec_transaction.Unsupported("exclusive rename unavailable")

    monkeypatch.setattr(spec_transaction, "_publish_noreplace", unsupported)
    (home / "acceptance-r-010-01").rmdir()
    assert accept.main(base) == outcome.result("INCOMPLETE")
    assert not list(home.glob("pending-*"))

    # 3. And the ordinal is still free, which a leftover would have taken forever.
    monkeypatch.setattr(spec_transaction, "_publish_noreplace", original)
    assert accept.main(base).outcome == "PASS"
    assert [path.name for path in sorted(home.glob("acceptance-*"))] == ["acceptance-r-010-01"]
    assert not list(home.glob("pending-*"))


def test_a_conclusive_privacy_failure_outranks_an_undecidable_one(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The rule that used to live in a function nothing called.

    Text carrying both an unclear name and a machine path is already disqualified, and which
    of the two gets reported must not depend on the order of the flags. Neither publishes, so
    this is about telling the truth in the message rather than about safety.
    """

    root = _repository(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    proof = root / "proof" / "risk.txt"
    proof.parent.mkdir()
    proof.write_bytes(b"executed local check receipt\n")
    _confirmed(monkeypatch)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    def attempt(finding: str, justification: str):
        return accept.main(
            [
                "--finding",
                finding,
                "--expires",
                tomorrow,
                "--by",
                "repository maintainer",
                "--justification",
                justification,
                "--evidence",
                "proof/risk.txt",
                "--spec",
                "010",
            ]
        )

    ambiguous = "reviewed by Robin Case"
    machine = "the log is at /home/somebody/gate.txt"
    assert attempt(ambiguous, "a bounded reason").outcome == "INCOMPLETE"
    assert attempt("a bounded finding", machine).outcome == "FAIL"
    # Both orders, same answer: the conclusive one.
    assert attempt(ambiguous, machine).outcome == "FAIL"
    assert attempt(machine, ambiguous).outcome == "FAIL"
    assert not list((root / "specs" / "010-governed-foundation").glob("acceptance-*"))


def test_exception_refuses_aliased_bypass_and_leaves_no_grant_after_incomplete(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bypass is the one grant worth attacking, so all three ways it could go quiet.

    Redirect the file and the guard reads a grant somebody else wrote. Leave a half-verified
    grant behind and the guard honours a concession the person was told was refused. Grant
    it without a findable record and the whole point of `report digest` naming bypasses is
    gone. None of the three ends with a live grant.
    """

    exception_command = importlib.import_module("ai_engineering.exception")
    store = isolated_home / ".ai-engineering" / "cache" / "bypass.json"
    monkeypatch.setattr(
        exception_command.sys,
        "stdin",
        type("Keyboard", (), {"isatty": staticmethod(lambda: True)})(),
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": "yes")

    # 1. A link anywhere on the way, including at the leaf and at the home itself.
    elsewhere = tmp_path / "somebody-elses-cache"
    elsewhere.mkdir()
    store.parent.mkdir(parents=True)
    store.parent.rmdir()
    store.parent.symlink_to(elsewhere, target_is_directory=True)
    assert exception_command.main(["--skip", "redirected cache"]) == outcome.result("INCOMPLETE")
    assert not list(elsewhere.iterdir())
    store.parent.unlink()

    store.parent.mkdir(parents=True)
    target = tmp_path / "somebody-elses-grant.json"
    target.write_text("{}\n", encoding="utf-8")
    store.symlink_to(target)
    assert exception_command.main(["--skip", "redirected grant"]) == outcome.result("INCOMPLETE")
    assert target.read_text(encoding="utf-8") == "{}\n"
    store.unlink()

    # 2. A grant whose concession cannot be found in the record is withdrawn, not kept.
    emitter = paths.load("_emit")
    real_emit = emitter.emit
    monkeypatch.setattr(emitter, "emit", lambda *arguments, **keywords: None)
    silent = exception_command.main(["--skip", "no record of this"])
    assert silent == outcome.result("INCOMPLETE")
    assert not store.exists()

    # 2b. A link swapped in while the person is typing is caught too: the check that counts
    #     is the one immediately before the write, not the one before the prompt.
    swapped = tmp_path / "swapped-in-cache"
    swapped.mkdir()

    def redirect(prompt: str = "") -> str:
        cache = store.parent
        if cache.is_dir() and not cache.is_symlink():
            for item in cache.iterdir():
                item.unlink()
            cache.rmdir()
            cache.symlink_to(swapped, target_is_directory=True)
        return "yes"

    monkeypatch.setattr("builtins.input", redirect)
    assert exception_command.main(["--skip", "swapped while typing"]) == outcome.result(
        "INCOMPLETE"
    )
    assert list(swapped.iterdir()) == []
    store.parent.unlink()
    monkeypatch.setattr("builtins.input", lambda prompt="": "yes")

    # 3. And with the record working again, the same command grants and the file is there.
    #    `monkeypatch.undo()` is never used here: this is the same MonkeyPatch the
    #    `isolated_home` fixture holds, so undoing it would send the grant to the real
    #    application home — a live bypass on the machine running the tests.
    monkeypatch.setattr(emitter, "emit", real_emit)
    assert exception_command.main(["--skip", "a bounded and recorded exception"]) == (
        outcome.result("PASS")
    )
    granted = json.loads(store.read_text(encoding="utf-8"))
    assert granted["guard"] == "loop_guard"
    assert granted["reason"] == "a bounded and recorded exception"


def test_uninstall_refuses_an_ancestor_redirected_global_mutation(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ownership answers "is this ours". It cannot answer "is this here".

    A receipt names a global destination, and a name is not a place: one link on the way and
    this verb strips entries out of, or unlinks, a file belonging to somebody else. Three
    answers come out of that question and only one is safe to act on — the run may proceed,
    the run must keep the row, or the run could not tell, which is `INCOMPLETE` and not a
    quiet keep with a zero exit.
    """

    home = isolated_home
    application = paths.home()
    application.mkdir(parents=True, exist_ok=True)
    allowed = uninstall.anchors("guard", None)
    assert application in allowed and Path.home() in allowed

    real = home / ".claude"
    real.mkdir()
    settings = real / "settings.json"
    settings.write_text('{"hooks": {}}\n', encoding="utf-8")
    assert uninstall.redirection(settings, allowed) == ""

    # The application home is not necessarily under the user's home, and a row under it is
    # placeable — the first version of this check called every one of them redirected.
    inside_application = application / "skills"
    inside_application.mkdir(parents=True, exist_ok=True)
    assert uninstall.redirection(inside_application, allowed) == ""

    # And the anchors are ordered widest-first, which is not cosmetic: with the narrow one
    # first, a default install matches it and the application home's own component is never
    # walked — so a symlink there would be trusted and then removed through.
    assert uninstall.anchors("skills", None) == (Path.home(), paths.home())
    if application.parent == Path.home():
        moved = tmp_path / "application-elsewhere"
        moved.mkdir()
        (moved / "skills").mkdir()
        for item in sorted(application.iterdir()):
            item.rmdir() if item.is_dir() else item.unlink()
        application.rmdir()
        application.symlink_to(moved, target_is_directory=True)
        assert uninstall.redirection(application / "skills", allowed) == "redirected"
        application.unlink()
        application.mkdir()

    # A link at the directory above the destination, pointing outside the home entirely.
    elsewhere = tmp_path / "somebody-elses-claude"
    elsewhere.mkdir()
    foreign = elsewhere / "settings.json"
    foreign.write_bytes(b'{"hooks": {"PreToolUse": ["theirs"]}}\n')
    before = foreign.read_bytes()
    settings.unlink()
    real.rmdir()
    (home / ".claude").symlink_to(elsewhere, target_is_directory=True)
    assert uninstall.redirection(home / ".claude" / "settings.json", allowed) == "redirected"
    assert foreign.read_bytes() == before
    # And a row this run cannot undo is not reported as a success it kept on purpose.
    surface = next(row for row in wiring.table()["surface"] if row["writer"] == "json_claude")
    blocked = uninstall.fate(
        {"kind": "guard", "path": surface["settings"], "how": surface["writer"]}, None
    )
    assert blocked.startswith(uninstall.UNDECIDED), blocked
    assert "a link on the way" in blocked

    # A link at the leaf itself is the same answer.
    (home / ".claude").unlink()
    real.mkdir()
    (real / "settings.json").symlink_to(foreign)
    assert uninstall.redirection(real / "settings.json", allowed) == "redirected"
    assert foreign.read_bytes() == before

    # A destination under no home this verb owns is undecided at the unit level.
    assert uninstall.redirection(tmp_path / "outside" / "settings.json", allowed) == "undecided"

    # And on a row this installer does own, a component it cannot even read is undecided
    # rather than a keep — which is the difference between "I looked" and "I could not".
    (real / "settings.json").unlink()
    surface = next(row for row in wiring.table()["surface"] if row["writer"] == "json_claude")
    owned_row = {"kind": "guard", "path": surface["settings"], "how": surface["writer"]}
    assert uninstall.fate(owned_row, None) == ""
    if hasattr(os, "getuid") and os.getuid() != 0:
        real.chmod(0o000)
        try:
            kept = uninstall.fate(owned_row, None)
        finally:
            real.chmod(0o755)
        assert kept.startswith(uninstall.UNDECIDED), kept
        assert "could not be placed" in kept


def test_every_verb_states_its_will_before_mutating_and_counts_its_steps(
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Three sentences this repository had in prose, now with an exit code behind them.

    A person is told what a command will touch before it touches anything, the progress
    count is the number of stages that actually run, and a cure appears only under a result
    that blocked. The will is checked against what the verbs can do rather than against what
    this table says about them, because a scope statement nobody verifies is decoration with
    a serious face on.
    """

    # Every canonical verb declares a scope, and only the canonical verbs do.
    assert set(cli.SCOPE) == set(cli.VERBS)
    for verb, (action, reads, writes, network) in cli.SCOPE.items():
        assert action and action[0].islower(), verb
        assert isinstance(reads, tuple) and isinstance(writes, tuple), verb
        assert isinstance(network, tuple), verb

    # Which verbs touch the network is derived from the product, not restated here. The
    # first version of this check grepped `src/` only and passed while `doctor` and `report`
    # were opening a socket through a hook loaded by path — the exact false green this
    # repository exists to prevent, produced by the test that was supposed to prevent it.
    # So the walk follows `paths.load(...)` into `hooks/`, which is where the egress lives.
    # A socket opened in this process is not the only way out. `spec claim` reaches a
    # remote by handing the work to git, and a check that only knows about `urlopen` would
    # have watched a verb push to a server while its will said `network none` — the same
    # false green as before, one process boundary away instead of one indirection. The git
    # subcommands that talk to a remote are markers too.
    egress = (
        "urlopen",
        "urllib.request",
        "import socket",
        "httpx",
        "requests.",
        '"push"',
        '"fetch"',
        '"ls-remote"',
    )
    hooks = ROOT / "hooks"

    def reaches_egress(name: str) -> bool:
        body = (ROOT / "src" / "ai_engineering" / f"{name}.py").read_text(encoding="utf-8")
        bodies = [body]
        # One level of sibling import, literal names only, including the ones written inside
        # a function. `spec` loads `claim` where it uses it, and following the import is the
        # difference between reading the verb and reading what the verb runs.
        for sibling in re.findall(r"from ai_engineering import ([a-z_, ]+)", body):
            for module in (part.strip() for part in sibling.split(",")):
                beside = ROOT / "src" / "ai_engineering" / f"{module}.py"
                if beside.is_file() and module != name:
                    bodies.append(beside.read_text(encoding="utf-8"))
        # The bound, said honestly: this follows a verb module into the hooks it names with
        # a double-quoted literal, and no further. It does not follow `src`-to-`src` imports,
        # so a verb reaching egress through a sibling module — or through `paths.load(name)`
        # with a variable — would leave both sides of the equality unchanged and stay green.
        # That is the same false green this check was written for, one indirection away.
        # Neither shape exists today; both call sites are literal and inside their own verb.
        for hook in re.findall(r'paths\.load\("([^"]+)"\)', body):
            loaded = hooks / f"{hook}.py"
            if loaded.is_file():
                bodies.append(loaded.read_text(encoding="utf-8"))
        return any(word in text for text in bodies for word in egress)

    assert {verb for verb in cli.VERBS if reaches_egress(verb)} == {
        verb for verb, entry in cli.SCOPE.items() if entry[3]
    }

    # A verb that mutates says so before it does, and the reader is told the direction.
    for verb in ("init", "update", "accept", "exception", "uninstall"):
        assert cli.SCOPE[verb][2], verb

    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    monkeypatch.setattr(
        importlib.import_module("ai_engineering.exception"),
        "main",
        lambda argv: outcome.result("PASS"),
    )
    capsys.readouterr()
    assert cli.main(["exception"]) == 0
    said = capsys.readouterr()

    # The will comes first, before the verb is even loaded.
    lines = [line for line in said.err.splitlines() if line.strip()]
    assert lines[0].strip().startswith("will  record one design exception")
    assert lines.index("  RUNNING 1/4  load the verb") > 0
    # Every stage the dispatcher declared, in order, and none of them invented.
    counted = [line.strip() for line in lines if line.strip().startswith("RUNNING")]
    assert counted == [
        "RUNNING 1/4  load the verb",
        "RUNNING 2/4  run it: exception",
        "RUNNING 3/4  report the outcome",
        "RUNNING 4/4  record the command",
    ]
    assert len(cli.STAGES) == 4
    # The line every verb writes whatever else it does, promised in the will because the
    # run performs it: `writes none` on a command that appends to the record is false.
    assert cli.ALWAYS_WRITES in said.err
    # A passing run offers no cure, because there is nothing to repair.
    assert "fix:" not in said.err and "fix:" not in said.out

    # And JSON mode keeps stdout to exactly one object with nothing else on either stream.
    capsys.readouterr()
    assert cli.main(["exception", "--json"]) == 0
    machine = capsys.readouterr()
    assert machine.err == ""
    assert machine.out.count("\n") == 1
    payload = json.loads(machine.out)
    assert payload["command"] == "exception" and payload["outcome"] == "PASS"
    assert "RUNNING" not in machine.out and "will" not in payload


def test_owned_means_exactly_our_entries_and_nothing_beside_them():
    """Fifty-one mutants lived in the one function that decides whether uninstall may delete.

    `_json_guard_owned` answers a question with two bad ways to be wrong. Too strict and
    uninstall leaves our hooks behind in somebody's editor for ever, because it cannot prove
    they are ours. Too loose and it deletes an entry a person added by hand. Nothing had asked
    it either question: every fixture drove the file the installer had just written, which is
    the one shape it is guaranteed to accept.

    So each surface's exact shape is asserted true, and four near-misses are asserted false:
    one of our entries missing, one extra of somebody else's beside ours, a required sibling
    field flipped, and a command that is nearly but not quite the one we install.
    """
    from ai_engineering import uninstall, wiring

    claude_hooks = [
        {"type": "command", "command": wiring.command(event)} for event in wiring.EVENTS
    ]
    claude = {
        "hooks": {
            event: [{"matcher": "*", "hooks": [hook]}]
            for event, hook in zip(wiring.EVENTS, claude_hooks, strict=True)
        }
    }
    assert uninstall._json_guard_owned(claude, "json_claude")

    # One of the four events missing: these are ours and they are not all here, so this file
    # is not one uninstall wrote and it may not be rewritten as if it were.
    short = {"hooks": {k: v for k, v in list(claude["hooks"].items())[:3]}}
    assert not uninstall._json_guard_owned(short, "json_claude")

    # Somebody else's hook beside ours is still owned, and that is the right answer — which is
    # worth stating because the opposite is the intuitive one. This function asks whether *our*
    # entries are exactly the ones we wrote, not whether the file contains nothing else. An
    # editor's settings file is shared, so refusing here would leave our hooks in it for ever;
    # what protects a person's work is that removal touches only the entries this answered for.
    shared = {
        "hooks": {
            **claude["hooks"],
            "PreToolUse": [
                *claude["hooks"]["PreToolUse"],
                {"matcher": "*", "hooks": [{"type": "command", "command": "their-own-tool"}]},
            ],
        }
    }
    assert uninstall._json_guard_owned(shared, "json_claude")

    # A command one character from ours is not ours.
    nearly = {
        "hooks": {
            event: [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": wiring.command(event) + " "}],
                }
            ]
            for event in wiring.EVENTS
        }
    }
    assert not uninstall._json_guard_owned(nearly, "json_claude")

    # Cursor carries a sibling field that is part of what makes the file ours: without
    # `failClosed` the entries could be anybody's copy of the same command.
    cursor_hook = {"command": wiring.command("PreToolUse")}
    cursor = {"failClosed": True, "hooks": {"beforeShellExecution": [cursor_hook, cursor_hook]}}
    assert uninstall._json_guard_owned(cursor, "json_cursor")
    assert not uninstall._json_guard_owned({**cursor, "failClosed": False}, "json_cursor")
    assert not uninstall._json_guard_owned(
        {"hooks": {"beforeShellExecution": [cursor_hook, cursor_hook]}}, "json_cursor"
    )

    # Codex's handler carries a timeout, a status message and an async flag, and each is part
    # of the shape. A handler missing one is not the one this installer writes.
    handler = {
        "type": "command",
        "command": wiring.command("PreToolUse"),
        "timeout": 5,
        "statusMessage": f"{wiring.MARK} guards",
        "async": False,
    }
    codex = {"hooks": {"PreToolUse": [{"hooks": [handler]}]}}
    assert uninstall._json_guard_owned(codex, "json_codex")
    for field in ("timeout", "statusMessage", "async"):
        thinner = {key: value for key, value in handler.items() if key != field}
        assert not uninstall._json_guard_owned(
            {"hooks": {"PreToolUse": [{"hooks": [thinner]}]}}, "json_codex"
        ), field

    # Copilot is compared whole rather than by collected entries, so anything beside ours is
    # a different file.
    copilot = {
        "hooks": {"preToolUse": [{"type": "command", "command": wiring.command("PreToolUse")}]}
    }
    assert uninstall._json_guard_owned(copilot, "json_copilot")
    assert not uninstall._json_guard_owned({**copilot, "theirs": 1}, "json_copilot")

    # And a spelling this function does not know is refused rather than assumed owned, which
    # is the direction that matters: an unknown surface is one uninstall must not touch.
    assert not uninstall._json_guard_owned(claude, "json_something_new")


def test_a_second_copy_of_one_of_our_own_entries_stops_the_removal():
    """The case that does refuse, and the reason is the interesting half.

    Somebody else's hook beside ours is fine: removal touches only our entries. But a second
    copy of one of *ours* is not, because now the file holds nine entries this function
    recognises and the installer writes eight. It cannot tell which of the two duplicates it
    wrote, and removing both would be guessing. So it refuses, and the refusal is what stops an
    uninstall from deleting an entry a person copied on purpose.
    """
    from ai_engineering import uninstall, wiring

    mine = {
        event: [{"matcher": "*", "hooks": [{"type": "command", "command": wiring.command(event)}]}]
        for event in wiring.EVENTS
    }
    doubled = {"hooks": {**mine, "PreToolUse": [*mine["PreToolUse"], *mine["PreToolUse"]]}}

    assert not uninstall._json_guard_owned(doubled, "json_claude")
