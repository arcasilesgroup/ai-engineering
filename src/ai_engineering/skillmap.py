"""The reference-integrity digest (spec 026).

`just map` runs `sm scan && sm check --json` and this module turns that into one number a
gate can hold honest: how many real broken references remain after the template holes
(`policy/skill-map-exclusions.toml`) and the accepted set (`policy/skill-map-accepted.toml`)
are taken out. A reference that is neither a declared template hole nor in the accepted set
is real, unaccepted breakage — the map prints it and exits non-zero.

This is the instrument the council asked for: the counts are computed from `sm check
--json` on every run, never read from a fixed number in a document. The two policy files
are data, not code: adding to the accepted set extends an acceptance that needs its own
dated record (docs/adr/0025), and the test suite refuses a template hole that is not
declared.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib

from ai_engineering import paths

_FAILURE = 1
_PASS = 0

# The version the recipe checks too (justfile `sm := "1.12.2"`). The module checks it as
# well rather than trusting the recipe's shell line alone, because the module can be
# reached directly (`uv run python -m ai_engineering.skillmap`, tests, a debugger) where
# the shell test has not run. A map from an engine of an untested version is not evidence.
SM_VERSION = "1.12.2"


def _load_toml(name: str) -> dict:
    return tomllib.loads(paths.policy(name).read_text(encoding="utf-8"))


def accepted_pairs() -> set[tuple[str, str]]:
    """The dated accepted (node, target) pairs from policy.

    Each entry is `node -> target` and only an exact pair is exempt, never a bare target
    name — a bare `SKILL.md` would forgive any future link with that name anywhere.
    """

    out: set[tuple[str, str]] = set()
    for entry in _load_toml("skill-map-accepted.toml").get("accepted", []):
        node, _, target = entry.partition(" -> ")
        if node and target:
            out.add((node.strip(), target.strip()))
    return out


def template_prefixes() -> list[str]:
    exclusions = _load_toml("skill-map-exclusions.toml")
    out = []
    for key in ("template", "nested_routes"):
        out.extend(exclusions.get(key, []))
    return out


def is_template(target: str, prefixes: list[str]) -> bool:
    """A demo hole if the marker is anywhere in the target.

    The exclusions file declares the `NNN-slug` convention as data; its exact spellings
    are the prefix list, but the *rule* is the marker. A skill-relative path like
    `specs/023-…/specs/NNN-slug/…` is a hole the same way the root form is — the marker
    is in it. `prefixes` is kept for the test that walks the tree, so the data file stays
    the one place the spellings are decided.
    """
    return "NNN-slug" in target


def main() -> int:
    prefixes = template_prefixes()
    accepted = accepted_pairs()

    # `sm` is the instrument; calling it is the point. Refuse the wrong version here rather
    # than trusting the recipe's shell line alone, and refuse a scan that returns nothing
    # usable: an empty scan voting green is the exact false-green the gate exists to stop.
    try:
        version = subprocess.run(
            ["sm", "--version"], capture_output=True, text=True, timeout=30
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as why:
        print(f"skill-map: sm could not run ({why})", file=sys.stderr)
        return _FAILURE
    if version != SM_VERSION:
        print(
            f"skill-map: sm is {version!r}, this gate is written for {SM_VERSION!r}",
            file=sys.stderr,
        )
        return _FAILURE

    try:
        check = subprocess.run(
            ["sm", "check", "--json"], capture_output=True, text=True, timeout=300
        )
    except (OSError, subprocess.SubprocessError) as why:
        print(f"skill-map: sm could not run ({why})", file=sys.stderr)
        return _FAILURE
    if check.returncode not in (0, 1):
        print(f"skill-map: sm check --json exited {check.returncode}", file=sys.stderr)
        return _FAILURE
    try:
        findings = json.loads(check.stdout)
    except json.JSONDecodeError:
        print("skill-map: sm check --json did not return JSON", file=sys.stderr)
        return _FAILURE

    real_remaining = []
    templates = 0
    for finding in findings:
        if finding.get("analyzerId") != "reference-broken":
            continue
        node = finding["nodeIds"][0]
        target = finding["data"].get("target", "")
        if is_template(target, prefixes):
            templates += 1
            continue
        if (node, target) in accepted:
            continue
        real_remaining.append((node, target))

    # The digest: what remains is what the gate is against, not a total that hides new
    # breakage. Node and target are repr'd so control bytes from a hostile scan cannot
    # reach the terminal or the log as escape sequences.
    print(
        f"skillmap: {len(findings)} findings | "
        f"{templates} template holes declared, "
        f"{len(accepted)} accepted, "
        f"{len(real_remaining)} real-and-unaccepted"
    )
    for node, target in sorted(set(real_remaining)):
        print(f"  REAL  {node!r} -> {target!r}")
    print("REAL_AND_UNACCEPTED=" + str(len(set(real_remaining))))
    if real_remaining:
        return _FAILURE
    return _PASS


if __name__ == "__main__":
    sys.exit(main())