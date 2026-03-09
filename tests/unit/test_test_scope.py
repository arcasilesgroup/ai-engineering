"""Unit tests for selective test scope resolution engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ai_engineering.policy.test_scope as test_scope

pytestmark = pytest.mark.unit


class TestComputeTestScope:
    """Tests for deterministic scope resolution logic."""

    def _patch_diff(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        changed: list[str],
        deleted: list[str] | None = None,
        renamed: list[str] | None = None,
    ) -> None:
        deleted = deleted or []
        renamed = renamed or []

        def fake_get_changed_files(
            project_root: Path,
            base_ref: str,
            diff_filter: str = "ACMRT",
        ) -> list[str]:
            if diff_filter == "ACMRT":
                return changed
            if diff_filter == "D":
                return deleted
            pytest.fail(f"unexpected diff_filter: {diff_filter}")

        monkeypatch.setattr(test_scope, "get_changed_files", fake_get_changed_files)
        monkeypatch.setattr(test_scope, "_parse_renamed_paths", lambda *_args: renamed)
        monkeypatch.setattr(test_scope, "current_branch", lambda *_args: "feature/test")

    def test_single_module_resolution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(
            monkeypatch,
            changed=["src/ai_engineering/hooks/manager.py"],
        )

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "selective"
        assert "tests/unit/test_hooks.py" in scope.selected_tests
        assert scope.unmatched_src_files == []

    def test_multi_module_resolution_union(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(
            monkeypatch,
            changed=[
                "src/ai_engineering/hooks/manager.py",
                "src/ai_engineering/vcs/factory.py",
            ],
        )

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "selective"
        assert "tests/unit/test_hooks.py" in scope.selected_tests
        assert "tests/unit/test_vcs_providers.py" in scope.selected_tests

    def test_changed_test_file_is_selected_for_tier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(monkeypatch, changed=["tests/unit/test_hooks.py"])

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "selective"
        assert scope.selected_tests == ["tests/unit/test_hooks.py"]

    def test_full_trigger_detection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(monkeypatch, changed=["pyproject.toml"])

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "full"
        assert "full_suite_trigger_changed" in scope.reasons
        assert scope.selected_tests == ["tests/unit"]

    def test_high_risk_glob_triggers_full(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(monkeypatch, changed=["scripts/check_workflow_policy.py"])

        scope = test_scope.compute_test_scope(Path("."), tier="integration", base_ref="main")

        assert scope.mode == "full"
        assert "high_risk_path_changed" in scope.reasons
        assert scope.selected_tests == ["tests/integration"]

    def test_unknown_src_file_falls_back_full(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(monkeypatch, changed=["src/ai_engineering/unknown/new_module.py"])

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "full"
        assert "unmatched_src_files" in scope.reasons
        assert "src/ai_engineering/unknown/new_module.py" in scope.unmatched_src_files

    def test_empty_result_after_code_change_falls_back_full(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self._patch_diff(monkeypatch, changed=["src/ai_engineering/updater/service.py"])

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "full"
        assert "empty_after_code_change" in scope.reasons

    def test_docs_only_changes_skip_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(monkeypatch, changed=["README.md", "docs/notes.txt"])

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "selective"
        assert scope.selected_tests == []
        assert scope.reasons == ["docs_only"]

    def test_deleted_src_file_falls_back_full(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(
            monkeypatch,
            changed=["README.md"],
            deleted=["src/ai_engineering/hooks/manager.py"],
        )

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "full"
        assert "src_delete_detected" in scope.reasons

    def test_rename_includes_old_and_new_module(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(
            monkeypatch,
            changed=["src/ai_engineering/vcs/new_name.py"],
            renamed=[
                "src/ai_engineering/hooks/old_name.py",
                "src/ai_engineering/vcs/new_name.py",
            ],
        )

        scope = test_scope.compute_test_scope(Path("."), tier="integration", base_ref="main")

        assert scope.mode == "selective"
        assert "tests/integration/test_hooks_git.py" in scope.selected_tests
        assert "tests/integration/test_vcs_factory.py" in scope.selected_tests

    def test_multiple_rules_union_has_no_duplicates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        rules = [
            test_scope.ScopeRule(
                name="a",
                source_globs=["src/ai_engineering/policy/*.py"],
                tiers={"unit": ["tests/unit/test_gates.py"], "integration": [], "e2e": []},
            ),
            test_scope.ScopeRule(
                name="b",
                source_globs=["src/ai_engineering/policy/gates.py"],
                tiers={"unit": ["tests/unit/test_gates.py"], "integration": [], "e2e": []},
            ),
        ]
        monkeypatch.setattr(test_scope, "TEST_SCOPE_RULES", rules)
        self._patch_diff(monkeypatch, changed=["src/ai_engineering/policy/gates.py"])

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "selective"
        assert scope.selected_tests == ["tests/unit/test_gates.py"]

    def test_main_branch_forces_full(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(monkeypatch, changed=["src/ai_engineering/hooks/manager.py"])
        monkeypatch.setattr(test_scope, "current_branch", lambda *_args: "main")

        scope = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="main")

        assert scope.mode == "full"
        assert any(reason.startswith("main_branch") for reason in scope.reasons)

    def test_json_diagnostic_has_expected_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(monkeypatch, changed=["src/ai_engineering/hooks/manager.py"])

        diagnostic = test_scope.compute_test_scope_diagnostic(
            Path("."),
            tier="unit",
            base_ref="main",
        )

        expected = {
            "tier",
            "base_ref_resolved",
            "changed_files",
            "matched_rules",
            "unmatched_src_files",
            "selected_tests",
            "mode",
            "reasons",
            "duration_ms",
        }
        assert set(diagnostic.keys()) == expected

    def test_stable_ordering_is_deterministic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_diff(
            monkeypatch,
            changed=[
                "src/ai_engineering/vcs/factory.py",
                "src/ai_engineering/hooks/manager.py",
            ],
        )

        scope1 = test_scope.compute_test_scope(Path("."), tier="integration", base_ref="main")
        scope2 = test_scope.compute_test_scope(Path("."), tier="integration", base_ref="main")

        assert scope1.selected_tests == scope2.selected_tests
        assert scope1.matched_rules == scope2.matched_rules

    def test_base_ref_auto_falls_back_to_origin_main_on_push(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        observed_base_refs: list[str] = []

        def fake_run_git(args: list[str], cwd: Path, timeout: int = 30) -> tuple[bool, str]:
            if args[:4] == ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"]:
                return False, ""
            if args[:3] == ["rev-parse", "--verify", "origin/main"]:
                return True, "ok"
            return True, ""

        def fake_get_changed_files(
            project_root: Path,
            base_ref: str,
            diff_filter: str = "ACMRT",
        ) -> list[str]:
            observed_base_refs.append(base_ref)
            return [] if diff_filter == "D" else ["README.md"]

        monkeypatch.setattr(test_scope, "run_git", fake_run_git)
        monkeypatch.setattr(test_scope, "get_changed_files", fake_get_changed_files)
        monkeypatch.setattr(test_scope, "_parse_renamed_paths", lambda *_args: [])
        monkeypatch.setattr(test_scope, "current_branch", lambda *_args: "feature/test")

        _ = test_scope.compute_test_scope(Path("."), tier="unit", base_ref="auto")

        assert observed_base_refs
        assert all(ref == "origin/main" for ref in observed_base_refs)


class TestResolveScopeMode:
    """Tests for env mode resolution."""

    def test_mode_defaults_to_shadow(self) -> None:
        mode = test_scope.resolve_scope_mode({})
        assert mode == "shadow"

    def test_mode_enforce(self) -> None:
        mode = test_scope.resolve_scope_mode({"AI_ENG_TEST_SCOPE_MODE": "enforce"})
        assert mode == "enforce"

    def test_mode_off_alias(self) -> None:
        mode = test_scope.resolve_scope_mode(
            {
                "AI_ENG_TEST_SCOPE_MODE": "enforce",
                "AI_ENG_TEST_SCOPE": "off",
            }
        )
        assert mode == "off"


class TestScopeCli:
    """Tests for test_scope CLI parsing and output."""

    def test_parse_args_defaults_to_args_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["test_scope.py", "--tier", "unit"],
        )

        args = test_scope._parse_args()

        assert args.tier == "unit"
        assert args.base_ref == "auto"
        assert args.format == "args"

    def test_main_json_format_prints_payload(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            [
                "test_scope.py",
                "--tier",
                "integration",
                "--format",
                "json",
                "--base-ref",
                "origin/main",
            ],
        )

        payload = {
            "tier": "integration",
            "base_ref_resolved": "origin/main",
            "changed_files": ["src/ai_engineering/hooks/manager.py"],
            "matched_rules": ["hooks"],
            "unmatched_src_files": [],
            "selected_tests": ["tests/integration/test_hooks_git.py"],
            "mode": "selective",
            "reasons": [],
            "duration_ms": 1,
        }
        monkeypatch.setattr(
            test_scope, "compute_test_scope_diagnostic", lambda *_args, **_kwargs: payload
        )

        exit_code = test_scope.main()
        output = capsys.readouterr().out.strip()

        assert exit_code == 0
        assert json.loads(output) == payload

    def test_main_args_format_prints_selected_tests(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["test_scope.py", "--tier", "unit", "--format", "args"],
        )

        payload = {
            "tier": "unit",
            "base_ref_resolved": "origin/main",
            "changed_files": ["src/ai_engineering/vcs/factory.py"],
            "matched_rules": ["vcs"],
            "unmatched_src_files": [],
            "selected_tests": [
                "tests/unit/test_vcs_factory.py",
                "tests/unit/test_vcs_providers.py",
            ],
            "mode": "selective",
            "reasons": [],
            "duration_ms": 1,
        }
        monkeypatch.setattr(
            test_scope, "compute_test_scope_diagnostic", lambda *_args, **_kwargs: payload
        )

        exit_code = test_scope.main()
        output = capsys.readouterr().out.strip()

        assert exit_code == 0
        assert output == "tests/unit/test_vcs_factory.py tests/unit/test_vcs_providers.py"
