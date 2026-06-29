#!/usr/bin/env python3
"""PreToolUse hook: advisory nudge routing raw git/gh to /ai-commit and /ai-pr (spec-182).

NON-BLOCKING. When the agent issues a raw ``git commit``, ``git push``, or
``gh pr create``, this hook ALLOWS the call and injects an advisory into the
model context steering it toward the governed pipelines (/ai-commit, /ai-pr).
Running these raw skips the governed pipeline -- the secret scan, docs gate,
spec consolidation, and audit chain. The advisory is a reminder at the
decision moment; it never denies (contrast: no-verify-guard.py, which exits 2).

Two reasons raw git/gh happens (spec-182 Summary):
1. genuine drift -- the agent forgets /ai-commit / /ai-pr for a standalone
   request. This is the case the nudge solves.
2. correct in-skill calls -- /ai-commit, /ai-pr and friends run these verbs
   internally, by design. The self-aware phrasing ("if you are not already
   inside ...") lets the agent recognise it is already governed and proceed.

Output shape (confirmed against the Claude Code hook protocol, D-182-01):
``{"hookSpecificOutput": {"hookEventName": "PreToolUse",
"permissionDecision": "allow", "additionalContext": <nudge>}}`` on stdout,
exit 0. NOT the flat ``{"decision": "allow", ...}`` form.

Disable with ``AIENG_GOVERNED_GIT_ADVISOR_DISABLED=1``.

Stdlib-only sealed contract (no ``ai_engineering.*`` imports) -- same as the
rest of ``.ai-engineering/scripts/hooks/``.
"""

from __future__ import annotations

import contextlib
import json
import os
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import get_session_id, passthrough_stdin
from _lib.hook_common import run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.observability import emit_framework_operation

# Verbs with a governed equivalent (D-182-02). Read-only / structural git
# (log, diff, status, rebase, stash, add) has no governed alternative and is
# never nudged.
_GIT_VERBS: frozenset[str] = frozenset({"commit", "push"})
_SHELL_SEPARATORS: frozenset[str] = frozenset({"&&", "||", ";", "|"})
# git global flags that consume the NEXT token as a value (so the verb finder
# must skip the pair). ``--git-dir=x`` / ``--work-tree=x`` use the ``=`` form
# and are skipped as ordinary ``-``-prefixed tokens below.
_GIT_VALUE_FLAGS: frozenset[str] = frozenset({"-C", "--namespace"})
# gh global flags that consume the NEXT token as a value before the subcommand,
# e.g. ``gh -R owner/repo pr create``. The ``--repo=owner/repo`` ``=`` form is
# skipped as an ordinary ``-``-prefixed token by the positional scan below.
_GH_VALUE_FLAGS: frozenset[str] = frozenset({"-R", "--repo"})
_GOVERNANCE_LOST = "secret scan, docs gate, spec consolidation, and the audit chain"
_MARKER_REL = (".ai-engineering", "runtime", "governed-git-seen")


def _strip_env_prefix(tokens: list[str]) -> list[str]:
    """Drop leading ``KEY=VALUE`` env-var prefix tokens (mirror no-verify-guard)."""
    out = list(tokens)
    while out and "=" in out[0] and not out[0].startswith("="):
        key = out[0].split("=", 1)[0]
        if not key or not (key[0].isalpha() or key[0] == "_"):
            break
        if not all(c.isalnum() or c == "_" for c in key):
            break
        out.pop(0)
    return out


def _subcommands(argv: str) -> list[list[str]]:
    """Split a compound Bash string into sub-command token lists (D-182-07).

    ``shlex.split`` does not treat ``&&`` / ``;`` / ``|`` as statement
    boundaries, so ``git add . && git commit`` would hide the commit behind
    the leading ``add`` verb. Tokenise once (fail-soft to ``[]`` on malformed
    quoting -- this is an advisory, so a parse failure means "no nudge", never
    a block), then re-split on shell-operator tokens.
    """
    if not argv:
        return []
    try:
        tokens = shlex.split(argv)
    except ValueError:
        return []
    subs: list[list[str]] = [[]]
    for tok in tokens:
        if tok in _SHELL_SEPARATORS:
            subs.append([])
        else:
            subs[-1].append(tok)
    return [sub for sub in subs if sub]


