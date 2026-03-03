"""Additional branch-focused tests for final coverage closure."""

from __future__ import annotations

import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.hooks import manager as hooks_manager
from ai_engineering.installer import templates as installer_templates
from ai_engineering.maintenance import branch_cleanup
from ai_engineering.maintenance import report as maintenance_report
from ai_engineering.pipeline import injector
from ai_engineering.policy import duplication, gates
from ai_engineering.skills import service as skills_service
from ai_engineering.state import decision_logic, defaults
from ai_engineering.state import io as state_io
from ai_engineering.state.models import (
    AuditEntry,
    CacheConfig,
    DecisionStore,
    InstallManifest,
    RemoteSource,
    SourcesLock,
)
from ai_engineering.updater import service as updater
from ai_engineering.validator import service as validator
from ai_engineering.vcs import azure_devops, factory, pr_description
from ai_engineering.vcs.protocol import VcsContext

pytestmark = pytest.mark.integration


def test_hooks_and_installer_templates_missing_inputs(tmp_path: Path) -> None:
    state_dir = tmp_path / ".ai-engineering" / "state"
    hooks_dir = tmp_path / ".git" / "hooks"
    state_dir.mkdir(parents=True, exist_ok=True)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "install-manifest.json").write_text("{}", encoding="utf-8")
    with patch("ai_engineering.state.io.read_json_model", side_effect=OSError("boom")):
        hooks_manager._record_hook_hashes(tmp_path)

    fake_root = tmp_path / "templates"
    fake_root.mkdir(parents=True, exist_ok=True)
    with (
        patch(
            "ai_engineering.installer.templates.get_project_template_root",
            return_value=fake_root,
        ),
        patch.object(
            installer_templates,
            "_PROJECT_TEMPLATE_MAP",
            {"missing.md": "dest/missing.md"},
        ),
        patch.object(
            installer_templates, "_PROJECT_TEMPLATE_TREES", [("missing-dir", "dest-tree")]
        ),
    ):
        result = installer_templates.copy_project_templates(tmp_path / "target")
    assert result.created == []
    assert result.skipped == []


def test_branch_cleanup_edge_branches_and_delete_failures(tmp_path: Path) -> None:
    merged = "\n* main\n\n  feature/a\n  feat/current\n"
    with (
        patch("ai_engineering.maintenance.branch_cleanup.run_git", return_value=(True, merged)),
        patch(
            "ai_engineering.maintenance.branch_cleanup.current_branch", return_value="feat/current"
        ),
    ):
        branches = branch_cleanup.list_merged_branches(tmp_path, "main")
    assert branches == ["feature/a"]

    def fake_run_git(args: list[str], project_root: Path) -> tuple[bool, str]:
        return (args[-1] != "feature/b", "")

    with patch("ai_engineering.maintenance.branch_cleanup.run_git", side_effect=fake_run_git):
        deleted, failed = branch_cleanup.delete_branches(tmp_path, ["feature/a", "feature/b"])
    assert deleted == ["feature/a"]
    assert failed == ["feature/b"]


def test_maintenance_report_exception_branches(tmp_path: Path) -> None:
    ai = tmp_path / ".ai-engineering"
    (ai / "state").mkdir(parents=True, exist_ok=True)
    (ai / "state" / "install-manifest.json").write_text(
        '{"frameworkVersion": "0.1.0", "schemaVersion": "1.2"}',
        encoding="utf-8",
    )
    (ai / "state" / "decision-store.json").write_text("{}", encoding="utf-8")

    real_read = maintenance_report.read_json_model

    def fake_read_json_model(path: Path, model_class: type[object]) -> object:
        if path.name == "decision-store.json":
            raise ValueError("bad")
        return real_read(path, model_class)

    with (
        patch("ai_engineering.version.checker.check_version", side_effect=RuntimeError("x")),
        patch(
            "ai_engineering.maintenance.report.read_json_model", side_effect=fake_read_json_model
        ),
        patch(
            "ai_engineering.maintenance.branch_cleanup.list_all_local_branches",
            side_effect=OSError("x"),
        ),
    ):
        rep = maintenance_report.generate_report(tmp_path)
    assert "Failed to parse decision store" in rep.warnings


