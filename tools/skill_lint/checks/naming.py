"""Naming lint — brief §2.5 R1-R5 conformance check.

Pure-stdlib (``re`` + ``pathlib``) checker mirroring the shape of
``no_nested_refs.py`` and ``pair_aware.py``. Walks four canonical roots:

* ``.claude/skills/`` — skill directory naming (R1, R4)
* ``.claude/agents/`` — agent .md naming (R1, R4)
* ``.ai-engineering/scripts/hooks/`` — hook script naming (R2, R3, R4, R5)
* ``.ai-engineering/scripts/scheduled/`` — scheduled script naming
  (R4, R5)

Five rules:

* **R1 — `ai-` prefix** on every skill / agent. The specialist roster
  (``reviewer-``, ``verifier-``, ``verify-``) is exempt — those are
  internal sub-agents never surfaced to the operator.
* **R2 — verb-noun + banned-metaphor list** on every hook script. The
  ``_R2_DEFERRED_LEGACY`` allow-list captures the seven D-131-10
  filenames that emit advisory ``MINOR`` so CI does not break on the
  legacy surface. New violations are flagged ``MAJOR``.
* **R3 — paired lifecycle verbs**: if ``<prefix>-<noun>-start.sh``
  exists, the matching ``-end.sh`` (or ``-stop.sh`` for runtime /
  daemon / process nouns) must exist. Missing partner → MAJOR.
* **R4 — kebab-case** in user-facing surfaces. ``_`` and camelCase →
  MAJOR.
* **R5 — `.sh` ↔ `.ps1` sibling parity** in
  ``.ai-engineering/scripts/{hooks,scheduled}/``. The three
  ``_R5_DEFERRED_SKILL_SCRIPTS`` skill-script ``.sh`` filenames emit
  ``INFO``. Otherwise missing sibling → ``MAJOR``.

Severity mapping:

* ``OK`` — rule satisfied.
* ``INFO`` — D-131-10 deferred allow-list match (does not break CI).
* ``MINOR`` — legacy metaphor allow-list match (does not break CI).
* ``MAJOR`` — genuine new violation (not driving exit code in sub-006;
  will be promoted once spec-132 closes the legacy renames).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}


# R1 — skip internal specialist roster (per Exploration §R1).
_R1_INTERNAL_PREFIXES = ("reviewer-", "verifier-", "verify-")

# R2 — banned metaphor tokens.
_R2_BANNED_METAPHORS = frozenset({"instinct", "strategic", "tactical"})

# R2 — D-131-10 deferred legacy filenames. Match emits MINOR (not MAJOR)
# so existing CI does not break on the seven names; spec-132 closes
# them.
_R2_DEFERRED_LEGACY = frozenset(
    {
        "copilot-instinct-extract",
        "copilot-instinct-observe",
        "copilot-strategic-compact",
        "copilot-mcp-health",
        "copilot-skill",
        "copilot-error",
        "copilot-agent",
    }
)

# R2 — recognised action verbs (used when the filename does NOT start
# with an adapter prefix).
_R2_ACTION_VERBS = frozenset(
    {
        "collect",
        "verify",
        "emit",
        "extract",
        "observe",
        "guard",
        "enforce",
        "rotate",
        "consolidate",
        "deny",
        "format",
        "compact",
        "dispatch",
        "handle",
        "check",
        "start",
        "stop",
        "end",
        "open",
        "close",
        "render",
        "sync",
        "scaffold",
        "cleanup",
        "sweep",
        "simplify",
        # Descriptive technical terms accepted as verb-equivalents per
        # Exploration §R2 (recognised technical names — kept as-is):
        "disclosure",
        "notification",
        "subagent",
    }
)

# R3 — paired lifecycle verbs.
_R3_PAIRS = {"start": "end", "open": "close", "enable": "disable"}
# Long-running processes legitimately use start/stop (not start/end).
_R3_PROCESS_NOUNS = frozenset({"runtime", "daemon", "process"})

# R4 — kebab-case (lowercase letters, digits, and dashes only).
_R4_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# R5 — D-131-10 deferred .sh files (no .ps1 yet).
_R5_DEFERRED_SKILL_SCRIPTS = frozenset(
    {
        "board-sync-github",
        "cleanup-settings-local",
        "scaffold-skill",
    }
)


@dataclass(frozen=True)
class RubricResult:
    """Outcome of a single naming check."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _is_metaphor(stem: str) -> str | None:
    """Return the offending metaphor token if `stem` carries one, else None."""
    tokens = stem.split("-")
    for token in tokens:
        if token in _R2_BANNED_METAPHORS:
            return token
    return None


