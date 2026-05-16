"""``GitLogPort`` adapter — extract near-miss phrases via ``git log --grep``.

Sub-007 M6 infrastructure layer. The adapter delegates to the local
``git`` CLI via :mod:`subprocess`; failures (no git, shallow clone,
binary not on PATH) degrade gracefully to an empty tuple so the
corpus generator falls back to LLM-only authoring.

The query pattern strips the ``ai-`` prefix and treats each token in
the description as a candidate grep target. Results are deduplicated
by lowercase normalised form and capped at ``max_phrases`` to avoid
flooding the LLM prompt.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import UTC, datetime, timedelta

from skill_app.ports.git_log import GitLogPort


class GitLogAdapter(GitLogPort):
    """Find candidate near-miss phrases in the local git history."""

    def __init__(self, repo_root: str | None = None) -> None:
        self._repo_root = repo_root

    def find_near_miss_phrases(
        self,
        skill_name: str,
        skill_description: str,
        months: int = 12,
        max_phrases: int = 24,
    ) -> tuple[str, ...]:
        """Return up to ``max_phrases`` near-miss candidates from git log.

        Falls back to empty tuple when:
        - ``git`` is not on ``PATH``;
        - the subprocess returns non-zero (shallow clone, etc.);
        - no commits in the last ``months`` match the keyword.
        """
        if shutil.which("git") is None:
            return ()

        # Build the date floor as ISO-8601 so ``git log --since`` is
        # locale-independent. ``timedelta`` covers months as 30 days
        # (good enough for the +/- a few days noise floor of a
        # corpus generator seed).
        since = (datetime.now(UTC) - timedelta(days=months * 30)).date().isoformat()

        # Use the first non-stop word of the skill name as the grep
        # token. ``ai-debug`` ⇒ ``debug``. The full description is
        # too noisy to grep against literally.
        token = skill_name.removeprefix("ai-") or skill_name
        # ``--grep`` matches commit messages; ``-i`` case-insensitive;
        # ``--no-color`` keeps the parsing deterministic.
        cmd = [
            "git",
        ]
        if self._repo_root is not None:
            cmd.extend(["-C", self._repo_root])
        cmd.extend(
            [
                "log",
                "--no-color",
                f"--since={since}",
                "-i",
                f"--grep={token}",
                "--pretty=format:%s",
            ]
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError):
            return ()

        if result.returncode != 0:
            return ()

        # Dedupe by lowercase form, preserve original casing of the
        # first occurrence so the LLM sees natural phrasing.
        seen: set[str] = set()
        ordered: list[str] = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            key = stripped.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(stripped)
            if len(ordered) >= max_phrases:
                break

        # ``skill_description`` accepted for protocol fit; the adapter
        # currently uses only the skill name token. Future work may
        # weave description keywords into the grep pattern.
        del skill_description
        return tuple(ordered)


__all__ = ["GitLogAdapter"]