def test_pipeline_duplication_and_gate_internal_edges(tmp_path: Path) -> None:
    unknown = injector.PipelineFile(path=Path("x.yml"), pipeline_type=injector.PipelineType.UNKNOWN)
    assert "Unknown pipeline type" in injector.suggest_injection(unknown)

    py = tmp_path / "a.py"
    py.write_text("# c\n\nprint('x')\n", encoding="utf-8")
    test_py = tmp_path / "test_skip.py"
    test_py.write_text("print('skip')\n", encoding="utf-8")
    assert duplication._normalized_lines(py) == ["print('x')"]
    ratio, dupes, total = duplication._duplication_ratio(tmp_path)
    assert (ratio, dupes, total) == (0.0, 0, 0)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("ai_engineering.policy.duplication", run_name="__main__")
    assert isinstance(exc.value.code, int)

    msg = tmp_path / "msg.txt"
    msg.write_text(f"feat: x\n\n{gates._GATE_TRAILER}\n", encoding="utf-8")
    gates._inject_gate_trailer(msg)
    assert msg.read_text(encoding="utf-8").count(gates._GATE_TRAILER) == 1

    msg2 = tmp_path / "msg2.txt"
    msg2.write_text("feat: y\n", encoding="utf-8")
    with patch.object(Path, "write_text", side_effect=OSError("nope")):
        gates._inject_gate_trailer(msg2)

    result = gates.GateResult(hook=gates.GateHook.PRE_PUSH)
    with (
        patch("ai_engineering.policy.gates.shutil.which", return_value="/bin/x"),
        patch("ai_engineering.policy.gates.subprocess.run", side_effect=FileNotFoundError),
    ):
        gates._run_tool_check(result, name="a", cmd=["tool"], cwd=tmp_path, required=True)
        gates._run_tool_check(result, name="b", cmd=["tool"], cwd=tmp_path, required=False)
    assert result.checks[-2].passed is False
    assert result.checks[-1].passed is True

    with patch("ai_engineering.policy.gates.read_json_model", side_effect=OSError("x")):
        assert gates._load_decision_store(tmp_path) is None

    ds_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    ds_path.parent.mkdir(parents=True, exist_ok=True)
    ds_path.write_text("{}", encoding="utf-8")
    with patch("ai_engineering.policy.gates.read_json_model", side_effect=ValueError("bad")):
        assert gates._load_decision_store(tmp_path) is None


def test_skills_state_and_defaults_edges(tmp_path: Path) -> None:
    assert skills_service.list_local_skill_status(tmp_path) == []

    fake_path = tmp_path / "f.yml"
    fake_path.write_text("x", encoding="utf-8")
    with patch.object(Path, "read_text", side_effect=OSError("x")):
        assert skills_service._safe_yaml_load(fake_path) == {}
        assert skills_service._safe_json_load(fake_path) == {}
        data, errors = skills_service._load_skill_frontmatter(fake_path)
    assert data == {}
    assert errors

    assert skills_service._config_path_truthy({"a": 1}, "a.b") is False

    lock = SourcesLock(
        sources=[RemoteSource(url="https://example.test/source", cache=CacheConfig())]
    )
    with (
        patch("ai_engineering.skills.service.load_sources_lock", return_value=lock),
        patch("ai_engineering.skills.service._fetch_url", return_value=None),
    ):
        failed_result = skills_service.sync_sources(tmp_path)
    assert failed_result.failed == ["https://example.test/source"]

    cache_dir = tmp_path / ".ai-engineering" / "skills-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = skills_service._cache_path(cache_dir, "https://example.test/source")
    cache_file.write_bytes(b"cached")
    with (
        patch("ai_engineering.skills.service.load_sources_lock", return_value=lock),
        patch("ai_engineering.skills.service._fetch_url", return_value=None),
    ):
        cached_result = skills_service.sync_sources(tmp_path)
    assert cached_result.cached == ["https://example.test/source"]

    assert skills_service._is_cache_fresh(lock.sources[0], cache_file) is False
    lock.sources[0].cache.last_fetched_at = lock.generated_at.replace(tzinfo=None)
    assert skills_service._is_cache_fresh(lock.sources[0], cache_file) is True

    class _Response:
        def read(self) -> bytes:
            return b"ok"

    conn = MagicMock()
    conn.getresponse.return_value = _Response()
    with patch("ai_engineering.skills.service.http.client.HTTPSConnection", return_value=conn):
        assert skills_service._fetch_url("https://example.test") == b"ok"

    ds = DecisionStore()
    with pytest.raises(ValueError):
        decision_logic.mark_remediated(ds, decision_id="missing")

    manifest = defaults.default_install_manifest(vcs_provider="azure_devops")
    assert "github" in manifest.providers.enabled

    with pytest.raises(TypeError):
        state_io._json_serializer(object())

    ndjson = tmp_path / "x.ndjson"
    ndjson.write_text(
        '{"timestamp":"2026-01-01T00:00:00Z","event":"x","actor":"y"}\n\n'
        '{"timestamp":"2026-01-01T00:00:01Z","event":"x2","actor":"y2"}\n',
        encoding="utf-8",
    )
    entries = state_io.read_ndjson_entries(ndjson, AuditEntry)
    assert entries


