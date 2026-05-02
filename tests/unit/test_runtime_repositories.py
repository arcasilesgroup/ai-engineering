"""Tests for HX-08 manifest and durable-state repository boundaries."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.state.defaults import default_ownership_map
from ai_engineering.state.io import write_json_model
from ai_engineering.state.models import (
    DecisionStore,
    FrameworkCapabilitiesCatalog,
)
from ai_engineering.state.repository import DurableStateRepository, ManifestRepository
from ai_engineering.state.service import StateService


def _write_manifest(root: Path) -> Path:
    manifest_path = root / ".ai-engineering" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        "# preserved comment\n"
        "providers:\n"
        "  vcs: github\n"
        "  ides: [claude_code]\n"
        "  stacks: [python, typescript]\n"
        "quality:\n"
        "  coverage: 80\n",
        encoding="utf-8",
    )
    return manifest_path


def test_manifest_repository_supports_typed_raw_partial_and_patch(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path)
    repository = ManifestRepository(tmp_path)

    typed = repository.load_typed()
    raw = repository.load_raw()
    providers = repository.get_partial("providers")
    repository.patch_field("quality.coverage", 90)

    assert isinstance(typed, ManifestConfig)
    assert typed.providers.stacks == ["python", "typescript"]
    assert raw["quality"]["coverage"] == 80
    assert providers == {
        "vcs": "github",
        "ides": ["claude_code"],
        "stacks": ["python", "typescript"],
    }
    updated_text = manifest_path.read_text(encoding="utf-8")
    assert "# preserved comment" in updated_text
    assert "coverage: 90" in updated_text


def test_manifest_repository_missing_raw_snapshot_is_empty(tmp_path: Path) -> None:
    repository = ManifestRepository(tmp_path)

    assert repository.manifest_path == tmp_path / ".ai-engineering" / "manifest.yml"
    assert repository.load_raw() == {}
    assert repository.get_partial("providers.stacks") is None
    assert repository.load_typed().providers.stacks == ["python"]


def test_durable_state_repository_loads_stable_state_families(tmp_path: Path) -> None:
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    write_json_model(state_dir / "decision-store.json", DecisionStore())
    write_json_model(state_dir / "ownership-map.json", default_ownership_map())
    write_json_model(state_dir / "framework-capabilities.json", FrameworkCapabilitiesCatalog())
    repository = DurableStateRepository(tmp_path)

    assert repository.state_dir == state_dir
    assert repository.install_state_path == state_dir / "install-state.json"
    assert repository.framework_events_path == state_dir / "framework-events.ndjson"
    assert repository.load_decisions().schema_version == "1.1"
    assert repository.load_ownership().paths
    assert repository.load_framework_capabilities().schema_version == "1.0"


def test_state_service_remains_compatible_with_repository_boundary(tmp_path: Path) -> None:
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    write_json_model(state_dir / "decision-store.json", DecisionStore())
    write_json_model(state_dir / "ownership-map.json", default_ownership_map())
    write_json_model(state_dir / "framework-capabilities.json", FrameworkCapabilitiesCatalog())
    service = StateService(tmp_path)

    assert service.state_dir == state_dir
    assert service.load_decisions().schema_version == "1.1"
    assert service.load_ownership().paths


def test_durable_state_repository_preserves_install_state_migration(tmp_path: Path) -> None:
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "install-state.json").write_text(
        '{"schemaVersion": "1.0", "tooling": {"gh": {"mode": "manual"}}}\n',
        encoding="utf-8",
    )
    repository = DurableStateRepository(tmp_path)

    state = repository.load_install_state()

    assert state.tooling["gh"].mode == "manual"
    assert state.required_tools_state == {}
    assert (state_dir / "install-state.json").is_file()
    assert list(state_dir.glob("install-state.json.legacy-*"))
