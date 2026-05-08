"""``GitLogPort`` — extract adversarial near-miss phrases from git history.

The corpus generator wants real-world phrasings that *look like* a
trigger for a given skill but actually belong to a different one.
Twelve months of user commit messages are an excellent source: they
are written by the same human in the same style as the prompts the
skill will receive, so they exercise the optimizer with realistic
edge cases.

This port abstracts the ``git log --grep`` pipeline so:

- Tests can substitute a fixture that returns canned phrases, keeping
  the regression-gate suite deterministic across CI environments
  that may not have a full git history checked out (shallow clones).
- The infra adapter can switch to ``git log -S<token>`` or other
  advanced queries without churning the application layer.
"""

from __future__ import annotations

from typing import Protocol


class GitLogPort(Protocol):
    """Extract candidate near-miss phrases from local git history."""

    def find_near_miss_phrases(
        self,
        skill_name: str,
        skill_description: str,
        months: int = 12,
        max_phrases: int = 24,
    ) -> tuple[str, ...]:
        """Return up to ``max_phrases`` candidate adversarial phrases.

        Implementations may dedupe by lowercase normalized form and
        truncate to the most-recent matches when the corpus exceeds
        ``max_phrases``. Returning an empty tuple is a valid degraded
        result (e.g. shallow checkout, no matches found, git
        unavailable); the corpus generator falls back to LLM-only
        case authoring in that case.
        """
        ...
