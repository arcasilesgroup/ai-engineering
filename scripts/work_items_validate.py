#!/usr/bin/env python3
"""Validate GitHub Project fields for all issues.

Audits every issue in the configured GitHub Project and checks that
required fields are populated. Fails with exit code 1 if any field is
missing.

Usage:
    python scripts/work_items_validate.py                  # all issues
    python scripts/work_items_validate.py --issues 79-86   # range
    python scripts/work_items_validate.py --issues 79,80   # specific
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

MANIFEST_PATH = Path(__file__).resolve().parent.parent / ".ai-engineering" / "manifest.yml"

REQUIRED_FIELDS = ["Priority", "Size", "Status"]
WARN_FIELDS = ["Estimate", "Start Date", "Target Date"]


def load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


def get_project_source(manifest: dict) -> dict:
    for src in manifest.get("work_items", {}).get("sources", []):
        if src.get("type") == "github-projects":
            return src
    print("ERROR: No github-projects source in manifest.", file=sys.stderr)
    sys.exit(1)


def run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def fetch_project_items(project_number: int, owner: str) -> list[dict]:
    """Fetch all items from a GitHub Project via gh CLI."""
    result = run_gh(
        [
            "project",
            "item-list",
            str(project_number),
            "--owner",
            owner,
            "--format",
            "json",
            "--limit",
            "200",
        ]
    )
    if result.returncode != 0:
        print(f"Failed to list project items: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(result.stdout)
    return data.get("items", [])


def parse_issue_range(spec: str) -> set[int]:
    """Parse '79-86' or '79,80,81' into a set of ints."""
    numbers: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            numbers.update(range(int(start), int(end) + 1))
        else:
            numbers.add(int(part))
    return numbers


def validate_spec_url(url: str | None) -> bool:
    """Validate that a spec URL is a GitHub URL, not a local path."""
    if not url:
        return True  # optional field
    return url.startswith(("http://", "https://"))


def validate_items(items: list[dict], issue_filter: set[int] | None) -> int:
    """Validate items and print a results table. Returns count of failures."""
    # Header
    print(f"\n{'#':>5}  {'Title':<50}  {'Type':<10}  ", end="")
    for f in REQUIRED_FIELDS:
        print(f"{f:<12}  ", end="")
    for f in WARN_FIELDS:
        print(f"{f:<14}  ", end="")
    print("Result")
    print("-" * 160)

    failures = 0
    warnings = 0

    for item in items:
        # Extract issue number from the item
        content = item.get("content", {})
        number = content.get("number")
        if number is None:
            continue
        if issue_filter and number not in issue_filter:
            continue

        title = content.get("title", "")[:48]
        item_type = content.get("type", "")

        row_fail = False
        row_warn = False

        print(f"{number:>5}  {title:<50}  {item_type:<10}  ", end="")

        # Check required fields
        for field_name in REQUIRED_FIELDS:
            value = item.get(field_name) or item.get(field_name.lower())
            if value:
                print(f"{'PASS':<12}  ", end="")
            else:
                print(f"{'FAIL':<12}  ", end="")
                row_fail = True

        # Check warn fields
        for field_name in WARN_FIELDS:
            # gh project item-list uses various key formats
            key = field_name.lower().replace(" ", " ")
            value = item.get(field_name) or item.get(key)
            if value:
                print(f"{'PASS':<14}  ", end="")
            else:
                print(f"{'WARN':<14}  ", end="")
                row_warn = True

        if row_fail:
            print("FAIL")
            failures += 1
        elif row_warn:
            print("WARN")
            warnings += 1
        else:
            print("PASS")

    print("-" * 160)
    print(f"\nTotal: {len(items)} items | {failures} failures | {warnings} warnings")

    if failures > 0:
        print("\nFAILED: Required fields missing on one or more issues.", file=sys.stderr)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GitHub Project fields for issues.")
    parser.add_argument(
        "--issues", type=str, help="Issue numbers to check (e.g., '79-86' or '79,80')"
    )
    parser.add_argument("--owner", default="arcasilesgroup", help="GitHub org/owner")
    parser.add_argument("--project", type=int, default=4, help="Project number")
    args = parser.parse_args()

    issue_filter = parse_issue_range(args.issues) if args.issues else None

    print(f"Validating Project #{args.project} ({args.owner})...")
    if issue_filter:
        print(f"Filtering: issues {sorted(issue_filter)}")

    items = fetch_project_items(args.project, args.owner)
    if not items:
        print("No items found in project.")
        return 0

    failures = validate_items(items, issue_filter)
    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
