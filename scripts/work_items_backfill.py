#!/usr/bin/env python3
"""Backfill GitHub Project fields for existing issues.

Reads a YAML config with target field values per issue and applies them
via ``gh project item-edit``. Issue types are set via GraphQL (the CLI
does not support issue types natively).

Usage:
    python scripts/work_items_backfill.py                # dry-run (default)
    python scripts/work_items_backfill.py --apply         # apply changes
    python scripts/work_items_backfill.py --config path   # custom config
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

DEFAULT_CONFIG = Path(__file__).parent / "work_items_backfill.yml"

# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

MANIFEST_PATH = Path(__file__).resolve().parent.parent / ".ai-engineering" / "manifest.yml"


def load_manifest() -> dict:
    with MANIFEST_PATH.open() as f:
        return yaml.safe_load(f)


def get_project_source(manifest: dict) -> dict:
    for src in manifest.get("work_items", {}).get("sources", []):
        if src.get("type") == "github-projects":
            return src
    print("ERROR: No github-projects source found in manifest.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# gh CLI helpers
# ---------------------------------------------------------------------------


def run_gh(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"gh {' '.join(args)} failed:\n{result.stderr}", file=sys.stderr)
    return result


def get_project_item_id(project_id: str, issue_number: int, owner: str, repo: str) -> str | None:
    """Get the project item ID for a given issue number."""
    query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        issue(number: $number) {
          projectItems(first: 10) {
            nodes {
              id
              project { id }
            }
          }
        }
      }
    }
    """
    result = run_gh(
        [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"owner={owner}",
            "-f",
            f"repo={repo}",
            "-F",
            f"number={issue_number}",
        ],
        check=False,
    )
    if result.returncode != 0:
        return None
    data = json.loads(result.stdout)
    nodes = (
        data.get("data", {})
        .get("repository", {})
        .get("issue", {})
        .get("projectItems", {})
        .get("nodes", [])
    )
    for node in nodes:
        if node.get("project", {}).get("id") == project_id:
            return node["id"]
    return None


