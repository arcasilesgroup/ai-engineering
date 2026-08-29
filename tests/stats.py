#!/usr/bin/env python3
"""One table, from the repository, with no model in the loop.

This existed as a paragraph a model retyped after every change, which is rule 12's own
trigger: the same judgement resolving the same way, at the price of a language model doing
arithmetic somebody could have run. Every number below is read from the tree or from an
artifact a gate left behind. None of it is asserted here — the gates already fail — so
this exits zero whatever it finds, and says so, because a report that sometimes fails is a
gate nobody can name.

The one thing it refuses to do is round a stale number up to a current one. Coverage is
not computed here; it is left behind by `just cover`, and an artifact older than the newest
source file it describes is reported STALE rather than reported. A number that was true
last Tuesday is the failure this product is about.

There is no mutation row. A mutation artifact would have to be a file this report quotes,
and quoting `mutants/mutmut-cicd-stats.json` or a recipe that no longer runs is a dash
next to a command nobody can invoke — the failure mode a report whose purpose is refusing
stale numbers must not ship. `just guards` leaves its answer in a `RAN` line and not in an
artifact, and inventing an artifact so this could quote one would be building machinery to
keep a report shaped like a claim rather than like the truth.

Usage: python tests/stats.py [--json]
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lib():
    """The package and the dispatcher, reached the way the dispatcher itself is: by path.
    Imported here rather than at the top because the path has to be set first, and the only
    way to import at the top is a suppression comment, which this repository forbids and
    this very file counts."""
    for folder in ("src", "hooks"):
        if str(ROOT / folder) not in sys.path:
            sys.path.insert(0, str(ROOT / folder))
    import chain

    from ai_engineering import contract, text

    return contract, text, chain


SUPPRESSION = re.compile(
    r"#\s*(noqa|nosec|type:\s*ignore|fmt:\s*off|pragma:\s*no\s*cover)"
    r"|//\s*(@ts-ignore|nolint|NOSONAR|eslint-disable)"
)
BUCKETS = {
    "tests": ("tests/",),
    "product": ("src/", "hooks/"),
    "policy and surfaces": ("policy/", "surfaces/", "git-hooks/", "migrations/"),
    "ci": (".github/",),
}


def newest_source() -> float:
    """The clock every derived artifact is judged against."""
    contract, _, _ = lib()
    return max(
        (ROOT / name).stat().st_mtime
        for name in contract.tracked(ROOT)
        if name.startswith(("src/", "hooks/", "tests/")) and (ROOT / name).exists()
    )


def freshness(*artifacts: Path) -> str:
    """Judged on the oldest of them, and that is the whole point. `coverage xml` rewrites
    the report from a `.coverage` that may be hours old, so reading the report's own
    timestamp calls a number fresh because it was rendered recently rather than because it
    was measured recently. The data file is the clock; the rendering is not."""
    present = [a for a in artifacts if a.exists()]
    if not present:
        return "not measured"
    return "STALE" if min(a.stat().st_mtime for a in present) < newest_source() else "fresh"


def coverage() -> tuple[str, str]:
    report = ROOT / "coverage.xml"
    state = freshness(report, ROOT / ".coverage")
    if state == "not measured":
        return "—", "run `just cover`"
    if not report.exists():
        return "—", "measured, not rendered — `coverage xml`"
    found = re.search(r'line-rate="([\d.]+)"', report.read_text(errors="replace"))
    return (f"{float(found.group(1)) * 100:.0f}%" if found else "?"), state


def suppressions() -> list[str]:
    contract, _, _ = lib()
    found = []
    for name in contract.tracked(ROOT):
        if name == "policy/semgrep.yml":
            continue  # a rule cannot be scanned by itself, and only that one is exempt
        try:
            body = (ROOT / name).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        found += [
            f"{name}:{n}" for n, line in enumerate(body.splitlines(), 1) if SUPPRESSION.search(line)
        ]
    return found


def committed_specs(names: list[str]) -> list[Path]:
    """From the index, never the filesystem. The acceptance register reads the working
    tree, which is right for the verb — a risk you are about to accept is still a risk — and
    wrong here: every other number on this page comes from `git ls-files`, and one row
    counting a draft that no reviewer has seen is two questions printed as one table."""
    return [ROOT / n for n in names if n.startswith("specs/") and n.endswith("spec.md")]


def record(names: list[str]) -> tuple[int, int, int, list[str]]:
    today = date.today().isoformat()
    decisions = accepted = 0
    expired = []
    _, text, _ = lib()
    for spec in committed_specs(names):
        for block in text.yaml_blocks(spec.read_text(errors="replace")):
            if "decision" in block:
                decisions += 1
            if "expires" in block and "finding" in block:
                accepted += 1
                if str(block["expires"]) < today:
                    expired.append(f"{block.get('id', '?')} expired {block['expires']}")
    return len(committed_specs(names)), decisions, accepted, expired


def gather() -> dict:
    contract, text, chain = lib()
    names = contract.tracked(ROOT)
    tests, product = contract.test_ratio(ROOT)
    surfaces = tomllib.loads((ROOT / "policy" / "surfaces.toml").read_text())["surface"]
    skills = sorted((ROOT / ".agents" / "skills").glob("ai-*/SKILL.md"))
    specs, decisions, accepted, expired = record(names)

    return {
        "governance": {
            "test_lines": tests,
            "product_lines": product,
            "ratio": round(tests / product, 2),
            "ratio_max": contract.TEST_RATIO_MAX,
            "doctrine_lines": len((ROOT / "AGENTS.md").read_text().splitlines()),
            "skills": len(skills),
            "longest_skill": max(len(s.read_text().splitlines()) for s in skills),
            "skill_problems": contract.audit(ROOT / ".agents" / "skills"),
            "specs": specs,
            "decisions": decisions,
            "risk_acceptances": accepted,
            "expired_risks": expired,
        },
        "quality": {
            "coverage": coverage(),
            "tests_collected": len(
                re.findall(
                    r"^def test_",
                    "\n".join(
                        (ROOT / n).read_text(errors="replace")
                        for n in names
                        if n.startswith("tests/")
                    ),
                    re.M,
                )
            ),
            "adversarial_cases": len(
                re.findall(
                    r"^@case\(", (ROOT / "tests" / "adversarial" / "run.py").read_text(), re.M
                )
            ),
            "shape": {
                label: contract.count(ROOT, [n for n in names if n.startswith(pref)])
                for label, pref in BUCKETS.items()
            },
        },
        "security": {
            "guards": sum(
                1
                for rows in chain.TABLE.values()
                for name, _ in rows
                if name not in chain.TELEMETRY
            ),
            "telemetry": len(chain.TELEMETRY),
            "surfaces": len(surfaces),
            # Counted from receipts, because the flag that used to answer this was a
            # thing we typed. A surface is proven when a denial executed there.
            "proven": len(_enforced()),
            "suppressions": suppressions(),
        },
    }


def _enforced() -> set[str]:
    """The surfaces whose enforcement receipt proved, read the way the product reads it."""

    sys.path.insert(0, str(ROOT / "src"))
    from datetime import UTC, datetime

    from ai_engineering import surface

    return {
        row.surface
        for row in surface.read(ROOT, now=datetime.now(UTC)).rows
        if row.state == "enforcement" and row.outcome == "PASS" and row.code == surface.PROVEN
    }


def show(data: dict) -> None:
    g, q, s = data["governance"], data["quality"], data["security"]
    print("\n  GOVERNANCE")
    print(
        f"    test ratio       {g['ratio']}x / {g['ratio_max']}x   "
        f"({g['test_lines']} test, {g['product_lines']} product)"
    )
    print(f"    doctrine         {g['doctrine_lines']} lines")
    print(
        f"    skills           {g['skills']}, longest {g['longest_skill']} lines"
        f"{'' if not g['skill_problems'] else '   ' + str(len(g['skill_problems'])) + ' PROBLEMS'}"
    )
    print(
        f"    record           {g['specs']} specs, {g['decisions']} decisions, "
        f"{g['risk_acceptances']} accepted risks"
    )
    for line in g["expired_risks"]:
        print(f"      EXPIRED        {line}")

    print("\n  QUALITY")
    value, state = q["coverage"]
    mark = "" if state == "fresh" else f"   <- {state}"
    print(f"    {'coverage':<16} {value}{mark}")
    print(
        f"    tests            {q['tests_collected']} functions, "
        f"{q['adversarial_cases']} adversarial cases"
    )
    print("    lines by kind    " + ", ".join(f"{k} {v}" for k, v in q["shape"].items()))

    print("\n  SECURITY")
    print(f"    hooks            {s['guards']} guard rows, {s['telemetry']} telemetry")
    print(f"    surfaces         {s['proven']} of {s['surfaces']} proven — the rest are paper")
    print(f"    suppressions     {len(s['suppressions'])}")
    for line in s["suppressions"][:10]:
        print(f"      {line}")
    print("\n  Nothing here fails. The gates do that; this only says where things stand.\n")


if __name__ == "__main__":
    body = gather()
    print(json.dumps(body, indent=2, default=str)) if "--json" in sys.argv else show(body)
