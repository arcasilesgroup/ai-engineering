"""TDD pair test (T-1.8) for the deduped IOC alias loader (T-1.7).

Asserts that the loader returns the same payload when keyed by canonical
name as when keyed by alias name. The catalog stores only canonical entries
(``suspicious_network``, ``dangerous_commands``) and a ``spec107_aliases``
pointer map (``malicious_domains -> suspicious_network``,
``shell_patterns -> dangerous_commands``); the loader dereferences alias
keys transparently so existing call sites that ask for the alias name
continue to work.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_HOOK_PATH = PROJECT_ROOT / ".ai-engineering" / "scripts" / "hooks" / "prompt-injection-guard.py"


def _load_guard_module():
    """Import the hook module by file path (its filename has hyphens)."""
    spec = importlib.util.spec_from_file_location("prompt_injection_guard", _HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["prompt_injection_guard"] = module
    spec.loader.exec_module(module)
    return module


def test_loader_dereferences_canonical_and_alias_to_same_payload(
    tmp_path: Path,
) -> None:
    """Canonical and alias keys MUST resolve to the same payload."""
    guard = _load_guard_module()

    # Build a minimal catalog: one canonical entry + alias pointer.
    refs = tmp_path / ".ai-engineering" / "security" / "iocs"
    refs.mkdir(parents=True)
    (refs / "iocs.json").write_text(
        "{\n"
        '  "schema_version": "1.0",\n'
        '  "last_updated": "2026-05-01",\n'
        '  "suspicious_network": {\n'
        '    "description": "test net",\n'
        '    "known_malicious_domains": [\n'
        '      {"domain": "evil.example", "incident": "test", "reference": "x"}\n'
        "    ]\n"
        "  },\n"
        '  "dangerous_commands": {\n'
        '    "description": "test cmds",\n'
        '    "patterns": ["curl evil"]\n'
        "  },\n"
        '  "spec107_aliases": {\n'
        '    "malicious_domains": "suspicious_network",\n'
        '    "shell_patterns": "dangerous_commands"\n'
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    catalog = guard.load_iocs(tmp_path)

    # The loader MUST expose both canonical and alias keys with identical
    # payloads (alias keys dereference the pointer map).
    assert "suspicious_network" in catalog
    assert "malicious_domains" in catalog, (
        "alias key 'malicious_domains' missing — loader did not dereference "
        "spec107_aliases pointer map"
    )
    assert catalog["malicious_domains"] == catalog["suspicious_network"]

    assert "dangerous_commands" in catalog
    assert "shell_patterns" in catalog, (
        "alias key 'shell_patterns' missing — loader did not dereference "
        "spec107_aliases pointer map"
    )
    assert catalog["shell_patterns"] == catalog["dangerous_commands"]


def test_loader_handles_missing_alias_pointer_map(tmp_path: Path) -> None:
    """When the spec107_aliases block is absent, alias keys MUST stay absent."""
    guard = _load_guard_module()

    refs = tmp_path / ".ai-engineering" / "security" / "iocs"
    refs.mkdir(parents=True)
    (refs / "iocs.json").write_text(
        "{\n"
        '  "schema_version": "1.0",\n'
        '  "suspicious_network": {"description": "x", "known_malicious_domains": []}\n'
        "}\n",
        encoding="utf-8",
    )

    catalog = guard.load_iocs(tmp_path)

    assert "suspicious_network" in catalog
    # No alias map => no alias keys synthesized.
    assert "malicious_domains" not in catalog


def test_loader_ignores_pointer_to_unknown_canonical(tmp_path: Path) -> None:
    """Pointers to unknown canonical keys MUST NOT crash and MUST be skipped."""
    guard = _load_guard_module()

    refs = tmp_path / ".ai-engineering" / "security" / "iocs"
    refs.mkdir(parents=True)
    (refs / "iocs.json").write_text(
        "{\n"
        '  "schema_version": "1.0",\n'
        '  "suspicious_network": {"description": "x"},\n'
        '  "spec107_aliases": {\n'
        '    "shell_patterns": "nonexistent_canonical"\n'
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    catalog = guard.load_iocs(tmp_path)

    # Loader must not crash and must not synthesize an alias whose target
    # is missing.
    assert "suspicious_network" in catalog
    assert "shell_patterns" not in catalog
