"""Payload-key extraction must be host-agnostic (spec-201 H5).

The OpenCode bridge canonicalises tool NAMES (`edit`/`patch` -> `Edit`) but
forwards `args` verbatim, so the payload keys arrive camelCase: `newString`,
`patchText`. `_extract_content` read Claude's snake_case keys only, returned
`""` for those, and `main()` then took the `_MIN_CONTENT_LEN` short-circuit --
no IOC scan, no injection scan, no log -- on a surface `gate-policy.md` tiers
GUARDED. These assert the extraction, which is what decides whether the scan
runs at all.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
GUARD_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "prompt-injection-guard.py"

_PAYLOAD = "x" * 40  # comfortably over _MIN_CONTENT_LEN


@pytest.fixture
def guard():
    """Load ``prompt-injection-guard.py`` under a fresh module name."""
    sys.modules.pop("aieng_prompt_injection_guard_payload_keys", None)
    spec = importlib.util.spec_from_file_location(
        "aieng_prompt_injection_guard_payload_keys", GUARD_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_prompt_injection_guard_payload_keys"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("Edit", {"file_path": "/tmp/a.py", "old_string": "a", "new_string": _PAYLOAD}),
        ("Edit", {"filePath": "/tmp/a.py", "oldString": "a", "newString": _PAYLOAD}),
        ("Edit", {"filePath": "/tmp/a.py", "patchText": _PAYLOAD}),
        ("patch", {"filePath": "/tmp/a.py", "patchText": _PAYLOAD}),
        ("Write", {"filePath": "/tmp/a.py", "content": _PAYLOAD}),
        ("Bash", {"command": _PAYLOAD}),
    ],
)
def test_scannable_content_is_extracted_on_every_host(guard, tool_name, tool_input) -> None:
    """Every host spelling yields content long enough to be scanned."""
    extracted = guard._extract_content(tool_name, tool_input)

    assert extracted == _PAYLOAD
    assert len(extracted) >= guard._MIN_CONTENT_LEN, "short-circuits before any scan runs"


def test_patch_is_on_the_guarded_surface(guard) -> None:
    """A host forwarding OpenCode's raw `patch` name must not fall off the surface."""
    assert "patch" in guard._GUARDED_TOOLS


def test_unknown_tool_still_extracts_nothing(guard) -> None:
    """Widening the key set must not widen the tool set."""
    assert guard._extract_content("Read", {"content": _PAYLOAD}) == ""


def test_non_string_payload_is_not_scanned_as_content(guard) -> None:
    """A malformed payload yields "", never a crash on len()."""
    assert guard._extract_content("Edit", {"new_string": {"nested": "object"}}) == ""