def _git_verb(args: list[str]) -> str | None:
    """First non-flag token after ``git``, skipping ``-C <path>`` style prefixes."""
    i = 0
    while i < len(args):
        tok = args[i]
        if tok in _GIT_VALUE_FLAGS:
            i += 2  # flag consumes its value
            continue
        if tok.startswith("-"):
            i += 1  # other global flag (incl. ``--git-dir=x``) -- skip
            continue
        return tok
    return None


def _is_gh_pr_create(args: list[str]) -> bool:
    """True when ``args`` (tokens after ``gh``) is a ``pr create`` invocation.

    Skips ``gh``-global value flags (``-R owner/repo`` / ``--repo owner/repo``)
    that precede the subcommand, mirroring ``_git_verb``'s handling of
    ``-C <path>`` so ``gh -R owner/repo pr create`` is not missed.
    """
    positional: list[str] = []
    i = 0
    while i < len(args) and len(positional) < 2:
        tok = args[i]
        if tok in _GH_VALUE_FLAGS:
            i += 2  # flag consumes its value
            continue
        if tok.startswith("-"):
            i += 1  # other global flag (incl. ``--repo=owner/repo``) -- skip
            continue
        positional.append(tok)
        i += 1
    return positional == ["pr", "create"]


def detect_verb(argv: str) -> str | None:
    """Return the governed verb label (``git commit`` / ``git push`` /
    ``gh pr create``) for any sub-command, else ``None``."""
    # Hot-path pre-screen (R4): the vast majority of Bash calls are neither
    # git nor gh -- skip shlex entirely (and bound its O(n^2) cost on
    # pathological single-token input) when neither tool name appears.
    if "git" not in argv and "gh" not in argv:
        return None
    for sub in _subcommands(argv):
        sub = _strip_env_prefix(sub)
        if not sub:
            continue
        head = sub[0]
        if head == "git":
            verb = _git_verb(sub[1:])
            if verb in _GIT_VERBS:
                return f"git {verb}"
        elif head == "gh" and _is_gh_pr_create(sub[1:]):
            return "gh pr create"
    return None


def _nudge(verb: str) -> str:
    route = "/ai-pr" if verb == "gh pr create" else "/ai-commit"
    return (
        f"[governed-git] Raw `{verb}` detected. If you are not already inside "
        f"/ai-commit or /ai-pr, prefer {route}: running git/gh raw skips the "
        f"governed pipeline ({_GOVERNANCE_LOST}). "
        f"For `git commit --amend`, prefer a fresh conventional commit via /ai-commit."
    )


def _session_seq(project_root: Path) -> str:
    """``first`` for the first advisory in this session, ``repeat`` after, or
    ``unknown`` if the marker is unwritable (fail-open). Partial signal for the
    v2 hard-block decision (D-182-05)."""
    sid = get_session_id()
    try:
        marker = project_root.joinpath(*_MARKER_REL)
        marker.parent.mkdir(parents=True, exist_ok=True)
        seen = set(marker.read_text(encoding="utf-8").split()) if marker.exists() else set()
        if sid in seen:
            return "repeat"
        seen.add(sid)
        marker.write_text(" ".join(sorted(seen)), encoding="utf-8")
        return "first"
    except OSError:
        return "unknown"


def main() -> None:
    ctx = get_hook_context()
    if os.environ.get("AIENG_GOVERNED_GIT_ADVISOR_DISABLED") == "1":
        passthrough_stdin(ctx.data)
        return
    if ctx.data.get("tool_name") != "Bash":
        passthrough_stdin(ctx.data)
        return
    tool_input = ctx.data.get("tool_input") or {}
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}
    command = ""
    if isinstance(tool_input, dict):
        command = tool_input.get("command") or ""
    if not isinstance(command, str):
        command = ""

    verb = detect_verb(command)
    if not verb:
        passthrough_stdin(ctx.data)
        return

    # Ledger (D-182-05) -- fail-open: a telemetry failure must never break the
    # advisory or the tool call.
    with contextlib.suppress(Exception):
        emit_framework_operation(
            ctx.project_root,
            operation="governed_git_advisory",
            component="hook.governed-git-advisor",
            metadata={"verb": verb, "session_seq": _session_seq(ctx.project_root)},
        )

    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": _nudge(verb),
                }
            },
            separators=(",", ":"),
        )
    )
    sys.stdout.flush()


if __name__ == "__main__":
    run_hook_safe(
        main,
        component="hook.governed-git-advisor",
        hook_kind="pre-tool-use",
        script_path=Path(__file__),
    )
