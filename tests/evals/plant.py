"""Plant defect packs into a clean fixture tree, graded key kept outside the tree.

Part of spec 029 / B-029-1: a review skill is scored against defects it must find, and the
graded answer key must never be visible to the skill being scored — a review that finds bugs
by reading the list of planted bugs proves nothing (graph-engineering's rule). `plant` writes
no key inside the fixture it mutates.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from eval_types import Defect, Key

_REFUSE_IN_TREE = "the graded key must live outside the fixture tree being scored"
_REFUSE_ABS = "defect paths and key dirs must be inside their declared roots"


def _guard_inside(root: Path, target: Path) -> None:
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(_REFUSE_ABS) from exc


def apply_pack(pack: Path, fixture: Path, key_dir: Path) -> Key:
    """Plant one pack's defects into `fixture` (mutated in place) and write the graded key.

    `fixture` must already be a clean copy; `key_dir` holds the graded positions and MUST NOT
    be the fixture.
    """
    fixture = fixture.resolve()
    key_dir = key_dir.resolve()
    if key_dir == fixture or fixture.is_relative_to(key_dir) or key_dir.is_relative_to(fixture):
        raise ValueError(_REFUSE_IN_TREE)

    spec = tomllib.loads((pack / "pack.toml").read_text(encoding="utf-8"))
    defects = list(spec["defects"])
    key: Key = {"pack": pack.name, "defects": []}
    graded: list[Defect] = []
    for defect in defects:
        rel = Path(str(defect["file"]))
        _guard_inside(fixture, fixture / rel)
        target = fixture / rel
        source = target.read_text(encoding="utf-8")
        if str(defect.get("find")) not in source:
            raise ValueError(f"defect {defect['id']}: 'find' not present in {rel}")
        target.write_text(
            source.replace(str(defect["find"]), str(defect["replace"])), encoding="utf-8"
        )
        graded.append(
            {
                "id": str(defect["id"]),
                "tier": int(defect["tier"]),
                "file": str(rel),
                "line": int(defect.get("line", 1)),
            }
        )
    key["defects"] = graded
    key_dir.mkdir(parents=True, exist_ok=True)
    (key_dir / f"{pack.name}.json").write_text(
        json.dumps(key, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return key


if __name__ == "__main__":  # pragma: no cover
    import argparse

    p = argparse.ArgumentParser("tests/evals/plant.py")
    p.add_argument("pack", type=Path)
    p.add_argument("fixture", type=Path)
    p.add_argument("key_dir", type=Path)
    a = p.parse_args()
    key = apply_pack(a.pack, a.fixture, a.key_dir)
    print(f"planted {len(key['defects'])} defects; key outside the tree")