def _has_verb(stem: str) -> bool:
    """Return True iff `stem` contains at least one recognised action verb."""
    tokens = stem.split("-")
    return any(token in _R2_ACTION_VERBS for token in tokens)


def _is_kebab_case(name: str) -> bool:
    """Return True iff `name` matches kebab-case (no `_`, no camelCase)."""
    return bool(_R4_KEBAB_RE.match(name))


def _paired_lifecycle_partner(stem: str) -> tuple[str, str] | None:
    """If `stem` ends in a lifecycle verb, return ``(verb, partner)``.

    Otherwise return ``None``. The partner is the expected stem of the
    matching sibling (e.g. ``foo-start`` → ``("start", "foo-end")``).
    Runtime / daemon / process nouns map ``start`` → ``stop`` because
    those are long-running processes (not transactional sessions).
    """
    tokens = stem.split("-")
    if len(tokens) < 2:
        return None
    last = tokens[-1]
    if last not in _R3_PAIRS and last not in {"end", "close", "disable", "stop"}:
        return None

    # Only look at the FORWARD half (start/open/enable) — orphan REVERSE
    # halves are caught when the partner is missing in the forward
    # direction.
    if last not in _R3_PAIRS:
        return None

    noun = tokens[-2] if len(tokens) >= 2 else ""
    if last == "start" and noun in _R3_PROCESS_NOUNS:
        expected_partner_verb = "stop"
    else:
        expected_partner_verb = _R3_PAIRS[last]
    partner_stem = "-".join([*tokens[:-1], expected_partner_verb])
    return last, partner_stem


# ---------------------------------------------------------------------------
# R1 — ai- prefix.
# ---------------------------------------------------------------------------


def _check_r1(skills_root: Path, agents_root: Path) -> list[tuple[Path, RubricResult]]:
    results: list[tuple[Path, RubricResult]] = []

    if skills_root.is_dir():
        for entry in sorted(skills_root.iterdir()):
            if not entry.is_dir():
                continue
            # _shared is scaffolding, not a skill.
            if entry.name == "_shared":
                continue
            # Only directories that ship a SKILL.md are user-facing skills.
            if not (entry / "SKILL.md").is_file():
                continue
            if entry.name.startswith("ai-"):
                results.append(
                    (
                        entry,
                        RubricResult(
                            "naming_r1_prefix",
                            "OK",
                            f"skill {entry.name!r} carries ai- prefix",
                        ),
                    )
                )
            else:
                results.append(
                    (
                        entry,
                        RubricResult(
                            "naming_r1_prefix",
                            "MAJOR",
                            f"skill {entry.name!r} missing ai- prefix",
                        ),
                    )
                )

    if agents_root.is_dir():
        for agent_file in sorted(agents_root.iterdir()):
            if not agent_file.is_file() or agent_file.suffix != ".md":
                continue
            stem = agent_file.stem
            if stem.startswith(_R1_INTERNAL_PREFIXES):
                # Specialist roster — exempt by §R1.
                results.append(
                    (
                        agent_file,
                        RubricResult(
                            "naming_r1_prefix",
                            "OK",
                            f"agent {stem!r} is internal specialist (exempt)",
                        ),
                    )
                )
                continue
            if stem.startswith("ai-"):
                results.append(
                    (
                        agent_file,
                        RubricResult(
                            "naming_r1_prefix",
                            "OK",
                            f"agent {stem!r} carries ai- prefix",
                        ),
                    )
                )
            else:
                results.append(
                    (
                        agent_file,
                        RubricResult(
                            "naming_r1_prefix",
                            "MAJOR",
                            f"agent {stem!r} missing ai- prefix",
                        ),
                    )
                )

    return results


# ---------------------------------------------------------------------------
# R2 — verb-noun + banned metaphor list.
# ---------------------------------------------------------------------------


