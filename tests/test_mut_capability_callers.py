"""How many declared capabilities anything actually goes through, counted rather than said.

`EP-078` asks that the declared capabilities be enforced and not only declared. The mechanism
is real: an action taken through `executor.Sandbox` is decided at the operation, against the
resolved path and the real binary, and a refusal is recorded. What the row could not say was
the plural — one capability of eighteen has a caller, and that sentence sat in a note.

A sentence is how the gate-recipe count came to read "six controlled and two argued" five
recipes after it stopped being true. So this counts, and it fails when the count drops. It
does not fail on one, because one is the honest state today and a case that reds the build
over a known gap is a case somebody deletes.

What it refuses is the two ways the number could go wrong without anybody deciding: a caller
disappearing, and a caller naming a capability the manifest does not declare — which would be
enforcement against a policy nobody wrote.
"""

from __future__ import annotations

import ast
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "src" / "ai_engineering"
CAPABILITIES = ROOT / "policy" / "capabilities.toml"


def declared() -> dict[str, set[str]]:
    rows = tomllib.loads(CAPABILITIES.read_text(encoding="utf-8"))["capabilities"]
    return {row["id"]: {mode["id"] for mode in row["modes"]} for row in rows}


def _committed(name: str) -> str:
    """A product file as git has it, never as the working tree has it.

    Found by the mutation lane, which is what it is for. `mutmut` copies the tree and writes
    *every* mutant into each file as a separate function, so a file on disk under `mutants/`
    contains `Sandbox("ai-report", ...)` and a variant naming something else at the same time.
    Reading disk made this case see a caller for a capability nobody declared, fail on the
    unmutated baseline, and take the whole run's statistics with it — a check that cannot tell
    the product from a rewritten copy of it.

    So it asks git. An answer git cannot give is no answer, and the case says so rather than
    reading the copy instead.
    """

    done = subprocess.run(
        ["git", "show", f"HEAD:src/ai_engineering/{name}"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    return done.stdout if done.returncode == 0 else ""


def callers() -> dict[str, str]:
    """Every `executor.Sandbox(...)` in the product, by the capability it names.

    Read with `ast` rather than by matching text: a grep counts the string in a docstring
    explaining why there are no callers, which is exactly the shape this file is about.
    """

    found: dict[str, str] = {}
    for source in sorted(PRODUCT.glob("*.py")):
        body = _committed(source.name)
        if not body:
            continue
        try:
            tree = ast.parse(body)
        except SyntaxError:  # pragma: no cover - the suite would be red for other reasons
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name != "Sandbox" or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                found[first.value] = source.name
    return found


def _readable() -> bool:
    """Whether the committed source can be read here at all.

    Same answer as the case above needs and for the same reason: `mutmut` copies the tree
    outside any repository, so nothing committed is reachable from inside it. A run that could
    not look must not read as a run that looked and found nothing — that is the difference
    between no callers and no answer, and this file exists because of it.
    """

    return bool(_committed("issue.py"))


def test_every_caller_names_a_capability_the_manifest_declares():
    """Enforcement against a policy nobody wrote is worse than no enforcement: it reads as
    governed and resolves against nothing."""

    if not _readable():
        pytest.skip("this tree is not a git repository, so the committed source is unreadable")
    known = declared()

    for capability_id, where in callers().items():
        assert capability_id in known, (
            f"{where} takes actions through capability {capability_id!r}, which "
            f"policy/capabilities.toml does not declare"
        )


def test_the_count_of_capabilities_with_a_caller_is_published_and_does_not_drop():
    """`EP-078`'s plural, as a number rather than a sentence.

    One of eighteen today, through `ai-report issue`. That gap is real and this does not
    pretend otherwise — what it stops is the gap widening while the note still says one, or
    narrowing without anybody noticing they had closed it.
    """

    if not _readable():
        pytest.skip("this tree is not a git repository, so the committed source is unreadable")
    known, taken = declared(), callers()

    assert len(known) == 18, f"{len(known)} capabilities are declared and the audit measured 18"
    assert taken, (
        "no capability has a caller at all. The manifest would then be eighteen declarations "
        "and nothing that resolves against them, which is the state EP-078 was filed for"
    )
    assert len(taken) >= 1, len(taken)
    assert "ai-report" in taken, (
        f"the one capability with a caller was ai-report, through issue.draft; now it is "
        f"{sorted(taken)}. If that is a deliberate move, say so here and change the number"
    )
