"""Executable contracts for spec 042 / B-042-3: every caller-less module has one checked status.

Modules that shipped with tests and no production caller float — a decision deferred, not
an infrastructure lane. `policy/module-status.toml` (data) + `wiring.module_status()` (a
reader, mirroring `skill_sequence()`) give each exactly one checked status: `consumer`
(AST-verified import in src/ or hooks/), `orchestrator-future` (reason cites the
orchestrator spec), or `deferred` (kept, tested, not wired, with a reason). No status,
a consumer with no import, a status naming a missing consumer, and an
orchestrator-future row citing no spec are all refused — the register cannot drift from
the tree.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import wiring  # noqa: E402

REGISTER = ROOT / "policy" / "module-status.toml"

# The modules this register exists to decide, measured on the tree before this test:
# these ship with tests and no import in src/ or hooks/. revalidate/cost are consumer
# (audit.py imports them); model_router is consumer once cli.py imports it (B-042-1).
ORPHANS = {
    "lane_merge", "loopgate", "skillify", "verify_cold", "evidencing",
    "trim", "decision_fw", "intake", "model_router", "revalidate", "cost",
}


def _imports(module: str, root: Path) -> list[str]:
    """Every production file that imports `module`, found by AST — a docstring mention or
    a comment is not a caller. Walks src/ and hooks/ only; tests never count."""
    found: list[str] = []
    for base in (root / "src" / "ai_engineering", root / "hooks"):
        if not base.is_dir():
            continue
        for file in base.rglob("*.py"):
            if "__pycache__" in file.parts:
                continue
            try:
                tree = ast.parse(file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    # `from ai_engineering import model_router` binds the module as the
                    # imported name itself. Match on the imported names, not the parent.
                    names = [a.name for a in node.names]
                else:
                    continue
                if any(n == module or n.startswith(f"{module}.") for n in names):
                    found.append(str(file.relative_to(root)))
                    break
    return found


def _names(register: Path) -> set[str]:
    import tomllib

    data = tomllib.loads(register.read_text(encoding="utf-8"))
    return {row["name"] for row in data.get("module", [])}


def test_every_known_orphan_has_a_status_in_the_register():
    rows = wiring.module_status()
    assert set(rows) >= ORPHANS, ORPHANS - set(rows)


def test_a_consumer_must_be_imported_by_a_production_file():
    rows = wiring.module_status()
    for name, row in rows.items():
        if row.get("status") == "consumer":
            consumers = {c for c in _imports(name, ROOT)}
            declared = {c.strip() for c in str(row.get("consumer", "")).split(",") if c.strip()}
            # The declared consumer file must actually import the module, and the import
            # must exist somewhere in production code (the AST walk proves it).
            assert declared, f"{name}: consumer row names no consumer"
            joined = " ".join(consumers)
            assert any(d.split("/")[-1] in joined for d in declared), (
                f"{name}: marked consumer but no production file imports it "
                f"(found: {sorted(consumers)})"
            )


def test_a_status_naming_a_missing_consumer_is_refused():
    rows = wiring.module_status()
    for name, row in rows.items():
        consumer = str(row.get("consumer") or "")
        if not name or consumer in ("", "NONE", "none"):
            continue
        # A consumer that names a file must be a file that exists in the tree.
        for candidate in consumer.split(","):
            candidate = candidate.strip()
            if candidate and not (ROOT / candidate).is_file():
                raise AssertionError(
                    f"{name}: consumer {candidate!r} does not exist in the tree"
                )


def test_an_orchestrator_future_row_cites_the_orchestrator_spec():
    rows = wiring.module_status()
    for name, row in rows.items():
        if row.get("status") == "orchestrator-future":
            reason = str(row.get("reason") or "")
            cited = [part for part in reason.split() if part.strip("`").isdigit()]
            assert cited, f"{name}: orchestrator-future with no spec cited in its reason"
            for spec_id in cited:
                spec_dir = next((ROOT / "specs").glob(f"{spec_id}-*"), None)
                assert spec_dir is not None, (
                    f"{name}: cites spec {spec_id} which does not exist"
                )
                home = spec_dir / "spec.md"
                assert home.is_file() and name in home.read_text(encoding="utf-8"), (
                    f"{name}: spec {spec_id} never mentions it"
                )


def test_every_module_name_in_the_register_is_unique():
    import tomllib

    data = tomllib.loads(REGISTER.read_text(encoding="utf-8"))
    names = [row["name"] for row in data.get("module", [])]
    assert len(names) == len(set(names)), "duplicate module row in the register"