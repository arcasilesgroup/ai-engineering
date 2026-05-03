#!/usr/bin/env python3
"""UserPromptSubmit hook: top-K skill suggestion (spec-116 G-5).

Loading every skill description into context "degrades performance
before the agent takes a single action" (Osmani, harness essay). This
hook implements progressive disclosure: rank the 49 skills against the
incoming user prompt and surface the top-K most relevant via
``hookSpecificOutput.additionalContext``. The model still has the full
``/ai-*`` surface available — this only highlights candidates it should
consider.

Heuristic ranking (deliberately stdlib-only, no embeddings):

* tokenise prompt + skill description into lowercase word set
* score = |prompt ∩ description| + 2·(name match)
* tie-break by description length (shorter = more focused)

Disabled when the prompt is already a slash command (``/ai-*``) — the
user picked a skill explicitly, no need to second-guess. Also skipped
for trivial prompts (<3 informative words).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import emit_event, get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.runtime_state import iso_now

_TOP_K = 5
_MIN_PROMPT_TOKENS = 3
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "to",
        "of",
        "for",
        "in",
        "on",
        "is",
        "are",
        "be",
        "this",
        "that",
        "with",
        "as",
        "it",
        "i",
        "we",
        "you",
        "they",
        "do",
        "does",
        "have",
        "has",
        "can",
        "should",
        "would",
        "could",
        "will",
        "shall",
        "if",
        "then",
        "so",
        "by",
        "from",
        "into",
        "out",
        "up",
        "down",
        "como",
        "que",
        "el",
        "la",
        "los",
        "las",
        "y",
        "o",
        "de",
        "para",
        "en",
        "un",
        "una",
        "es",
        "está",
        "esta",
        "esto",
        "estos",
        "se",
        "lo",
        "le",
        "me",
        "te",
        "no",
        "si",
    }
)
_TOKEN_RE = re.compile(r"[a-zA-Z0-9_-]{2,}")


def _tokenise(text: str) -> set[str]:
    tokens = {t.lower() for t in _TOKEN_RE.findall(text)}
    return tokens - _STOPWORDS


def _read_skill_descriptions(project_root: Path) -> list[tuple[str, str]]:
    """Return ``[(skill_name, description)]`` for every SKILL.md found."""
    out: list[tuple[str, str]] = []
    skills_dir = project_root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return out
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Description lives on the first non-empty `description:` line of the YAML preamble.
        match = re.search(r'^description:\s*"?([^"\n]+)"?', text, flags=re.MULTILINE)
        description = match.group(1).strip() if match else ""
        out.append((entry.name, description))
    return out


def _rank_skills(
    prompt_tokens: set[str], skills: list[tuple[str, str]]
) -> list[tuple[int, str, str]]:
    """Return ``[(score, name, description)]`` sorted desc."""
    scored: list[tuple[int, str, str]] = []
    for name, description in skills:
        if not description:
            continue
        desc_tokens = _tokenise(description)
        overlap = len(prompt_tokens & desc_tokens)
        if overlap == 0 and not any(t in name.lower() for t in prompt_tokens):
            continue
        name_tokens = _tokenise(name.replace("ai-", ""))
        name_match = len(prompt_tokens & name_tokens)
        score = overlap + 2 * name_match
        scored.append((score, name, description))
    scored.sort(key=lambda row: (-row[0], len(row[2])))
    return scored


def _emit_telemetry(
    project_root: Path,
    *,
    session_id: str | None,
    correlation_id: str,
    matches: list[tuple[int, str, str]],
) -> None:
    event: dict = {
        "kind": "ide_hook",
        "engine": "claude_code",
        "timestamp": iso_now(),
        "component": "hook.runtime-progressive-disclosure",
        "outcome": "success",
        "correlationId": correlation_id,
        "schemaVersion": "1.0",
        "project": project_root.name,
        "source": "hook",
        "detail": {
            "hook_kind": "user-prompt-submit",
            "match_count": len(matches),
            "top_skills": [m[1] for m in matches[:_TOP_K]],
        },
    }
    if session_id:
        event["sessionId"] = session_id
    emit_event(project_root, event)


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "UserPromptSubmit":
        passthrough_stdin(ctx.data)
        return

    raw_prompt = ctx.data.get("prompt") or ctx.data.get("user_prompt") or ""
    if not isinstance(raw_prompt, str):
        passthrough_stdin(ctx.data)
        return

    stripped = raw_prompt.strip()
    if not stripped or stripped.startswith("/ai-") or stripped.startswith("/"):
        passthrough_stdin(ctx.data)
        return

    prompt_tokens = _tokenise(stripped)
    if len(prompt_tokens) < _MIN_PROMPT_TOKENS:
        passthrough_stdin(ctx.data)
        return

    skills = _read_skill_descriptions(ctx.project_root)
    if not skills:
        passthrough_stdin(ctx.data)
        return

    ranked = _rank_skills(prompt_tokens, skills)
    if not ranked:
        passthrough_stdin(ctx.data)
        return

    top = ranked[:_TOP_K]
    _emit_telemetry(
        ctx.project_root,
        session_id=ctx.session_id,
        correlation_id=get_correlation_id(),
        matches=top,
    )

    # Cap each description so the hint stays bounded.
    lines = [
        f"- /{name} — {description[:140].rstrip()}{'…' if len(description) > 140 else ''}"
        for _score, name, description in top
    ]
    hint = (
        "[runtime-progressive-disclosure] Skills ranked by relevance to your "
        "prompt (consider invoking one of these instead of free-form work):\n" + "\n".join(lines)
    )
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": hint,
                }
            },
            separators=(",", ":"),
        )
    )
    sys.stdout.flush()


if __name__ == "__main__":
    run_hook_safe(
        main,
        component="hook.runtime-progressive-disclosure",
        hook_kind="user-prompt-submit",
    )
