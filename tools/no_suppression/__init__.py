"""no_suppression — repo-wide anti-suppression gate (spec-128 sub-d).

Enforces ``CONSTITUTION.md`` Article VII: no ``# noqa``, ``# nosec``,
``# pragma: no cover``, ``NOSONAR``, ``# type: ignore``,
``// @ts-ignore``, ``// nolint``, ``// eslint-disable``, or Sonar
``sonar.issue.ignore.multicriteria`` directives are allowed unless an
explicit allowlist entry (optionally linked to a DEC) covers the file +
rule.

Console entry: ``python -m no_suppression`` and ``no_suppression``
(registered in ``pyproject.toml`` ``[project.scripts]``).
"""

from __future__ import annotations
