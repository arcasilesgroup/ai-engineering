#!/usr/bin/env python3
"""Plant a pack of known defects into a working repo, on a scratch branch.

The answer key never enters the repo. It is written to a run directory outside
the working tree, because a review that finds the planted bugs by reading the
list of planted bugs tells you nothing.

Usage:
    plant.py --pack evals/packs/example-node-web/answer-key.json [--repo .] [--out DIR]
    plant.py --cleanup                      # from inside the repo, drop the scratch branch

Stdlib only. Python 3.8+.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime

RUN_ROOT = pathlib.Path.home() / ".claude" / "evals"


def die(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(1)


def git(repo, *args, check=True):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        die("git {} failed:\n{}".format(" ".join(args), proc.stderr.strip()))
    return proc.stdout.strip()


def require_clean(repo):
    if git(repo, "status", "--porcelain"):
        die(
            "working tree is dirty. Commit or stash first — planting on top of "
            "uncommitted work makes the diff scope meaningless."
        )


def line_of(text, index):
    return text.count("\n", 0, index) + 1


def apply_bug(repo, bug):
    """Apply one find/replace edit. Returns the 1-indexed line it landed on."""
    path = pathlib.Path(repo) / bug["file"]
    if not path.exists():
        die("bug {}: file not found: {}".format(bug["id"], bug["file"]))

    text = path.read_text(encoding="utf-8")
    find = bug["find"]
    hits = [m.start() for m in re.finditer(re.escape(find), text)]

    if not hits:
        die(
            "bug {}: `find` text not present in {}. The pack has drifted from "
            "the repo — update the pack, do not loosen the match.".format(
                bug["id"], bug["file"]
            )
        )

    want = bug.get("occurrence")
    if want is None:
        if len(hits) > 1:
            die(
                "bug {}: `find` matches {} times in {}. Make it unique or set "
                '"occurrence".'.format(bug["id"], len(hits), bug["file"])
            )
        idx = hits[0]
    else:
        if want < 1 or want > len(hits):
            die(
                "bug {}: occurrence {} requested, only {} matches".format(
                    bug["id"], want, len(hits)
                )
            )
        idx = hits[want - 1]

    line = line_of(text, idx)
    path.write_text(text[:idx] + bug["replace"] + text[idx + len(find):], encoding="utf-8")
    return line


def resolve_lines(repo, bugs):
    """Re-derive line numbers from the final file contents.

    Two bugs in one file shift each other, so apply-time lines are only a
    fallback (used when `replace` is empty, i.e. a deletion).
    """
    for bug in bugs:
        replace = bug["replace"]
        if not replace.strip():
            bug["line"] = bug["line_at_apply"]
            bug["line_candidates"] = [bug["line_at_apply"]]
            continue
        text = (pathlib.Path(repo) / bug["file"]).read_text(encoding="utf-8")
        hits = [line_of(text, m.start()) for m in re.finditer(re.escape(replace), text)]
        bug["line_candidates"] = hits or [bug["line_at_apply"]]
        bug["line"] = bug["line_candidates"][0]


def cleanup(repo):
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if not branch.startswith("eval/"):
        die("current branch is {!r}, not an eval branch. Refusing.".format(branch))
    require_clean(repo)
    git(repo, "checkout", "-")
    git(repo, "branch", "-D", branch)
    print("removed branch {}".format(branch))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", help="path to an answer-key.json")
    ap.add_argument("--repo", default=".", help="repo to plant into (default: cwd)")
    ap.add_argument("--out", help="run directory (default: ~/.claude/evals/<repo>-<stamp>)")
    ap.add_argument("--branch", help="branch name (default: eval/<pack>-<stamp>)")
    ap.add_argument("--cleanup", action="store_true", help="delete the current eval branch")
    args = ap.parse_args()

    repo = pathlib.Path(args.repo).resolve()
    if not (repo / ".git").exists():
        die("{} is not a git repository".format(repo))

    if args.cleanup:
        cleanup(repo)
        return

    if not args.pack:
        die("--pack is required (or --cleanup)")

    pack = json.loads(pathlib.Path(args.pack).read_text(encoding="utf-8"))
    bugs = pack.get("bugs") or []
    if not bugs:
        die("pack contains no bugs")

    ids = [b["id"] for b in bugs]
    if len(set(ids)) != len(ids):
        die("duplicate bug ids in pack")

    require_clean(repo)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = git(repo, "rev-parse", "HEAD")
    base_branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    branch = args.branch or "eval/{}-{}".format(pack.get("pack", "pack"), stamp)

    git(repo, "checkout", "-b", branch)

    for bug in bugs:
        bug["line_at_apply"] = apply_bug(repo, bug)
    resolve_lines(repo, bugs)

    git(repo, "add", "-A")
    git(repo, "commit", "-m", "eval: plant {} ({} defects)".format(pack.get("pack"), len(bugs)))
    head = git(repo, "rev-parse", "HEAD")

    out = pathlib.Path(args.out) if args.out else RUN_ROOT / "{}-{}".format(repo.name, stamp)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "pack": pack.get("pack"),
        "planted_at": stamp,
        "repo": str(repo),
        "base_branch": base_branch,
        "base_commit": base,
        "branch": branch,
        "head_commit": head,
        "bugs": bugs,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("planted {} defects on branch {}".format(len(bugs), branch))
    for bug in bugs:
        print("  {:<4} {:<24} {}:{}".format(bug["id"], bug["class"], bug["file"], bug["line"]))
    print()
    print("answer key: {}".format(manifest_path))
    print("  It is outside the repo on purpose. Do not show it to the reviewer,")
    print("  do not paste it into the session, do not let an agent read it.")
    print()
    print("next:")
    print("  1. run the review skill under test against `{}...HEAD`".format(base_branch))
    print("  2. score.py --run {}".format(manifest_path))
    print("  3. plant.py --repo {} --cleanup".format(repo))


if __name__ == "__main__":
    main()