def set_single_select_field(
    project_id: str,
    item_id: str,
    field_id: str,
    option_id: str,
    *,
    dry_run: bool,
    label: str = "",
) -> bool:
    desc = f"  Set {label}: field={field_id} option={option_id}"
    if dry_run:
        print(f"  [DRY-RUN] {desc}")
        return True
    result = run_gh(
        [
            "project",
            "item-edit",
            "--id",
            item_id,
            "--project-id",
            project_id,
            "--field-id",
            field_id,
            "--single-select-option-id",
            option_id,
        ],
        check=False,
    )
    if result.returncode != 0:
        print(f"  FAIL {desc}: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"  OK   {desc}")
    return True


def set_date_field(
    project_id: str,
    item_id: str,
    field_id: str,
    value: str,
    *,
    dry_run: bool,
    label: str = "",
) -> bool:
    desc = f"  Set {label}: {value}"
    if dry_run:
        print(f"  [DRY-RUN] {desc}")
        return True
    result = run_gh(
        [
            "project",
            "item-edit",
            "--id",
            item_id,
            "--project-id",
            project_id,
            "--field-id",
            field_id,
            "--date",
            value,
        ],
        check=False,
    )
    if result.returncode != 0:
        print(f"  FAIL {desc}: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"  OK   {desc}")
    return True


def set_number_field(
    project_id: str,
    item_id: str,
    field_id: str,
    value: float,
    *,
    dry_run: bool,
    label: str = "",
) -> bool:
    desc = f"  Set {label}: {value}"
    if dry_run:
        print(f"  [DRY-RUN] {desc}")
        return True
    result = run_gh(
        [
            "project",
            "item-edit",
            "--id",
            item_id,
            "--project-id",
            project_id,
            "--field-id",
            field_id,
            "--number",
            str(value),
        ],
        check=False,
    )
    if result.returncode != 0:
        print(f"  FAIL {desc}: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"  OK   {desc}")
    return True


def set_issue_type(
    owner: str, repo: str, issue_number: int, type_name: str, *, dry_run: bool
) -> bool:
    """Set issue type via GraphQL (gh CLI doesn't support issue types)."""
    desc = f"  Set type: {type_name}"
    if dry_run:
        print(f"  [DRY-RUN] {desc}")
        return True

    # First get the issue node ID and available types
    query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        issue(number: $number) { id }
        issueTypes { id name }
      }
    }
    """
    result = run_gh(
        [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"owner={owner}",
            "-f",
            f"repo={repo}",
            "-F",
            f"number={issue_number}",
        ],
        check=False,
    )
    if result.returncode != 0:
        print(f"  FAIL {desc}: could not query issue: {result.stderr.strip()}", file=sys.stderr)
        return False

    data = json.loads(result.stdout)
    repo_data = data.get("data", {}).get("repository", {})
    issue_id = repo_data.get("issue", {}).get("id")
    issue_types = repo_data.get("issueTypes", [])

    if not issue_id:
        print(f"  FAIL {desc}: issue not found", file=sys.stderr)
        return False

    type_id = None
    for it in issue_types or []:
        if it.get("name", "").lower() == type_name.lower():
            type_id = it["id"]
            break

    if not type_id:
        available = [it.get("name") for it in (issue_types or [])]
        print(
            f"  SKIP {desc}: type '{type_name}' not found (available: {available})", file=sys.stderr
        )
        return True  # non-fatal — repo may not have issue types enabled

    mutation = """
    mutation($issueId: ID!, $issueTypeId: ID!) {
      updateIssueIssueType(input: {issueId: $issueId, issueTypeId: $issueTypeId}) {
        issue { id }
      }
    }
    """
    result = run_gh(
        [
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-f",
            f"issueId={issue_id}",
            "-f",
            f"issueTypeId={type_id}",
        ],
        check=False,
    )
    if result.returncode != 0:
        print(f"  FAIL {desc}: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"  OK   {desc}")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_config(path: Path) -> list[dict]:
    with path.resolve().open() as f:
        data = yaml.safe_load(f)
    return data.get("issues", [])


def backfill_issue(
    issue: dict,
    project_source: dict,
    owner: str,
    repo: str,
    *,
    dry_run: bool,
) -> bool:
    number = issue["number"]
    project_id = project_source["project_id"]
    fields = project_source["fields"]

    print(f"\n--- Issue #{number} ---")

    # Get item ID in the project
    item_id = get_project_item_id(project_id, number, owner, repo)
    if not item_id:
        print(f"  SKIP: Issue #{number} not found in project")
        return False

    ok = True

    # Priority
    if "priority" in issue:
        option_id = project_source["priority_options"].get(issue["priority"].lower())
        if option_id:
            ok &= set_single_select_field(
                project_id,
                item_id,
                fields["priority"],
                option_id,
                dry_run=dry_run,
                label="priority",
            )

    # Size
    if "size" in issue:
        option_id = project_source["size_options"].get(issue["size"].lower())
        if option_id:
            ok &= set_single_select_field(
                project_id, item_id, fields["size"], option_id, dry_run=dry_run, label="size"
            )

    # Status
    if "status" in issue:
        option_id = project_source["status_options"].get(issue["status"].lower())
        if option_id:
            ok &= set_single_select_field(
                project_id, item_id, fields["status"], option_id, dry_run=dry_run, label="status"
            )

    # Estimate (number field) — need field ID from manifest or config
    if "estimate" in issue:
        # Estimate field ID must be in the config or we discover it
        estimate_field_id = project_source.get("fields", {}).get("estimate")
        if estimate_field_id:
            ok &= set_number_field(
                project_id,
                item_id,
                estimate_field_id,
                issue["estimate"],
                dry_run=dry_run,
                label="estimate",
            )
        else:
            if dry_run:
                val = issue["estimate"]
                print(f"  [DRY-RUN] Set estimate: {val} (no field ID)")

    # Start date
    if "start_date" in issue:
        start_field_id = project_source.get("fields", {}).get("start_date")
        if start_field_id:
            ok &= set_date_field(
                project_id,
                item_id,
                start_field_id,
                issue["start_date"],
                dry_run=dry_run,
                label="start_date",
            )
        elif dry_run:
            val = issue["start_date"]
            print(f"  [DRY-RUN] Set start_date: {val} (no field ID)")

    # Target date
    if "target_date" in issue:
        target_field_id = project_source.get("fields", {}).get("target_date")
        if target_field_id:
            ok &= set_date_field(
                project_id,
                item_id,
                target_field_id,
                issue["target_date"],
                dry_run=dry_run,
                label="target_date",
            )
        elif dry_run:
            val = issue["target_date"]
            print(f"  [DRY-RUN] Set target_date: {val} (no field ID)")

    # Issue type (via GraphQL)
    if "type" in issue:
        ok &= set_issue_type(owner, repo, number, issue["type"], dry_run=dry_run)

    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill GitHub Project fields for issues.")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG, help="YAML config with issue data"
    )
    parser.add_argument("--owner", default="arcasilesgroup", help="GitHub org/owner")
    parser.add_argument("--repo", default="ai-engineering", help="Repository name")
    args = parser.parse_args()

    dry_run = not args.apply

    if dry_run:
        print("=== DRY-RUN MODE (use --apply to execute) ===\n")
    else:
        print("=== APPLY MODE ===\n")

    manifest = load_manifest()
    project_source = get_project_source(manifest)

    if not args.config.exists():
        print(f"Config not found: {args.config}", file=sys.stderr)
        print(
            "Create it with the issue data to backfill. See work_items_backfill.yml.",
            file=sys.stderr,
        )
        return 1

    issues = load_config(args.config)
    if not issues:
        print("No issues in config.")
        return 0

    print(f"Processing {len(issues)} issues...")
    all_ok = True
    for issue in issues:
        ok = backfill_issue(issue, project_source, args.owner, args.repo, dry_run=dry_run)
        all_ok &= ok

    mode = "DRY-RUN" if dry_run else "APPLY"
    status = "All OK" if all_ok else "Some failures — see above."
    print(f"\n{mode} complete. {status}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
