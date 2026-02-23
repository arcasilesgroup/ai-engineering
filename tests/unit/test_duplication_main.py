"""Coverage for duplication checker CLI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

from ai_engineering.policy import duplication


def test_window_hashes_short_input() -> None:
    assert duplication._window_hashes(["a", "b"], width=8) == []


def test_main_pass_and_fail(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("\n".join(f"v{i}=1" for i in range(20)), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["dup", "--path", str(src), "--threshold", "100"])
    assert duplication.main() == 0

    block = "\n".join(["x=1", "x+=1", "x+=2", "x+=3"] * 3)
    (src / "b.py").write_text(block, encoding="utf-8")
    (src / "c.py").write_text(block, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dup", "--path", str(src), "--threshold", "0"])
    assert duplication.main() == 1
