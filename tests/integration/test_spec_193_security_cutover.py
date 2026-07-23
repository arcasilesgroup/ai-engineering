"""Synthetic integration contracts for spec-193 host discovery and handoff."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

RUNNER_PATH = (
    Path(__file__).resolve().parents[2]
    / ".ai-engineering"
    / "scripts"
    / "spec-193"
    / "security_cutover.py"
)


def _load_runner():
    assert RUNNER_PATH.is_file(), "spec-193 isolated runner must exist"
    spec = importlib.util.spec_from_file_location("spec_193_integration", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_surface(
    root: Path,
    host: str,
    state: str,
    components: list[dict[str, str]],
) -> None:
    directory = root / host
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "surface.json").write_text(
        json.dumps({"host": host, "state": state, "components": components}),
        encoding="utf-8",
    )


def _fixture_tree(root: Path) -> Path:
    known_third_party = {
        "component_id": "third-party-mcp",
        "publisher": "third-party",
        "channel": "user-config",
        "version": "1.0.0",
    }
    codex_allowed = {
        "component_id": "node_repl",
        "publisher": "openai",
        "channel": "vendor",
        "version": "1.0.0",
    }
    for host, state in {
        "claude-code": "installed+runnable",
        "codex": "installed+runnable",
        "opencode": "installed+runnable",
        "pi": "installed+runnable",
        "cursor": "installed+broken",
        "copilot-cli": "installed+runnable",
        "vscode-copilot": "installed+runnable",
        "antigravity": "installed+runnable",
        "gemini": "residual-only",
        "kiro": "residual-only",
        "shared-root": "shared-root",
    }.items():
        components = [codex_allowed] if host == "codex" else [known_third_party]
        _write_surface(root, host, state, components)
    return root


def _clean_fixture_tree(root: Path) -> Path:
    root = _fixture_tree(root)
    for directory in root.iterdir():
        if directory.is_dir() and directory.name != "codex":
            document = json.loads((directory / "surface.json").read_text(encoding="utf-8"))
            _write_surface(root, directory.name, document["state"], [])
    return root


def test_fixture_discovery_closes_every_declared_host_state(tmp_path: Path) -> None:
    runner = _load_runner()

    report = runner.scan_fixture_discovery(_fixture_tree(tmp_path.resolve() / "surfaces"))

    assert {surface.host for surface in report.surfaces} == {
        "claude-code",
        "codex",
        "opencode",
        "pi",
        "cursor",
        "copilot-cli",
        "vscode-copilot",
        "antigravity",
        "gemini",
        "kiro",
        "shared-root",
    }
    assert report.blockers == ()


def test_fixture_discovery_blocks_symlinks_and_codex_identity_mismatches(tmp_path: Path) -> None:
    runner = _load_runner()
    root = _fixture_tree(tmp_path.resolve() / "surfaces")
    (root / "alias").symlink_to(root / "claude-code", target_is_directory=True)
    _write_surface(
        root,
        "codex-mismatch",
        "installed+runnable",
        [
            {
                "component_id": "node_repl",
                "publisher": "untrusted",
                "channel": "user-config",
                "version": "1.0.0",
            }
        ],
    )

    report = runner.scan_fixture_discovery(root)

    assert "symlink-surface" in report.blockers
    assert "codex-identity-mismatch" in report.blockers


def test_deletion_preview_preserves_survivors_and_blocks_dirty_overlap(tmp_path: Path) -> None:
    runner = _load_runner()
    report = runner.scan_fixture_discovery(_fixture_tree(tmp_path.resolve() / "surfaces"))

    preview = runner.build_deletion_preview(
        report,
        dirty_relpaths=frozenset({"opencode/surface.json"}),
        expected_survivors=frozenset({"skills"}),
    )

    assert "dirty-overlap" in preview.blockers
    assert "skills" in preview.survivors
    assert all(action.host != "codex" for action in preview.removals)


def test_restart_evidence_fails_if_a_removed_mcp_is_regenerated(tmp_path: Path) -> None:
    runner = _load_runner()
    before = runner.scan_fixture_discovery(_fixture_tree(tmp_path.resolve() / "before"))
    after_root = _clean_fixture_tree(tmp_path.resolve() / "after")
    clean_after = runner.scan_fixture_discovery(after_root)

    clean = runner.verify_restart_epoch(before, clean_after)
    assert clean.clean is True

    regenerated_root = _clean_fixture_tree(tmp_path.resolve() / "regenerated")
    _write_surface(
        regenerated_root,
        "opencode",
        "installed+runnable",
        [
            {
                "component_id": "third-party-mcp",
                "publisher": "third-party",
                "channel": "user-config",
                "version": "1.0.0",
            }
        ],
    )
    regenerated = runner.scan_fixture_discovery(regenerated_root)
    evidence = runner.verify_restart_epoch(clean_after, regenerated)
    assert evidence.clean is False
    assert "regenerated-third-party-mcp" in evidence.blockers


def test_handoff_exports_only_terminal_rows_and_values_free_fields(tmp_path: Path) -> None:
    runner = _load_runner()
    report = runner.scan_fixture_discovery(_clean_fixture_tree(tmp_path.resolve() / "surfaces"))

    handoff = runner.export_handoff(
        report,
        credential_states={"credential-001": "POSTCHECK"},
        cli_rows=[
            {
                "alias": "engram",
                "version": "1.0.0",
                "origin": "package-manager",
                "auth_class": "keychain",
                "smoke": "passed",
                "risk_class": "read-only",
                "mcp_status": "absent",
            }
        ],
    )

    assert handoff["credential_states"] == {"credential-001": "POSTCHECK"}
    with pytest.raises(ValueError):
        runner.export_handoff(
            report, credential_states={"credential-001": "NEW_AUTH_OK"}, cli_rows=[]
        )