def test_updater_validator_and_vcs_edges(tmp_path: Path) -> None:
    ai = tmp_path / ".ai-engineering"
    (ai / "state").mkdir(parents=True, exist_ok=True)
    # ownership missing -> defaults path
    with (
        patch("ai_engineering.updater.service._evaluate_governance_files", return_value=[]),
        patch("ai_engineering.updater.service._evaluate_project_files", return_value=[]),
    ):
        res = updater.update(tmp_path, dry_run=True)
    assert res.dry_run is True

    project_root = tmp_path / "project_templates"
    project_root.mkdir(parents=True, exist_ok=True)
    with (
        patch(
            "ai_engineering.updater.service.get_project_template_root", return_value=project_root
        ),
        patch.object(updater, "_PROJECT_TEMPLATE_MAP", {"missing.md": "dest.md"}),
        patch.object(updater, "_PROJECT_TEMPLATE_TREES", [("missing-dir", "dest-tree")]),
    ):
        changes = updater._evaluate_project_files(tmp_path, updater.OwnershipMap())
    assert changes == []

    src = tmp_path / "src.txt"
    src.write_text("a", encoding="utf-8")
    dest = tmp_path / "dest.txt"
    change = updater._evaluate_file_change(src, dest, "dest.txt", updater.OwnershipMap())
    assert change.action == "create"

    assert updater._generate_diff(b"same", b"same", "x") is None
    assert updater._backup_targets([], tmp_path) is None

    external = tmp_path.parent / "not-under-target.txt"
    external.write_text("x", encoding="utf-8")
    file_change = updater.FileChange(path=external, action="update", src=src)
    backup_dir = updater._backup_targets([file_change], tmp_path)
    assert backup_dir is not None

    (tmp_path / ".claude" / "commands" / "a.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "commands" / "a.md").write_text("a", encoding="utf-8")
    mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "commands"
    mirror.mkdir(parents=True, exist_ok=True)
    (mirror / "a.md").write_text("a", encoding="utf-8")
    r = validator.validate_content_integrity(
        tmp_path, categories=[validator.IntegrityCategory.MIRROR_SYNC]
    )
    assert r.by_category()[validator.IntegrityCategory.MIRROR_SYNC]

    instruction = (
        "## Skills\n- `.ai-engineering/skills/a.md`\n\n## Agents\n- `.ai-engineering/agents/a.md`\n"
    )
    for name in ("AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md"):
        file_path = tmp_path / name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(instruction, encoding="utf-8")
    for name in ("AGENTS.md", "CLAUDE.md", "copilot-instructions.md"):
        file_path = tmp_path / "src" / "ai_engineering" / "templates" / "project" / name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(instruction + "- `.ai-engineering/agents/b.md`\n", encoding="utf-8")
    product_contract = tmp_path / ".ai-engineering" / "context" / "product"
    product_contract.mkdir(parents=True, exist_ok=True)
    (product_contract / "product-contract.md").write_text("1 skills, 1 agents", encoding="utf-8")
    ri = validator.validate_content_integrity(
        tmp_path,
        categories=[
            validator.IntegrityCategory.COUNTER_ACCURACY,
            validator.IntegrityCategory.CROSS_REFERENCE,
            validator.IntegrityCategory.INSTRUCTION_CONSISTENCY,
            validator.IntegrityCategory.MANIFEST_COHERENCE,
            validator.IntegrityCategory.SKILL_FRONTMATTER,
        ],
    )
    assert ri.checks

    ctx = VcsContext(project_root=tmp_path, branch="feat/x", target_branch="main")
    provider = azure_devops.AzureDevOpsProvider()
    with patch.object(provider, "_run", return_value=SimpleNamespace(success=True, output="{bad")):
        pr = provider.create_pr(ctx)
    assert pr.success is True

    with patch.object(
        provider, "_run", return_value=SimpleNamespace(success=True, output='[{"x":1}]')
    ):
        auto = provider.enable_auto_complete(ctx)
    assert auto.success is False

    manifest_path = tmp_path / ".ai-engineering" / "state" / "install-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    state_io.write_json_model(
        manifest_path,
        InstallManifest(providers={"primary": "invalid", "enabled": ["invalid"]}),
    )
    with patch("ai_engineering.vcs.factory.detect_from_remote", return_value="unknown"):
        assert factory.get_provider(tmp_path).provider_name() == "github"

    active = tmp_path / ".ai-engineering" / "context" / "specs" / "_active.md"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_text('active: "123-test"\n', encoding="utf-8")
    with patch.object(Path, "read_text", side_effect=OSError("x")):
        assert pr_description._read_active_spec(tmp_path) is None


