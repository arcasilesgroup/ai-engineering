"""Score a review skill against a planted defect pack: recall, precision, traps.

Spec 029 / B-029-1. The graded key lives outside the tree (plant.py guarantees it); a skill
is scored on what it reports, never on the key. The three tiers are load-bearing:

- Tier 1 (gimmes) — must be found; prove the skill runs and reports.
- Tier 2 (near-misses) — must be found; prove recall against a skill that only greps.
- Tier 3 (traps) — correct code that pattern-matches a defect; a finding here is a false
  positive and fails precision.

A skill that reports nothing on a non-empty pack is FAIL. A clean control (no defects) that
fires is FAIL (astryx `clean-stays-quiet`). Spec 030 / B-030-2 adds: a pack declaring
coverage roots must not have a reporter reading outside them.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from eval_types import Defect, Key

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "tests" / "evals"
KEY_ROOT = ROOT / ".ai" / "evals"  # .ai/.gitignore begins with `*`: never visible to a skill
WORK_ROOT = ROOT / ".ai" / "evals-work"


@dataclass
class Report:
    skill: str
    pack: str
    total: int = 0
    must_find: int = 0
    found: int = 0
    traps: int = 0
    trap_hits: int = 0
    spurious: int = 0
    clean: bool = False
    findings: list[dict] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def recall(self) -> float:
        return self.found / self.must_find if self.must_find else 1.0

    @property
    def precision(self) -> float:
        denom = (self.found + self.spurious + self.trap_hits) or 1
        return self.found / denom


def _load_reporter(pack: Path):
    """Import the pack's `scan.py` as a module and return its `find_findings`."""
    scan = pack / "scan.py"
    if not scan.is_file():
        raise FileNotFoundError(f"{scan} missing: a pack must ship its reporter")
    spec = importlib.util.spec_from_file_location(f"pack_{pack.name}_scan", scan)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load reporter for {pack.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    find = getattr(module, "find_findings", None)
    if not callable(find):
        raise AttributeError(f"{scan} must define find_findings(root)")
    return find


def _fresh_work(pack_name: str) -> Path:
    """A clean copy of the fixture under WORK_ROOT, cleared of any prior run."""
    shutil.rmtree(WORK_ROOT, ignore_errors=True)
    work = WORK_ROOT / pack_name
    work.mkdir(parents=True, exist_ok=True)
    return work


def _coverage_problem(report: Report, outside: list[str]) -> None:
    report.problems.append(f"finding(s) outside declared coverage roots: {sorted(set(outside))}")


def score_one(pack: Path, fixture: Path) -> Report:
    spec = tomllib.loads((pack / "pack.toml").read_text(encoding="utf-8"))
    report = Report(skill=spec.get("skill", "?"), pack=pack.name, clean=bool(spec.get("clean")))
    find = _load_reporter(pack)

    if report.clean:
        # Clean control: fresh copy, nothing planted, reporter must stay quiet.
        work = _fresh_work(pack.name)
        shutil.copytree(fixture, work, dirs_exist_ok=True)
        report.findings = find(work)
        for _finding in report.findings:
            report.spurious += 1
        if report.findings:
            report.problems.append("fired on a clean control")
        return report

    # Non-clean: plant into a fresh copy with the graded key OUTSIDE the work tree.
    from plant import apply_pack

    work = _fresh_work(pack.name)
    shutil.copytree(fixture, work, dirs_exist_ok=True)
    key: Key = apply_pack(pack, work, KEY_ROOT / pack.name)
    defects: list[Defect] = list(key.get("defects", []))
    report.total = len(defects)
    must = [d for d in defects if d.get("tier") in (1, 2)]
    traps = [d for d in defects if d.get("tier") == 3]
    report.must_find = len(must)
    report.traps = len(traps)

    report.findings = find(work)
    for f in report.findings:
        fp = Path(str(f.get("file", "")))
        if any(fp == Path(str(d["file"])) for d in must):
            report.found += 1
        elif any(fp == Path(str(d["file"])) for d in traps):
            report.trap_hits += 1
        else:
            report.spurious += 1

    # Spec 030 / B-030-2: a pack that declares coverage roots must not have a reporter
    # reading outside them — a finding outside the declared roots is a coverage escape.
    # The pack's coverage is data owned by the pack: write it beside the work and
    # validate findings against that declared set, not the repository's policy dir.
    coverage_roots = spec.get("coverage", {}).get("roots", [])
    if coverage_roots:
        from ai_engineering import coverage as cov

        cov_dir = WORK_ROOT / "coverage"
        cov_dir.mkdir(parents=True, exist_ok=True)
        (cov_dir / f"{pack.name}.toml").write_text(
            'schema = "urn:ai-engineering:coverage:1"\nschema_version = "1"\n\n'
            + "".join(f'roots = ["{r}"]\n' for r in coverage_roots),
            encoding="utf-8",
        )
        outside = [
            f["file"]
            for f in report.findings
            if not cov.may_scan(str(f.get("file", "")), policy_dir=cov_dir)
        ]
        if outside:
            _coverage_problem(report, outside)

    if report.must_find and report.found == 0:
        report.problems.append("reports nothing on a non-empty pack")
    if report.trap_hits:
        report.problems.append(f"{report.trap_hits} finding(s) on tier-3 traps")
    return report


def main(argv: list[str] | None = None) -> int:
    del argv
    packs = sorted(EVALS.glob("packs/*"))
    if not packs:
        print("  no packs under tests/evals/packs/ — the lane measured nothing")
        return 1
    failed = 0
    for pack in packs:
        fixture = EVALS / "fixtures" / pack.name
        if not fixture.is_dir():
            print(f"  no_instrument  {pack.name}: no fixture tree, reason recorded")
            continue
        report = score_one(pack, fixture)
        line = (
            f"  evals {report.skill:>10} pack={report.pack:<22} "
            f"recall={report.recall:.2f} precision={report.precision:.2f} "
            f"(must_find={report.must_find} found={report.found} spurious={report.spurious}"
            f" trap_hits={report.trap_hits})"
        )
        if report.clean:
            line += " · clean control"
        print(line)
        for problem in report.problems:
            print(f"    FAIL {problem}")
            failed += 1
    if failed:
        return 1
    print("RAN evals=pass")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
