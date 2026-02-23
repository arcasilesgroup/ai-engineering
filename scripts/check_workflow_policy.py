"""Workflow policy sanity checks for GitHub Actions files.

Current enforced policies:
- No use of `pull_request_target` trigger.
- Top-level `permissions` key must be present.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def main() -> int:
    workflows = sorted(Path(".github/workflows").glob("*.yml"))
    failures: list[str] = []

    for workflow in workflows:
        data = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            failures.append(f"{workflow}: workflow root must be a mapping")
            continue

        triggers = data.get("on")
        if isinstance(triggers, dict) and "pull_request_target" in triggers:
            failures.append(f"{workflow}: 'pull_request_target' is not allowed")

        if "permissions" not in data:
            failures.append(f"{workflow}: missing top-level permissions block")

    if failures:
        print("workflow policy check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"workflow policy check passed ({len(workflows)} workflow files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