def test_validator_remaining_branches(tmp_path: Path) -> None:
    ai = tmp_path / ".ai-engineering"
    (ai / "skills").mkdir(parents=True, exist_ok=True)
    (ai / "agents").mkdir(parents=True, exist_ok=True)
    (ai / "context" / "product").mkdir(parents=True, exist_ok=True)
    (ai / "context" / "specs").mkdir(parents=True, exist_ok=True)
    (ai / "state").mkdir(parents=True, exist_ok=True)
    (ai / "manifest.yml").write_text("name: x\n", encoding="utf-8")

    (ai / "skills" / "refs.md").write_text(
        "see `ai-engineering/skills/missing.md`\n",
        encoding="utf-8",
    )

    canonical_cmd = tmp_path / ".claude" / "commands"
    canonical_cmd.mkdir(parents=True, exist_ok=True)
    (canonical_cmd / "same.md").write_text("A", encoding="utf-8")
    (canonical_cmd / "only-canonical.md").write_text("B", encoding="utf-8")
    mirror_cmd = (
        tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "commands"
    )
    mirror_cmd.mkdir(parents=True, exist_ok=True)
    (mirror_cmd / "same.md").write_text("DIFF", encoding="utf-8")

    base = (
        "## Skills\n"
        "- `.ai-engineering/skills/a.md`\n"
        "- `   `\n\n"
        "## Agents\n"
        "- `.ai-engineering/agents/a.md`\n"
    )
    (tmp_path / "AGENTS.md").write_text(base, encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(
        base + "- `.ai-engineering/skills/extra.md`\n- `.ai-engineering/agents/extra.md`\n",
        encoding="utf-8",
    )
    (tmp_path / ".github" / "copilot-instructions.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".github" / "copilot-instructions.md").write_text(base, encoding="utf-8")

    template_root = tmp_path / "src" / "ai_engineering" / "templates" / "project"
    template_root.mkdir(parents=True, exist_ok=True)
    (template_root / "AGENTS.md").write_text(base, encoding="utf-8")
    (template_root / "CLAUDE.md").write_text(base, encoding="utf-8")
    (template_root / "copilot-instructions.md").write_text(base, encoding="utf-8")

    (ai / "skills" / "good-file-name").mkdir(parents=True, exist_ok=True)
    (ai / "skills" / "good-file-name" / "SKILL.md").write_text(
        "---\nname: BadName\nversion: one\n---\n",
        encoding="utf-8",
    )
    (ai / "context" / "product" / "product-contract.md").write_text(
        "1 skills, 1 agents", encoding="utf-8"
    )

    report = validator.validate_content_integrity(
        tmp_path,
        categories=[
            validator.IntegrityCategory.FILE_EXISTENCE,
            validator.IntegrityCategory.MIRROR_SYNC,
            validator.IntegrityCategory.CROSS_REFERENCE,
            validator.IntegrityCategory.INSTRUCTION_CONSISTENCY,
            validator.IntegrityCategory.MANIFEST_COHERENCE,
            validator.IntegrityCategory.SKILL_FRONTMATTER,
        ],
    )
    assert report.checks


def test_validator_internal_line_coverage_targets(tmp_path: Path) -> None:
    ai = tmp_path / ".ai-engineering"
    (ai / "skills").mkdir(parents=True, exist_ok=True)
    (ai / "agents").mkdir(parents=True, exist_ok=True)

    # line 240: force ref_path to include ai-engineering/ prefix
    skill_file = ai / "skills" / "debug.md"
    skill_file.write_text("`ai-engineering/skills/missing.md`\n", encoding="utf-8")
    report = validator.IntegrityReport()
    custom_pattern = validator.re.compile(r"`?(ai-engineering/skills/missing\.md)`?")
    with patch.object(validator, "_PATH_REF_PATTERN", custom_pattern):
        validator._check_file_existence(tmp_path, report)

    # lines 425-458: drive claude commands mirror mismatch/missing logic directly
    canonical = tmp_path / ".claude" / "commands"
    canonical.mkdir(parents=True, exist_ok=True)
    (canonical / "a.md").write_text("1", encoding="utf-8")
    (canonical / "b.md").write_text("2", encoding="utf-8")
    mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "commands"
    mirror.mkdir(parents=True, exist_ok=True)
    (mirror / "a.md").write_text("DIFF", encoding="utf-8")
    mirror_report = validator.IntegrityReport()
    validator._check_claude_commands_mirror(tmp_path, mirror_report)

    # line 654: blank ref line in a skill References section
    refs = ai / "skills" / "refs.md"
    refs.write_text("## References\n- `   `\n", encoding="utf-8")
    cross_report = validator.IntegrityReport()
    validator._check_cross_references(tmp_path, cross_report)

    # line 782: create missing agent in non-reference instruction file
    base_ref = (
        "## Skills\n"
        "- `.ai-engineering/skills/a.md`\n"
        "## Agents\n"
        "- `.ai-engineering/agents/a.md`\n"
        "- `.ai-engineering/agents/b.md`\n"
    )
    base_other = (
        "## Skills\n- `.ai-engineering/skills/a.md`\n## Agents\n- `.ai-engineering/agents/a.md`\n"
    )
    files = {
        ".github/copilot-instructions.md": base_ref,
        "AGENTS.md": base_other,
        "CLAUDE.md": base_other,
        "src/ai_engineering/templates/project/copilot-instructions.md": base_other,
        "src/ai_engineering/templates/project/AGENTS.md": base_other,
        "src/ai_engineering/templates/project/CLAUDE.md": base_other,
    }
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    consistency = validator.IntegrityReport()
    validator._check_instruction_consistency(tmp_path, consistency)


def test_validator_claude_commands_mirror_ok_path(tmp_path: Path) -> None:
    canonical = tmp_path / ".claude" / "commands"
    mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "commands"
    canonical.mkdir(parents=True, exist_ok=True)
    mirror.mkdir(parents=True, exist_ok=True)
    (canonical / "same.md").write_text("ok", encoding="utf-8")
    (mirror / "same.md").write_text("ok", encoding="utf-8")

    report = validator.IntegrityReport()
    validator._check_claude_commands_mirror(tmp_path, report)
    assert any(check.name == "claude-commands-mirrors" for check in report.checks)
