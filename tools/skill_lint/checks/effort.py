"""effort checker — spec-131 S3 (sub-003) frontmatter contract.

Every SKILL.md must declare ``effort:`` and ``model_tier:`` in its
YAML frontmatter, drawn from the closed vocabularies:

* ``effort: cheap | mid | high`` (D-131-08)
* ``model_tier: haiku | sonnet | opus``

Posture (per R-131-09 grace window):

* ``effort:`` enforcement is blocking from day one. Missing field or
  invalid enum → MAJOR.
* ``model_tier:`` is observation-only during the grace window. Missing
  field or invalid enum → MINOR. ``enforce_tier=True`` (driven by the
  CLI ``--enforce-tier`` flag, post-grace) promotes both to MAJOR.

In addition the declaration is cross-checked against
``docs/model-dispatch-policy.md`` (SSOT). Mismatch surfaces as MAJOR
(effort) or MINOR (model_tier, grace window). The policy doc is parsed
once via ``load_policy`` and threaded through the driver to avoid
per-skill re-reads.

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

# Closed vocabularies (D-131-08).
VALID_EFFORTS: frozenset[str] = frozenset({"cheap", "mid", "high"})
VALID_MODEL_TIERS: frozenset[str] = frozenset({"haiku", "sonnet", "opus"})

# Allow-listed mirror gaps. The .github surface intentionally omits
# ``ai-analyze-permissions``; the driver must tolerate the absence
# without flagging it as a violation.
GITHUB_MIRROR_ALLOWLIST: frozenset[str] = frozenset({"ai-analyze-permissions"})


# Frontmatter delimiter regex — reuses the pair_aware shape.
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
# Field line: ``key: value`` with optional inline comment. Value captured
# verbatim; quoting (``"value"`` or ``'value'``) stripped downstream.
_FIELD_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.+?)\s*$", re.MULTILINE)
# Policy table row: pipe-delimited markdown, with leading whitespace
# tolerance.
_POLICY_ROW_RE = re.compile(
    r"^\|\s*(ai-[\w-]+)\s*\|\s*(cheap|mid|high)\s*\|\s*(haiku|sonnet|opus)\s*\|.*\|\s*$",
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


def load_policy(policy_path: Path) -> dict[str, tuple[str, str]]:
    """Parse the model-dispatch policy markdown into ``{skill: (effort, tier)}``.

    The expected shape is a markdown table whose rows match
    ``_POLICY_ROW_RE``. Header / separator rows that fall outside the
    pattern are silently skipped. Returns an empty dict when the file
    does not exist (lint surfaces the absence at call-site instead).
    """
    if not policy_path.is_file():
        return {}
    text = policy_path.read_text(encoding="utf-8")
    out: dict[str, tuple[str, str]] = {}
    for skill, effort, tier in _POLICY_ROW_RE.findall(text):
        out[skill] = (effort, tier)
    return out


# ---------------------------------------------------------------------------
# Frontmatter extraction
# ---------------------------------------------------------------------------


def _read_frontmatter(skill_md: Path) -> dict[str, str]:
    """Return the YAML frontmatter as a flat ``{key: value}`` mapping.

    Handles only the subset we care about (scalar string values for the
    ``effort`` / ``model_tier`` keys). Quoted values have their outer
    quotes stripped. Returns an empty dict when the file is missing or
    has no frontmatter — call-site decides how to surface that.
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


def _check_model_tier_declared(fm: dict[str, str], *, enforce: bool) -> RubricResult:
    """Validate the ``model_tier:`` field declaration.

    Posture:
    * Missing field → MINOR during R-131-09 grace (``enforce=False``),
      MAJOR once enforcement flips on.
    * Invalid enum value → always MAJOR (drift from the closed vocabulary
      is a hard violation regardless of grace).
    """
    missing_severity = "MAJOR" if enforce else "MINOR"
    value = fm.get("model_tier")
    if value is None:
        return RubricResult(
            "model_tier_declared",
            missing_severity,
            "frontmatter missing field `model_tier:` (haiku | sonnet | opus)",
        )
    if value not in VALID_MODEL_TIERS:
        return RubricResult(
            "model_tier_declared",
            "MAJOR",
            f"model_tier {value!r} not in {sorted(VALID_MODEL_TIERS)}",
        )
    return RubricResult(
        "model_tier_declared",
        "OK",
        f"model_tier: {value}",
    )


