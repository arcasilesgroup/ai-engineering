"""The harness contract for spec 029 / B-029-1. The engine and the fixtures.

What the harness proves, and why the form matters: a review skill is scored against planted
defects whose graded key lives OUTSIDE the tree (graph-engineering's rule — a review that
finds bugs by reading the list of planted bugs proves nothing). Recall is over Tier 1+2
defects that must be found; Tier 3 traps (correct code that looks like a defect) must not
fire; a clean control with no defects must stay quiet (astryx `clean-stays-quiet`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "tests" / "evals"
PACKS = EVALS / "packs"

if str(EVALS) not in sys.path:
    sys.path.insert(0, str(EVALS))

import plant  # noqa: E402
import score  # noqa: E402


def _mk_pack(root: Path, name: str, toml: str, reporter: str) -> Path:
    pack = root / name
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "pack.toml").write_text(toml, encoding="utf-8")
    (pack / "scan.py").write_text(reporter, encoding="utf-8")
    return pack


def test_plant_writes_the_key_outside_the_tree(tmp_path):
    """The graded answer key must not be reachable from the mutated fixture."""
    fixture = tmp_path / "fixture"
    (fixture / "src").mkdir(parents=True)
    (fixture / "src" / "app.py").write_text("TOKEN = 'keep'\n", encoding="utf-8")
    pack = _mk_pack(
        tmp_path,
        "demo",
        'skill = "demo"\nreporter = "scan.py"\nclean = false\n\n[[defects]]\n'
        'id = "d1"\ntier = 2\nfile = "src/app.py"\nfind = "keep"\nreplace = "leak"\n',
        "def find_findings(root):\n    return []\n",
    )
    key_dir = tmp_path / "graded-outside"
    plant.apply_pack(pack, fixture, key_dir)
    assert (key_dir / "demo.json").exists()
    # The key's own copy is not under the fixture.
    assert not (fixture / "demo.json").exists()
    assert "leak" in (fixture / "src" / "app.py").read_text()


def test_plant_refuses_an_in_tree_key(tmp_path):
    """A key inside the fixture is the exact false-green the harness refuses."""
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    pack = _mk_pack(
        tmp_path,
        "demo",
        'skill = "demo"\nreporter = "scan.py"\nclean = false\n\n[[defects]]\n'
        'id = "d1"\ntier = 2\nfile = "src/app.py"\nfind = "keep"\nreplace = "leak"\n',
        "def find_findings(root):\n    return []\n",
    )
    (fixture / "src").mkdir()
    (fixture / "src" / "app.py").write_text("TOKEN='keep'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="outside the fixture"):
        plant.apply_pack(pack, fixture, fixture / ".graded")


def test_recall_counts_tier12_and_precision_punishes_traps(tmp_path):
    """plant + score over a two-file pack (must + trap): what the engine must measure."""
    fixture = tmp_path / "fixture"
    (fixture / "src").mkdir(parents=True)
    (fixture / "src" / "app.py").write_text(
        "import os\nCTX = os.getenv('APP_SECRET')\n", encoding="utf-8"
    )
    (fixture / "src" / "helper.py").write_text("ok = True\n", encoding="utf-8")
    pack = _mk_pack(
        tmp_path,
        "demo-pair",
        'skill = "demo-sk"\nreporter = "scan.py"\nclean = false\n\n'
        '[[defects]]\nid = "t2"\ntier = 2\nfile = "src/app.py"\n'
        'find = "os.getenv"\nreplace = "os.environ"\n\n'
        '[[defects]]\nid = "t3"\ntier = 3\nfile = "src/helper.py"\n'
        'find = "ok"\nreplace = "okay"\n',
        "from pathlib import Path\n"
        "def find_findings(root):\n"
        "    out = []\n"
        "    for p in (root / 'src').glob('*.py'):\n"
        "        src = p.read_text()\n"
        "        if 'os.environ' in src:\n"
        "            out.append({'file': 'src/app.py', 'finding': 'env'})\n"
        "        if 'okay' in src:\n"
        "            out.append({'file': 'src/helper.py', 'finding': 'trap'})\n"
        "    return out\n",
    )
    report = score.score_one(pack, fixture)
    assert report.must_find == 1
    assert report.found == 1  # the tier-2 defect (unique file) is found
    assert report.trap_hits == 1  # the trap fired: precision suffers
    assert report.recall == 1.0
    assert report.precision < 1.0
    assert any("trap" in p for p in report.problems)


def test_clean_control_must_stay_quiet(tmp_path):
    """astryx `clean-stays-quiet`: no defects planted, a finding is a false positive."""
    fixture = tmp_path / "fixture"
    (fixture / "src").mkdir(parents=True)
    (fixture / "src" / "app.py").write_text("ok = True\n", encoding="utf-8")
    pack = _mk_pack(
        tmp_path,
        "clean",
        'skill = "clean-sk"\nreporter = "scan.py"\nclean = true\n',
        "from pathlib import Path\n"
        "def find_findings(root):\n"
        "    return [{'file': 'src/app.py', 'finding': 'noise'}] "
        "if (root / 'src' / 'app.py').exists() else []\n",
    )
    report = score.score_one(pack, fixture)
    assert report.clean
    assert any("clean control" in p for p in report.problems)


def test_main_exits_nonzero_when_a_skill_reports_nothing(tmp_path):
    """A skill reporting nothing on a non-empty pack is FAIL (B-029-1)."""
    fixture = tmp_path / "fixture"
    (fixture / "src").mkdir(parents=True)
    (fixture / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    pack = _mk_pack(
        tmp_path,
        "silent",
        'skill = "silent"\nreporter = "scan.py"\nclean = false\n\n'
        '[[defects]]\nid = "d1"\ntier = 1\nfile = "src/app.py"\nfind = "x"\nreplace = "y"\n',
        "def find_findings(root):\n    return []\n",
    )
    report = score.score_one(pack, fixture)
    assert report.must_find == 1
    assert report.found == 0
    assert any("reports nothing" in p for p in report.problems)


def test_the_lane_refuses_without_packs(tmp_path, monkeypatch, capsys):
    """`just evals` is a lane: without packs it must refuse, not pass silently."""
    monkeypatch.setattr(score, "EVALS", tmp_path / "empty")
    assert score.main([]) == 1
    assert "no packs" in capsys.readouterr().out

def test_a_reporter_reading_outside_declared_coverage_is_refused(tmp_path):
    """Spec 030 / B-030-2: a pack whose reporter reads outside its coverage roots fails."""
    fixture = tmp_path / "fixture"
    (fixture / "src").mkdir(parents=True)
    (fixture / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (fixture / "outside.py").write_text("y = 2\n", encoding="utf-8")
    pack = _mk_pack(
        tmp_path,
        "out-of-coverage",
        'skill = "demo"\nreporter = "scan.py"\nclean = false\n\n'
        "[coverage]\nroots = [\"src\"]\n\n"
        '[[defects]]\nid = "d1"\ntier = 1\nfile = "src/app.py"\nfind = "x"\nreplace = "y"\n',
        "from pathlib import Path\n"
        "def find_findings(root):\n"
        "    out = []\n"
        "    for p in (root).glob('*.py'):\n"
        "        if 'y = 2' in p.read_text():\n"
        "            out.append({'file': 'outside.py', 'finding': 'escaped'})\n"
        "    return out\n",
    )
    report = score.score_one(pack, fixture)
    assert any("coverage" in p for p in report.problems), report.problems
