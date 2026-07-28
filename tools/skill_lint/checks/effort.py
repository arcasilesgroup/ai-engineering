"""effort checker — spec-131 S3 (sub-003) / spec-189 (D-189-04) contract.

Every SKILL.md must declare ``effort:`` in its YAML frontmatter, drawn
from the closed vocabulary ``effort: cheap | mid | high`` (D-131-08).
Per spec-189 (D-189-04) ``effort`` is the SOLE skill dispatch axis; the
legacy per-model tier field is retired fleet-wide.

Posture:

* ``effort:`` enforcement is blocking. Missing field or invalid enum →
  MAJOR.

In addition the declaration is cross-checked against
``.ai-engineering/reference/model-dispatch-policy.md`` (SSOT). Mismatch
surfaces as MAJOR. The policy doc is parsed once via ``load_policy`` and
threaded through the driver to avoid per-skill re-reads.

Pure stdlib (re + pathlib + dataclasses). Returns ``RubricResult``
records identical in shape to ``no_nested_refs.py`` /
``principles.py`` so the existing CLI rendering pipeline picks them
up without translation. The driver returns
``[(skill_md_path, RubricResult), ...]`` matching the
``check_principles_citations`` shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}

# Closed vocabulary (D-131-08). ``effort`` is the sole skill dispatch axis
# (spec-189 D-189-04).
VALID_EFFORTS: frozenset[str] = frozenset({"cheap", "mid", "high"})

# Allow-listed mirror gaps. The .github surface may omit any Claude-Code-only
# skill (``copilot_compatible: false``); the driver tolerates such absences
# without flagging them. No skill currently uses this scoping.
GITHUB_MIRROR_ALLOWLIST: frozenset[str] = frozenset()


# Frontmatter delimiter regex — reuses the pair_aware shape.
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
# Field line: ``key: value`` with optional inline comment. Value captured
# verbatim; quoting (``"value"`` or ``'value'``) stripped downstream.
_FIELD_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.+?)\s*$", re.MULTILINE)
# Policy table row: pipe-delimited markdown ``| ai-<skill> | <effort> | ... |``
# with leading whitespace tolerance. Trailing columns (Rationale) are
# tolerated by the ``.*\|`` tail. CRITICAL (spec-189 D-189-04): this
# 2-column shape MUST stay in lockstep with the SSOT policy table column
# count — a 3-column regex against a 2-column table (or vice versa) makes
# ``findall`` return zero rows, silently marking every skill "not in policy".
_POLICY_ROW_RE = re.compile(
    r"^\|\s*(ai-[\w-]+)\s*\|\s*(cheap|mid|high)\s*\|.*\|\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class RubricResult:
    """Outcome of running one effort-lint sub-check against a skill."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


# ---------------------------------------------------------------------------
# Policy loader (SSOT = .ai-engineering/reference/model-dispatch-policy.md)
# ---------------------------------------------------------------------------


def load_policy(policy_path: Path) -> dict[str, str]:
    """Parse the model-dispatch policy markdown into ``{skill: effort}``.

    The expected shape is a markdown table whose rows match
    ``_POLICY_ROW_RE``. Header / separator rows that fall outside the
    pattern are silently skipped. Returns an empty dict when the file
    does not exist (lint surfaces the absence at call-site instead).
    """
    if not policy_path.is_file():
        return {}
    text = policy_path.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for skill, effort in _POLICY_ROW_RE.findall(text):
        out[skill] = effort
    return out


# ---------------------------------------------------------------------------
# Frontmatter extraction
# ---------------------------------------------------------------------------


def _read_frontmatter(skill_md: Path) -> dict[str, str]:
    """Return the YAML frontmatter as a flat ``{key: value}`` mapping.

    Handles only the subset we care about (scalar string values for the
    ``effort`` key). Quoted values have their outer quotes stripped.
    Returns an empty dict when the file is missing or has no frontmatter —
    call-site decides how to surface that.
    """
    if not skill_md.is_file():
        return {}
    text = skill_md.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.search(text)
    if not match:
        return {}
    fm_text = match.group(1)
    out: dict[str, str] = {}
    for key, value in _FIELD_RE.findall(fm_text):
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        out[key] = value
    return out


# ---------------------------------------------------------------------------
# Per-field checks
# ---------------------------------------------------------------------------


def _check_effort_declared(fm: dict[str, str]) -> RubricResult:
    value = fm.get("effort")
    if value is None:
        return RubricResult(
            "effort_declared",
            "MAJOR",
            "frontmatter missing required field `effort:` (cheap | mid | high)",
        )
    if value not in VALID_EFFORTS:
        return RubricResult(
            "effort_declared",
            "MAJOR",
            f"effort {value!r} not in {sorted(VALID_EFFORTS)} (D-131-08)",
        )
    return RubricResult(
        "effort_declared",
        "OK",
        f"effort: {value}",
    )


def _check_effort_policy_match(
    fm: dict[str, str],
    policy_effort: str | None,
) -> RubricResult:
    if policy_effort is None:
        return RubricResult(
            "effort_policy_match",
            "MINOR",
            "skill not listed in .ai-engineering/reference/model-dispatch-policy.md (advisory)",
        )
    declared = fm.get("effort")
    if declared is None:
        return RubricResult(
            "effort_policy_match",
            "MAJOR",
            f"cannot match policy ({policy_effort}) — effort missing",
        )
    if declared != policy_effort:
        return RubricResult(
            "effort_policy_match",
            "MAJOR",
            f"declared effort {declared!r} != policy {policy_effort!r}",
        )
    return RubricResult(
        "effort_policy_match",
        "OK",
        f"declared effort matches policy ({policy_effort})",
    )


# ---------------------------------------------------------------------------
# Per-skill driver
# ---------------------------------------------------------------------------


def check_effort(
    skill_md: Path,
    policy: dict[str, str],
) -> list[RubricResult]:
    """Run the two sub-checks against a single SKILL.md path.

    Returns a list of ``RubricResult`` records — one per sub-check
    (``effort_declared``, ``effort_policy_match``). ``CRITICAL`` is
    returned only when the file itself is unreadable.
    """
    if not skill_md.is_file():
        return [
            RubricResult(
                "effort_declared",
                "CRITICAL",
                f"SKILL.md not found at {skill_md}",
            )
        ]
    fm = _read_frontmatter(skill_md)
    skill_slug = skill_md.parent.name
    policy_effort = policy.get(skill_slug)
    return [
        _check_effort_declared(fm),
        _check_effort_policy_match(fm, policy_effort),
    ]


# ---------------------------------------------------------------------------
# Skills-root driver
# ---------------------------------------------------------------------------


def check_all_skills(
    skills_root: Path,
    policy: dict[str, str],
) -> list[tuple[Path, RubricResult]]:
    """Walk every ``<skills_root>/ai-*/SKILL.md`` and run the contract.

    Returns ``[(skill_md_path, result), ...]`` sorted by path so CI
    output stays stable. A Claude-Code-only skill absent from
    ``.agents/skills/`` is an allow-listed gap: if the skill is absent
    under the walked root, no result rows are emitted for it (the other
    tree is responsible for surfacing the absence if applicable).
    """
    if not skills_root.is_dir():
        raise FileNotFoundError(f"skills root {skills_root} does not exist")
    results: list[tuple[Path, RubricResult]] = []
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        for rubric in check_effort(skill_md, policy):
            results.append((skill_md, rubric))
    return results
