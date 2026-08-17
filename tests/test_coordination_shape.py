"""The shapes this coordination must never grow, as tests that fail when one appears.

Specification 013 records four of them as non-goals: a bare force push, a background rebase
or per-commit publication, an ownership store with heartbeats and TTL takeover, and a
coordination record carrying a prompt, reasoning, client, user, hostname, absolute path or
provider payload.

A non-goal with no check is a sentence, and the shape arrives six months later in a commit
that looked reasonable on its own. Every scan here plants the shape first and asserts the
scan finds it, because a scan that finds nothing and a scan that looked at nothing print the
same result.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The tree these assertions are about, which is not always the tree they run in. The
# mutation harness copies the repository and lets mutmut rewrite `src/`: every function
# becomes a dispatcher plus a dict of variants, so a check that counts one occurrence of a
# string in a module counts it once per variant and fails on a file nobody wrote. That is
# what happened to the single-writer count below — it read a generated artifact and
# reported "more than one place publishes a claim" about code that publishes from one.
# `AI_ENG_REAL_SRC` names the `src/` those mutants were generated from.
SOURCE = Path(os.environ["AI_ENG_REAL_SRC"]).parent if os.environ.get("AI_ENG_REAL_SRC") else ROOT
SEARCHED = ("src/ai_engineering", "hooks", "git-hooks", ".github/workflows")


def sources() -> list[tuple[str, str]]:
    """Every file the product can execute, as (name, body)."""
    found: list[tuple[str, str]] = []
    for folder in SEARCHED:
        where = ROOT / folder
        for path in sorted(where.rglob("*")):
            if path.is_file() and path.suffix in ("", ".py", ".yml", ".yaml", ".sh"):
                found.append((str(path.relative_to(ROOT)), path.read_text(encoding="utf-8")))
    return found


def hits(pattern: re.Pattern[str], bodies: list[tuple[str, str]]) -> list[str]:
    return [name for name, body in bodies if pattern.search(body)]


# A bare force replaces whatever is on the server with whatever is here, including work
# somebody else pushed thirty seconds ago. The lease form asks the server whether it still
# holds what we last saw, which is the difference between overwriting and refusing.
#
# Read per line and only where a push is: `uv tool install --force` and `ai-eng update
# --force` are neither pushes nor destructive to anybody else's work, and a pattern that
# flagged them would be one somebody switches off.
BARE_FORCE = re.compile(r"^.*\bpush\b.*--force(?!-with-lease|-if-includes)\b.*$", re.MULTILINE)


def test_no_bare_force_push_exists_anywhere_the_product_can_run_it():
    """EP-190. Every push is fast-forward or compare-and-swap against an exact SHA."""
    bodies = sources()
    assert hits(BARE_FORCE, [("planted", "git push --force origin main")]) == ["planted"]
    assert hits(BARE_FORCE, [("leased", "git push --force-with-lease origin main")]) == []
    assert hits(BARE_FORCE, [("elsewhere", "uv tool install --force dist/x.whl")]) == []
    assert hits(BARE_FORCE, bodies) == []


# "Background" is the part that matters: a rebase somebody asked for is a person's decision,
# and a rebase this framework performs while nobody is watching rewrites history under the
# writer who is still working on it.
BACKGROUND_REBASE = re.compile(r'"rebase"|\brebase\b\s*(?:--autostash|--onto)|git rebase')
PER_COMMIT_PUBLICATION = re.compile(r"push.*(?:after (?:each|every) commit|per[- ]commit)")


def test_nothing_rebases_in_the_background_or_publishes_every_commit():
    """EP-191. A stale base is a refusal, and the refusal is the answer — not a rebase, and
    not a loop that pushes each commit as it appears."""
    bodies = sources()
    planted = [
        ("rebase", 'subprocess.run(["git", "rebase", "origin/main"])'),
        ("autopush", "push the branch after each commit"),
    ]
    assert hits(BACKGROUND_REBASE, planted) == ["rebase"]
    assert hits(PER_COMMIT_PUBLICATION, planted) == ["autopush"]
    assert hits(BACKGROUND_REBASE, bodies) == []
    assert hits(PER_COMMIT_PUBLICATION, bodies) == []


# An ownership store is a second source of truth about who holds what, and the moment it
# disagrees with the remote there is no way to tell which is right. A heartbeat and a TTL
# takeover are how it stops disagreeing: by deciding somebody is gone and taking their work.
#
# Scoped to the files that coordinate, and said so rather than searched everywhere: the
# OpenCode surface has a heartbeat, which is a liveness probe for a plugin and has nothing
# to do with who holds a task. A pattern that could not tell those apart would be answered
# by renaming a variable.
# Word boundaries, and `expire` deliberately absent. Bare `ttl` matches "settle", which is
# how the first version of this failed on its own prose; and a receipt expiring is a
# required concept two files over — `checkpoint` reads a stale receipt as no receipt — so a
# pattern that banned the word would ban the control beside it.
OWNERSHIP_STORE = re.compile(
    r"\bheartbeat\b|\bownership[_ ]store\b|\bttl\b|\btakeover\b|\bsteals?\b"
)
COORDINATION = (
    "src/ai_engineering/claim.py",
    "src/ai_engineering/checkpoint.py",
    "src/ai_engineering/dag.py",
    "hooks/claim_scope_guard.py",
)


def test_no_ownership_store_no_heartbeat_and_no_ttl_takeover():
    """EP-192. The branch on the remote is the only record of who holds a work item, and a
    claim is released by the writer rather than expired by a clock."""
    coordinating = [(name, (SOURCE / name).read_text(encoding="utf-8")) for name in COORDINATION]
    assert len(coordinating) == 4, "the coordination surface moved and this list did not"
    assert hits(OWNERSHIP_STORE, [("planted", "heartbeat = 30  # seconds")]) == ["planted"]
    assert hits(OWNERSHIP_STORE, coordinating) == []


def test_a_coordination_record_carries_only_the_fields_it_is_allowed():
    """EP-193, read off the record this product actually writes rather than off a grep.

    The seven forbidden classes have no field to arrive in, and the two scanners in
    `claim.take` are what stops one arriving inside an allowed field anyway."""

    from ai_engineering import claim

    body = claim.record("work-42", "a" * 40, ["src/thing.py"], "writer-one", "abc123")
    keys = {line.split(" ", 1)[0] for line in body.splitlines() if line.strip()}

    assert keys == {"claim", "base", "role", "claimant", "path"}
    for forbidden in ("prompt", "reason", "client", "user", "host", "provider", "model"):
        assert forbidden not in body, forbidden


def test_the_claim_module_names_no_second_writer_of_ownership():
    """One writer per work item is the rule, and it holds because there is one place the
    answer is written. A second one — a file, a table, a lock directory — is what this
    checks has not appeared beside it."""

    from ai_engineering import claim

    body = (SOURCE / "src" / "ai_engineering" / "claim.py").read_text(encoding="utf-8")
    # The remote ref, and the local file that only mirrors it for the guard to read.
    written = re.findall(r'"push"|IN_FORCE|open\(|write_text', body)
    assert written.count('"push"') == 1, "more than one place publishes a claim"
    assert claim.REF.startswith("refs/"), claim.REF


def test_the_intent_schema_gained_no_runtime_coordination_field():
    """EP-181. The Solution Intent is durable context — what is fixed, what varies, what is
    true now, what is intended. A claim, a base SHA or a lease in there would make a
    long-lived record carry the state of one afternoon's run, and the record would be wrong
    by the next morning without anybody editing it."""

    import json

    schema = json.loads((ROOT / "policy" / "intent-v1.schema.json").read_text(encoding="utf-8"))
    body = json.dumps(schema)
    for runtime in ("claim", "base_sha", "worktree", "lease", "branch", "writer"):
        assert runtime not in body, f"the Intent schema grew a runtime field: {runtime}"

    top = set(schema["properties"])
    assert top == {
        "schema",
        "schema_version",
        "type",
        "identity",
        "solution_intent",
        "ownership",
        "relations",
        "lifecycle",
    }, sorted(top)


def test_ci_verifies_a_branch_against_its_claim_only_when_one_exists():
    """EP-184. The gate runs where the diff is, and says "not applicable" out loud when the
    branch holds no claim — rather than passing quietly, which reads the same as passing."""

    workflow = (ROOT / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")
    assert "spec checkpoint" in workflow
    step = workflow.split("spec checkpoint", 1)[0]
    assert "ls-remote" in step, "the step never asks whether a claim exists"
    assert "not applicable" in workflow
