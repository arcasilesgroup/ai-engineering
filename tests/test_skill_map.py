"""The map's template holes are data, not suppressions.

`sm` (skill-map.ai) flags as broken any link whose target does not exist, and the
framework's own skills and corpora point at `specs/NNN-slug/...` — a demo hole that
says "your number and slug go here", not a missing file. The exclusion list in
`policy/skill-map-exclusions.toml` declares those holes as data (spec 026): the scan
still runs, the exclusion just tells the gate which broken pointers are expected. This
file refuses an exclusion list that stops covering what the tree actually writes, and
refuses a template disguise — a real target smuggled in as a hole would be the exact
failure the map exists to make visible.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from ai_engineering import paths

ROOT = Path(__file__).resolve().parents[1]


def _exclusions() -> list[str]:
    data = tomllib.loads(paths.policy("skill-map-exclusions.toml").read_text(encoding="utf-8"))
    out = []
    for key in ("template", "nested_routes"):
        out.extend(data.get(key, []))
    return out


def _template_targets() -> list[str]:
    """The NNN-slug targets the tree writes, read from the markdown nodes.

    Every backticked path containing `NNN-slug` is a demonstration hole by the
    framework's own convention. Read from the tree rather than from a typed list so
    the exclusion list is the one place that decides; the test only confirms the
    tree's holes are all declared.
    """

    hits: set[str] = set()
    pattern = re.compile(r"`([^`]*NNN-slug[^`]*)`")
    for path in [*ROOT.glob(".agents/skills/*/SKILL.md"), *ROOT.glob(".agents/skills/*/corpus.md")]:
        if not path.is_file():
            continue
        for match in pattern.finditer(path.read_text(encoding="utf-8", errors="replace")):
            hits.add(match.group(1).strip())
    return sorted(hits)


def test_every_template_hole_in_the_tree_is_declared():
    """A hole the tree writes but the list does not name would red the gate every run.

    The list is the only judgement; this test keeps it honest by walking the tree. If a
    skill starts pointing at a new `NNN-slug` path tomorrow, this fails until the list
    names it — which is the split spec 026 wanted: the exclusion is checked data, not a
    suppression comment.
    """

    declared = _exclusions()
    assert declared, "the exclusion list is empty; every template hole would red the gate"
    for target in _template_targets():
        covered = any(target == prefix or target.startswith(prefix) for prefix in declared)
        assert covered, f"the tree writes template hole {target!r} and the list does not name it"


def test_no_real_target_is_disguised_as_a_template_hole():
    """A real, existing file must never be hidden behind the template prefix.

    The prefix list is for `NNN-slug` demonstration paths only. If a real filename
    matching a prefix ever exists on disk, the exclusion would silently forgive a real
    broken link that happens to share the spelling — the one failure mode the map
    exists to prevent.
    """

    declared = _exclusions()
    for prefix in declared:
        assert "NNN-slug" in prefix, (
            f"exclusion {prefix!r} does not contain the NNN-slug marker; "
            "a real target could be hidden behind it"
        )