def _check_effort_policy_match(
    fm: dict[str, str],
    policy_row: tuple[str, str] | None,
) -> RubricResult:
    if policy_row is None:
        return RubricResult(
            "effort_policy_match",
            "MINOR",
            "skill not listed in docs/model-dispatch-policy.md (advisory)",
        )
    expected_effort, _ = policy_row
    declared = fm.get("effort")
    if declared is None:
        return RubricResult(
            "effort_policy_match",
            "MAJOR",
            f"cannot match policy ({expected_effort}) — effort missing",
        )
    if declared != expected_effort:
        return RubricResult(
            "effort_policy_match",
            "MAJOR",
            f"declared effort {declared!r} != policy {expected_effort!r}",
        )
    return RubricResult(
        "effort_policy_match",
        "OK",
        f"declared effort matches policy ({expected_effort})",
    )


def _check_model_tier_policy_match(
    fm: dict[str, str],
    policy_row: tuple[str, str] | None,
    *,
    enforce: bool,
) -> RubricResult:
    severity_for_violation = "MAJOR" if enforce else "MINOR"
    if policy_row is None:
        return RubricResult(
            "model_tier_policy_match",
            "MINOR",
            "skill not listed in docs/model-dispatch-policy.md (advisory)",
        )
    _, expected_tier = policy_row
    declared = fm.get("model_tier")
    if declared is None:
        return RubricResult(
            "model_tier_policy_match",
            severity_for_violation,
            f"cannot match policy ({expected_tier}) — model_tier missing",
        )
    if declared != expected_tier:
        return RubricResult(
            "model_tier_policy_match",
            severity_for_violation,
            f"declared model_tier {declared!r} != policy {expected_tier!r}",
        )
    return RubricResult(
        "model_tier_policy_match",
        "OK",
        f"declared model_tier matches policy ({expected_tier})",
    )


# ---------------------------------------------------------------------------
# Per-skill driver
# ---------------------------------------------------------------------------


def check_effort(
    skill_md: Path,
    policy: dict[str, tuple[str, str]],
    *,
    enforce_tier: bool = False,
) -> list[RubricResult]:
    """Run the four sub-checks against a single SKILL.md path.

    Returns a list of ``RubricResult`` records — one per sub-check
    (``effort_declared``, ``model_tier_declared``, ``effort_policy_match``,
    ``model_tier_policy_match``). ``CRITICAL`` is returned only when the
    file itself is unreadable.
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
    policy_row = policy.get(skill_slug)
    return [
        _check_effort_declared(fm),
        _check_model_tier_declared(fm, enforce=enforce_tier),
        _check_effort_policy_match(fm, policy_row),
        _check_model_tier_policy_match(fm, policy_row, enforce=enforce_tier),
    ]


# ---------------------------------------------------------------------------
# Skills-root driver
# ---------------------------------------------------------------------------


def check_all_skills(
    skills_root: Path,
    policy: dict[str, tuple[str, str]],
    *,
    enforce_tier: bool = False,
) -> list[tuple[Path, RubricResult]]:
    """Walk every ``<skills_root>/ai-*/SKILL.md`` and run the contract.

    Returns ``[(skill_md_path, result), ...]`` sorted by path so CI
    output stays stable. The known ``ai-analyze-permissions`` gap on
    ``.github/skills/`` is allow-listed: if the skill is absent under
    the walked root, no result rows are emitted for it (other mirrors
    are responsible for surfacing the absence if applicable).
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
        for rubric in check_effort(skill_md, policy, enforce_tier=enforce_tier):
            results.append((skill_md, rubric))
    return results
