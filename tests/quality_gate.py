#!/usr/bin/env python3
"""The Quality Gate is a rule on somebody else's server. This reads it back.

`sonar.qualitygate.wait=true` fails the build when the gate is red and says nothing about
what the gate contains. Its conditions live in a web console, so a project admin can drop
new-code coverage from 80 to 0 and no diff in this repository records it — the scan stays
green and the badge stays the same colour. That is a claimed gate whose rule nobody can
read, which is the whole subject of this product.

So policy/quality-gate.toml declares what we require and this asks the API what is actually
configured. A live gate weaker than the declaration turns the build red here, in a diff,
with the metric named.

Usage: SONAR_TOKEN=... python tests/quality_gate.py [project-key] [organization]
"""

from __future__ import annotations

import json
import os
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://sonarcloud.io/api/qualitygates/"
# Stricter means: catches more. For a LT condition ("fail if less than") a higher threshold
# is stricter; for GT ("fail if greater than") a lower one is. An operator that changed is
# a different question being asked, and that is never silently acceptable.
STRICTER = {"LT": lambda live, want: live >= want, "GT": lambda live, want: live <= want}


def declared() -> dict[str, tuple[str, float]]:
    body = tomllib.loads((ROOT / "policy" / "quality-gate.toml").read_text(encoding="utf-8"))
    rows = body["conditions"]
    if not rows:
        raise ValueError("policy/quality-gate.toml declares no conditions, so this proved nothing")
    return {metric: (op, float(value)) for metric, (op, value) in rows.items()}


def request(endpoint: str, query: dict, token: str) -> dict:
    url = f"{API}{endpoint}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as answer:
        return json.load(answer)


def live(project: str, organization: str, token: str) -> dict[str, tuple[str, float]]:
    assigned = request("get_by_project", {"project": project, "organization": organization}, token)
    gate_id = assigned.get("qualityGate", {}).get("id")
    if gate_id is None:
        raise ValueError(f"SonarCloud named no Quality Gate for {project}")
    body = request("show", {"id": gate_id, "organization": organization}, token)
    found = {}
    for row in body.get("conditions", []):
        try:
            found[row["metric"]] = (row["op"], float(row["error"]))
        except (KeyError, TypeError, ValueError):
            continue
    return found


def main(project: str, organization: str, token: str) -> int:
    want, have = declared(), live(project, organization, token)
    problems = []
    for metric, (op, threshold) in want.items():
        if metric not in have:
            problems.append(f"{metric}: declared here, absent from the live gate")
            continue
        live_op, live_threshold = have[metric]
        if live_op != op:
            problems.append(f"{metric}: asks {live_op}, we declared {op} — a different question")
        elif not STRICTER[op](live_threshold, threshold):
            problems.append(
                f"{metric}: live {live_op} {live_threshold}, weaker than {op} {threshold}"
            )
    for line in problems:
        sys.stderr.write(f"  quality-gate: {line}\n")
    if problems:
        sys.stderr.write(
            "  The gate on SonarCloud is weaker than policy/quality-gate.toml says it is. "
            "Restore it there, or change the declaration here in a diff somebody reviews.\n"
        )
        return 1
    print(f"quality-gate: {len(want)} conditions, and the live gate is at least this strict.")
    return 0


def configured() -> tuple[str, str]:
    rows = {}
    for line in (ROOT / "sonar-project.properties").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            rows[key.strip()] = value.strip()
    try:
        return rows["sonar.projectKey"], rows["sonar.organization"]
    except KeyError as why:
        raise ValueError(f"sonar-project.properties has no {why.args[0]}") from why


if __name__ == "__main__":
    configured_key, configured_org = configured()
    key = sys.argv[1] if len(sys.argv) > 1 else configured_key
    organization = sys.argv[2] if len(sys.argv) > 2 else configured_org
    secret = os.environ.get("SONAR_TOKEN", "")
    if not secret:
        # Not a pass. A person running the suite has no token and this is not their gate.
        sys.exit("quality-gate: no SONAR_TOKEN, so nothing was read back. This did not run.")
    try:
        sys.exit(main(key, organization, secret))
    except (urllib.error.URLError, OSError, ValueError) as why:
        sys.exit(f"quality-gate: could not read the live gate ({why}). Undecided is not green.")