def _check_r2(hooks_root: Path) -> list[tuple[Path, RubricResult]]:
    """Lint hook script names for verb-noun + banned-metaphor rules.

    Only `.sh` files at the top level of `hooks/` are inspected. The
    `.ps1` sibling inherits R2 outcomes by R5 parity (separate rule).
    `_lib/` helpers are excluded — they are not user-facing surfaces.
    """
    results: list[tuple[Path, RubricResult]] = []
    if not hooks_root.is_dir():
        return results

    for script in sorted(hooks_root.glob("*.sh")):
        stem = script.stem

        # Deferred allow-list match — advisory MINOR.
        if stem in _R2_DEFERRED_LEGACY:
            metaphor = _is_metaphor(stem)
            if metaphor is not None:
                reason = (
                    f"banned metaphor {metaphor!r} (D-131-10 deferred legacy — rename to "
                    f"non-metaphor verb-noun in spec-132)"
                )
            else:
                reason = (
                    f"{stem!r} lacks an action verb (D-131-10 deferred legacy — "
                    f"rename to verb-noun in spec-132)"
                )
            results.append((script, RubricResult("naming_r2_verb_noun", "MINOR", reason)))
            continue

        # Banned metaphor on a non-deferred filename — MAJOR.
        metaphor = _is_metaphor(stem)
        if metaphor is not None:
            results.append(
                (
                    script,
                    RubricResult(
                        "naming_r2_verb_noun",
                        "MAJOR",
                        f"banned metaphor {metaphor!r} in {stem!r}",
                    ),
                )
            )
            continue

        # Verb presence check — non-deferred filenames must carry a verb.
        if not _has_verb(stem):
            results.append(
                (
                    script,
                    RubricResult(
                        "naming_r2_verb_noun",
                        "MAJOR",
                        f"{stem!r} lacks an action verb",
                    ),
                )
            )
            continue

        results.append(
            (
                script,
                RubricResult(
                    "naming_r2_verb_noun",
                    "OK",
                    f"{stem!r} is a clean verb-noun",
                ),
            )
        )

    return results


# ---------------------------------------------------------------------------
# R3 — paired lifecycle verbs.
# ---------------------------------------------------------------------------


def _check_r3(hooks_root: Path) -> list[tuple[Path, RubricResult]]:
    results: list[tuple[Path, RubricResult]] = []
    if not hooks_root.is_dir():
        return results

    sh_stems = {p.stem for p in hooks_root.glob("*.sh")}
    for script in sorted(hooks_root.glob("*.sh")):
        stem = script.stem
        partner_info = _paired_lifecycle_partner(stem)
        if partner_info is None:
            # No forward lifecycle verb → not in scope of R3.
            continue
        verb, partner_stem = partner_info
        if partner_stem in sh_stems:
            results.append(
                (
                    script,
                    RubricResult(
                        "naming_r3_lifecycle_pair",
                        "OK",
                        f"{stem!r} pairs with {partner_stem!r}",
                    ),
                )
            )
        else:
            results.append(
                (
                    script,
                    RubricResult(
                        "naming_r3_lifecycle_pair",
                        "MAJOR",
                        f"{stem!r} has forward verb {verb!r} but no partner {partner_stem!r}.sh",
                    ),
                )
            )

    return results


# ---------------------------------------------------------------------------
# R4 — kebab-case.
# ---------------------------------------------------------------------------


def _check_r4(
    skills_root: Path,
    agents_root: Path,
    hooks_root: Path,
    scheduled_root: Path,
) -> list[tuple[Path, RubricResult]]:
    results: list[tuple[Path, RubricResult]] = []

    def _emit(path: Path, name: str) -> None:
        if _is_kebab_case(name):
            results.append(
                (
                    path,
                    RubricResult(
                        "naming_r4_kebab_case",
                        "OK",
                        f"{name!r} is kebab-case",
                    ),
                )
            )
        else:
            results.append(
                (
                    path,
                    RubricResult(
                        "naming_r4_kebab_case",
                        "MAJOR",
                        f"{name!r} is not kebab-case (use lowercase + dashes)",
                    ),
                )
            )

    if skills_root.is_dir():
        for entry in sorted(skills_root.iterdir()):
            if not entry.is_dir() or entry.name == "_shared":
                continue
            if not (entry / "SKILL.md").is_file():
                continue
            _emit(entry, entry.name)

    if agents_root.is_dir():
        for agent_file in sorted(agents_root.iterdir()):
            if not agent_file.is_file() or agent_file.suffix != ".md":
                continue
            _emit(agent_file, agent_file.stem)

    if hooks_root.is_dir():
        for script in sorted(hooks_root.glob("*.sh")):
            _emit(script, script.stem)
        for script in sorted(hooks_root.glob("*.ps1")):
            _emit(script, script.stem)

    if scheduled_root.is_dir():
        for script in sorted(scheduled_root.glob("*.sh")):
            _emit(script, script.stem)
        for script in sorted(scheduled_root.glob("*.ps1")):
            _emit(script, script.stem)

    return results


# ---------------------------------------------------------------------------
# R5 — .sh ↔ .ps1 sibling parity.
# ---------------------------------------------------------------------------


