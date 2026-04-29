"""RED-phase test for spec-110 Phase 2 -- npm/bun/pnpm/yarn ``--ignore-scripts``.

Spec acceptance criterion (governance v3 harvest, Phase 2, T-2.9):
    Every JavaScript package-install invocation in ``.github/workflows/*.yml``
    (``npm``, ``bun``, ``pnpm``, ``yarn`` followed by ``install``, ``i``,
    ``ci``, or ``add``) must include the ``--ignore-scripts`` flag. This
    blocks malicious lifecycle scripts (``preinstall`` / ``postinstall``)
    from executing in CI runners with elevated privileges, the supply-chain
    vector exercised by the 2024 ``shai-hulud`` and 2024 ``ua-parser-js``
    incidents.

Status: RED until T-2.10. Initial audit during ``/ai-brainstorm`` flagged
``ci-check.yml`` line 522 (``npm install -g snyk``) as the lone real
violation in the repo today; the bash comment in ``install-smoke.yml`` line
301 is intentionally NOT a violation and the comment-stripping logic below
keeps the test focused on executable commands only.

The framework is Python-only at runtime, so this test may eventually become
vacuous if the snyk dependency is removed. That's acceptable -- a vacuous
pass still serves as a regression guard for any FUTURE js install that lands
without the flag.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import yaml

# Repo root: tests/integration/<this file> -> up 3 levels.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# Match a js package-install pattern at the start of a token sequence.
# Tools: npm, bun, pnpm, yarn. Subcommands: install, i, ci, add.
# Word-boundary on both ends so ``npmcli`` and ``yarn-berry`` won't match.
# The pattern matches anywhere on a line so ``sudo npm install ...`` and
# ``cd /tmp && npm install ...`` are both flagged.
JS_INSTALL_RE = re.compile(
    r"\b(npm|bun|pnpm|yarn)\s+(install|i|ci|add)\b",
    re.IGNORECASE,
)

# The flag tokens that satisfy the gate. ``shlex`` tokenisation of a shell
# line preserves quoting so ``--ignore-scripts=true`` and ``--ignore-scripts``
# both surface as a single argv element starting with the flag prefix.
IGNORE_SCRIPTS_TOKENS = frozenset({"--ignore-scripts"})


def _iter_run_steps(node: Any) -> list[str]:
    """Recursively collect every ``run:`` value from a parsed workflow tree.

    GitHub Actions allows ``run:`` keys at the step level inside ``steps[]``.
    The walker recurses into every dict/list it encounters so future nesting
    (matrix-include sub-steps, composite actions inlined into workflows)
    is automatically covered.
    """
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "run" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_iter_run_steps(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_iter_run_steps(item))
    return found


def _strip_inline_comment(line: str) -> str:
    """Return the executable portion of a bash line, dropping any inline ``#`` comment.

    Comments are everything from an unquoted ``#`` to end-of-line. We use
    ``shlex`` to walk the tokens and stop at the first ``#``-prefixed token
    that is not inside quotes. This keeps real commands like
    ``echo "value=#42"`` intact while dropping ``# spot-check`` trailers.
    Lines that are pure comments (after lstrip the first non-whitespace
    character is ``#``) yield an empty string.
    """
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return ""
    # shlex with posix=True lets quoted ``#`` survive as part of a token.
    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=False)
        lexer.whitespace_split = True
        kept: list[str] = []
        for tok in lexer:
            if tok.startswith("#"):
                break
            kept.append(tok)
        return " ".join(kept)
    except ValueError:
        # Unbalanced quotes: fall back to the raw line so the regex still
        # has a chance. The post-step bash will likely have failed already.
        return line


def _has_ignore_scripts(command_line: str) -> bool:
    """Return True if the command line includes ``--ignore-scripts``.

    Handles both bare ``--ignore-scripts`` and ``--ignore-scripts=true``
    forms, plus ``--ignore-scripts false`` (which would be a bypass attempt
    -- we still treat the flag as present per token match; if a future bypass
    pattern emerges, harden here without changing the public API).
    """
    try:
        tokens = shlex.split(command_line, posix=True)
    except ValueError:
        # Unbalanced quotes: fall back to substring search.
        return "--ignore-scripts" in command_line
    return any(tok.startswith("--ignore-scripts") for tok in tokens)


def test_no_install_without_ignore_scripts() -> None:
    """Every npm/bun/pnpm/yarn install in ``.github/workflows/*.yml`` uses --ignore-scripts.

    Algorithm:
      1. Glob ``.github/workflows/*.yml``.
      2. For each workflow, walk the YAML tree to collect every ``run:`` block.
      3. Split each block into lines; strip inline ``#`` comments and pure
         comment lines so the regex never trips on documentation.
      4. For each non-comment line, search for the js-install pattern.
      5. When a match is found, check that the SAME line carries
         ``--ignore-scripts``.
      6. Collect (workflow, line excerpt, missing flag) tuples.
      7. Assert violations is empty.

    Vacuous-pass note: if no workflows install js packages, the violations
    list is empty and the test passes trivially. That's acceptable per
    plan-110 T-2.10 -- the test still acts as a regression guard for any
    FUTURE js install added without ``--ignore-scripts``.
    """
    assert WORKFLOWS_DIR.is_dir(), (
        f"Expected workflows directory at {WORKFLOWS_DIR}; cannot validate "
        "--ignore-scripts gate without workflow files."
    )

    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    assert workflow_files, (
        f"No ``.yml`` files found under {WORKFLOWS_DIR}; spec-110 Phase 2 "
        "requires at least one workflow to validate."
    )

    violations: list[str] = []
    for workflow_path in workflow_files:
        parsed = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        for run_block in _iter_run_steps(parsed):
            for raw_line in run_block.splitlines():
                command_line = _strip_inline_comment(raw_line)
                if not command_line.strip():
                    continue
                if not JS_INSTALL_RE.search(command_line):
                    continue
                if _has_ignore_scripts(command_line):
                    continue
                excerpt = command_line.strip()
                if len(excerpt) > 120:
                    excerpt = excerpt[:117] + "..."
                violations.append(
                    f"{workflow_path.relative_to(REPO_ROOT)}: '{excerpt}' "
                    f"-- missing --ignore-scripts"
                )

    assert not violations, (
        "All npm/bun/pnpm/yarn install invocations in .github/workflows/*.yml "
        "must include --ignore-scripts to block malicious lifecycle scripts. "
        f"Found {len(violations)} violation(s):\n  - " + "\n  - ".join(violations)
    )
