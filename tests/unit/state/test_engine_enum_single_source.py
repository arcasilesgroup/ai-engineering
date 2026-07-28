"""Lock the ``ALLOWED_ENGINES`` sites against drift (spec-201 D-201-06).

``ALLOWED_EVENT_KINDS`` has had a symmetric-difference drift guard since
spec-137 (``test_event_kinds_single_source.py``). ``ALLOWED_ENGINES`` had
**none** — it is duplicated across the package authority and the
stdlib-only hook mirror with nothing but discipline holding them
together, which is exactly how the kind drift spec-137 repaired happened.

Sites guarded here:

1. ``tools/skill_domain/event_schema.py`` — ``ALLOWED_ENGINES`` (authority).
2. ``.ai-engineering/scripts/hooks/_lib/hook-common.py`` — ``_ALLOWED_ENGINES``.
3. ``.ai-engineering/scripts/hooks/_lib/observability.py`` — ``_ALLOWED_ENGINES``,
   added by spec-201 T-2.8 so the busiest hook-side writer stops accepting
   any engine string at all. A third copy is only acceptable because this
   guard covers it, exactly as the kinds already do.

The hook-side files cannot import the package authority (stdlib-only
constraint, and ``hook-common.py`` is not even a legal module name), so
the contract enforced is *membership equality* over the parsed literals,
not import identity.

A further guard walks ``_lib/hook_context.py`` and asserts that every engine
literal that detection ladder can produce — including the terminal
``unknown`` fallback — is admitted by the authority. A detector that can
emit a label the validator refuses is a silent event-loss bug, which is
the defect D-201-06 names.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from tests.unit.state.test_event_kinds_single_source import _extract_frozenset_literal

REPO_ROOT = Path(__file__).resolve().parents[3]

AUTHORITY = REPO_ROOT / "tools" / "skill_domain" / "event_schema.py"
HOOKS_LIB = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib"
MIRROR_HOOK_COMMON = HOOKS_LIB / "hook-common.py"
MIRROR_OBSERVABILITY = HOOKS_LIB / "observability.py"
HOOK_CONTEXT = HOOKS_LIB / "hook_context.py"

# spec-201 D-201-06: the two values the closed enum was missing.
_SPEC_201_ADDITIONS: frozenset[str] = frozenset({"openai_compatible", "unknown"})

# Detection-ladder labels that must never disappear from hook_context.py
# without this guard noticing (a silent extraction failure would otherwise
# leave the ladder assertion trivially green).
_EXPECTED_LADDER_LITERALS: frozenset[str] = frozenset(
    {"claude_code", "codex", "antigravity", "unknown"}
)


def _load_authority() -> ModuleType:
    """Load the authoritative schema module by path (Pydantic-free)."""
    spec = importlib.util.spec_from_file_location("_test_engine_enum_authority", str(AUTHORITY))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_engines_from_authority() -> frozenset[str]:
    engines = _load_authority().ALLOWED_ENGINES
    assert isinstance(engines, frozenset)
    return engines


def _top_level_str_constants(value: ast.expr) -> set[str]:
    """Return the string constants an expression can yield *directly*.

    Only the expression itself and the operands of a boolean / conditional
    expression count. Constants buried in call arguments (e.g. the
    ``"AIENG_HOOK_ENGINE"`` in ``os.environ.get("AIENG_HOOK_ENGINE", "")``)
    are env-var *names*, not engine labels, and must not be collected.
    """
    if isinstance(value, ast.Constant):
        return {value.value} if isinstance(value.value, str) and value.value else set()
    if isinstance(value, ast.BoolOp):
        collected: set[str] = set()
        for operand in value.values:
            collected |= _top_level_str_constants(operand)
        return collected
    if isinstance(value, ast.IfExp):
        return _top_level_str_constants(value.body) | _top_level_str_constants(value.orelse)
    return set()


def _engine_literals_from_hook_context() -> frozenset[str]:
    """Collect every engine label ``_lib/hook_context.py`` can produce.

    Parsed rather than executed: the detection ladder branches on env vars
    and filesystem markers, so exercising every arm would need eight
    fixtures to assert one property. The AST walk covers assignments to a
    name ``engine`` and every ``return`` inside a function whose name
    mentions ``engine``.
    """
    tree = ast.parse(HOOK_CONTEXT.read_text(encoding="utf-8"))
    literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "engine":
                    literals |= _top_level_str_constants(node.value)
        elif isinstance(node, ast.FunctionDef) and "engine" in node.name:
            for inner in ast.walk(node):
                if isinstance(inner, ast.Return) and inner.value is not None:
                    literals |= _top_level_str_constants(inner.value)
    return frozenset(literals)


@pytest.mark.parametrize("mirror", [MIRROR_HOOK_COMMON, MIRROR_OBSERVABILITY], ids=lambda p: p.name)
def test_engine_enum_mirrors_agree_with_authority(mirror: Path) -> None:
    """Authority and every hook-side mirror hold identical engine membership."""
    authority = _load_engines_from_authority()
    parsed = _extract_frozenset_literal(mirror, "_ALLOWED_ENGINES")

    drift = authority.symmetric_difference(parsed)

    assert not drift, (
        f"{mirror.name} mirror has drifted from authoritative ALLOWED_ENGINES: {sorted(drift)}"
    )


def test_engine_enum_admits_spec_201_additions() -> None:
    """D-201-06: the closed enum admits ``openai_compatible`` and ``unknown``."""
    authority = _load_engines_from_authority()
    mirror_hook_common = _extract_frozenset_literal(MIRROR_HOOK_COMMON, "_ALLOWED_ENGINES")

    assert authority >= _SPEC_201_ADDITIONS, (
        f"authority is missing {sorted(_SPEC_201_ADDITIONS - authority)}; "
        "every foreign-harness event is refused until it is admitted"
    )
    assert mirror_hook_common >= _SPEC_201_ADDITIONS, (
        f"hook-common mirror is missing {sorted(_SPEC_201_ADDITIONS - mirror_hook_common)}"
    )


def test_hook_context_ladder_produces_only_admitted_engines() -> None:
    """Every label the detection ladder can emit must validate (D-201-06).

    ``_lib/hook_context.py`` terminates its ladder at the literal
    ``unknown``. Before spec-201 the authority refused that value, so a
    host with no marker produced events the validator dropped — 100% loss,
    not mislabelling.
    """
    authority = _load_engines_from_authority()
    ladder = _engine_literals_from_hook_context()

    assert ladder >= _EXPECTED_LADDER_LITERALS, (
        f"engine-literal extraction from {HOOK_CONTEXT.name} went blind: expected at least "
        f"{sorted(_EXPECTED_LADDER_LITERALS)}, extracted {sorted(ladder)}"
    )
    unadmitted = ladder - authority
    assert not unadmitted, (
        f"{HOOK_CONTEXT.name} can produce engine labels the schema refuses: {sorted(unadmitted)}"
    )


def test_brief_drafted_event_validates_against_authority() -> None:
    """D-201-07 + D-201-06 together: the new kind and the new engine validate."""
    module = _load_authority()
    event = {
        "kind": "brief_drafted",
        "engine": "openai_compatible",
        "timestamp": "2026-07-27T00:00:00Z",
        "component": "ai-spec-draft",
        "outcome": "success",
        "correlationId": "c-201",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "detail": {"topic": "event-plane-identity"},
    }
    assert module.validate_event_schema(event) is True