def _check_r5(
    hooks_root: Path,
    scheduled_root: Path,
    skills_root: Path,
) -> list[tuple[Path, RubricResult]]:
    """Sibling parity across hooks/, scheduled/, and skill scripts/.

    Skill script `.sh` files under `.claude/skills/<slug>/scripts/`
    that lack `.ps1` siblings are matched against
    `_R5_DEFERRED_SKILL_SCRIPTS` and emit advisory `INFO`. Outside the
    allow-list, missing siblings → MAJOR.
    """
    results: list[tuple[Path, RubricResult]] = []

    def _emit_parity(root: Path) -> None:
        if not root.is_dir():
            return
        sh_files = sorted(root.glob("*.sh"))
        ps1_stems = {p.stem for p in root.glob("*.ps1")}
        sh_stems = {p.stem for p in sh_files}

        for sh_file in sh_files:
            stem = sh_file.stem
            if stem in ps1_stems:
                results.append(
                    (
                        sh_file,
                        RubricResult(
                            "naming_r5_sh_ps1_parity",
                            "OK",
                            f"{stem!r} has .sh + .ps1 pair",
                        ),
                    )
                )
            elif stem in _R5_DEFERRED_SKILL_SCRIPTS:
                results.append(
                    (
                        sh_file,
                        RubricResult(
                            "naming_r5_sh_ps1_parity",
                            "INFO",
                            f"{stem}.sh has no .ps1 sibling (D-131-10 deferred skill script)",
                        ),
                    )
                )
            else:
                results.append(
                    (
                        sh_file,
                        RubricResult(
                            "naming_r5_sh_ps1_parity",
                            "MAJOR",
                            f"{stem}.sh missing .ps1 sibling",
                        ),
                    )
                )

        # Reverse direction: .ps1 with no .sh.
        for ps1_file in sorted(root.glob("*.ps1")):
            stem = ps1_file.stem
            if stem in sh_stems:
                continue  # already counted on the forward leg
            results.append(
                (
                    ps1_file,
                    RubricResult(
                        "naming_r5_sh_ps1_parity",
                        "MAJOR",
                        f"{stem}.ps1 missing .sh sibling",
                    ),
                )
            )

    _emit_parity(hooks_root)
    _emit_parity(scheduled_root)
    # `_lib/` helpers under hooks/ — assert the copilot-common pair.
    _emit_parity(hooks_root / "_lib")

    # Skill scripts: only emit for the deferred allow-list so the lint
    # surfaces the gap without scanning every skill scripts/ dir for
    # other rules.
    if skills_root.is_dir():
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            scripts_dir = skill_dir / "scripts"
            if not scripts_dir.is_dir():
                continue
            ps1_stems = {p.stem for p in scripts_dir.glob("*.ps1")}
            for sh_file in sorted(scripts_dir.glob("*.sh")):
                stem = sh_file.stem
                if stem in ps1_stems:
                    continue  # paired — pass silently to keep results focused
                if stem in _R5_DEFERRED_SKILL_SCRIPTS:
                    results.append(
                        (
                            sh_file,
                            RubricResult(
                                "naming_r5_sh_ps1_parity",
                                "INFO",
                                (f"{stem}.sh has no .ps1 sibling (D-131-10 deferred skill script)"),
                            ),
                        )
                    )
                else:
                    results.append(
                        (
                            sh_file,
                            RubricResult(
                                "naming_r5_sh_ps1_parity",
                                "MAJOR",
                                f"{stem}.sh missing .ps1 sibling in skill scripts/",
                            ),
                        )
                    )

    return results


# ---------------------------------------------------------------------------
# Driver.
# ---------------------------------------------------------------------------


def check_naming(
    skills_root: Path,
    agents_root: Path,
    hooks_root: Path,
    scheduled_root: Path,
) -> list[tuple[Path, RubricResult]]:
    """Run R1-R5 over the four canonical roots.

    Returns a list of ``(path, RubricResult)`` tuples for the CLI to roll
    up. The CLI summary line surfaces counts by severity. Naming MAJORs
    do not drive the exit code in sub-006 — they will be promoted once
    spec-132 closes the deferred legacy renames.
    """
    results: list[tuple[Path, RubricResult]] = []
    results.extend(_check_r1(skills_root, agents_root))
    results.extend(_check_r2(hooks_root))
    results.extend(_check_r3(hooks_root))
    results.extend(_check_r4(skills_root, agents_root, hooks_root, scheduled_root))
    results.extend(_check_r5(hooks_root, scheduled_root, skills_root))
    return results
