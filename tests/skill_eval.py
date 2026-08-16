#!/usr/bin/env python3
"""The repeatable evaluation of the skill corpus, which is code because it is repeatable.

`ai-reliability-eval` was absorbed with an instruction: turn it into a CI harness for
skills, because an evaluation that always decides the same way is a script and not a
prompt. That is rule 12 applied to our own corpus, and until now `just check` evaluated a
skill's format and nothing about what it routes.

What this evaluates is routing, and routing is decidable. Each skill's description names
the situations it claims — the trigger phrases — and the situations it refuses, each
refusal naming where the work goes instead. Those two lists are a graph over the corpus,
and a graph has properties a machine can settle without a model in the loop:

- a skill that claims nothing is a skill nothing reaches;
- two skills claiming the same situation is a fork with no rule for taking it;
- a refusal pointing at a skill that is not there, or at a command this CLI does not have,
  is a dead end that reads like a route;
- a skill refusing work to itself is a loop;
- and a refusal naming one destination while a third skill claims that same situation is
  the corpus disagreeing with itself, which is the defect this repository keeps finding in
  its own files under a different name.

Beside every skill is a `corpus.md` the admission gate already demands: the cases it must
take and the cases it must refuse, each refusal naming the skill that should have it. That
is a labelled routing set, and until this ran the only thing reading it checked that the two
headings existed with a bullet under each. So the rules above are answered twice — once by a
skill's description against the other descriptions, and once by the cases somebody wrote
down. A routing evaluation with no sample is a self-consistency check wearing an
evaluation's name.

What it does not evaluate: whether the instructions inside a skill are any good. No model
runs here, nothing is scored for quality, and a corpus that passes this has been shown to
route consistently and nothing more. Saying so is the point — the alternative is a green
that reads like an evaluation of the writing.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"

_TRIGGER = re.compile(r'"([^"]+)"')
# The whole tail after the dash, and not only the tails that begin with "use". Requiring
# that word made the rule below — a refusal that names nowhere to take the work — unreachable
# from any file in the tree: five of the thirty-one written clauses were invisible to this
# harness, including the one clause that names no destination at all, which is the case the
# rule exists for. A check that cannot see the input it was written for is the defect this
# repository is named after, so the regex reads every clause and the classification happens
# below, where it can be argued with.
_REFUSAL = re.compile(r"Not for ([^.]*?)\s*[—:]\s*([^.]+)")
_SKILL_TARGET = re.compile(r"/(ai-[a-z-]+)")
_VERB_TARGET = re.compile(r"`ai-eng ([a-z-]+)")


def description(body: str) -> str:
    """The folded description, on one line. Read from the raw file rather than through a
    YAML parser: an indented comment a parser discards is an instruction a reader keeps."""

    if "description: >-" not in body:
        return ""
    folded = body.split("description: >-", 1)[1].split("\nlicense:", 1)[0]
    return " ".join(line.strip() for line in folded.splitlines()).strip()


def corpus(root: Path | None = None) -> dict[str, dict]:
    """Every skill, with what it claims and what it refuses.

    The default is read on the call and not bound to the signature: a default argument is
    evaluated once at import, so a harness pointed at another tree would have gone on
    reading this one and reported a pass about a corpus it never opened."""

    found: dict[str, dict] = {}
    for skill in sorted((SKILLS if root is None else root).iterdir()):
        if not (skill / "SKILL.md").is_file():
            continue
        text = description((skill / "SKILL.md").read_text(encoding="utf-8"))
        found[skill.name] = {
            "claims": [phrase.lower() for phrase in _TRIGGER.findall(text)],
            "refusals": [
                (subject.strip().lower(), target.strip())
                for subject, target in _REFUSAL.findall(text)
            ],
            **cases(skill),
        }
    return found


def _section(body: str, heading: str) -> list[str]:
    part = body.partition(heading)[2].partition("\n## ")[0]
    return [line.strip()[2:].strip() for line in part.splitlines() if line.strip().startswith("- ")]


def cases(skill: Path) -> dict[str, list]:
    """The labelled cases beside a skill, which are the sample this evaluation runs on.

    `corpus.md` is required before a skill may land — a case it must take and a case it must
    refuse — and until now the only thing that read it checked that the two headings were
    there with a bullet under each. That is a shape check. The cases themselves are a
    labelled routing set: each refusal quotes a situation and names the skill that should
    have it, which is exactly what an evaluation needs and nothing was running.

    A row that is not a quoted situation is skipped rather than guessed at. The admission
    gate already refuses a corpus with no rows at all, so silence here cannot hide an empty
    file — and inventing a label out of unquoted prose would put this harness in the business
    of deciding what somebody meant.
    """

    body = (
        (skill / "corpus.md").read_text(encoding="utf-8") if (skill / "corpus.md").is_file() else ""
    )
    takes = []
    for row in _section(body, "## Routes here"):
        quoted = re.match(r'"([^"]+)"', row)
        if quoted:
            takes.append(quoted.group(1).lower())
    sends = []
    for row in _section(body, "## Refuses"):
        quoted = re.match(r'"([^"]+)"', row)
        target = _SKILL_TARGET.search(row)
        if quoted:
            sends.append((quoted.group(1).lower(), target.group(1) if target else ""))
    return {"takes": takes, "sends": sends}


def verbs() -> set[str]:
    """The CLI's verbs, read from the package where they are declared. A refusal that sends
    somebody to `ai-eng accept` is a route like any other, and it is worth exactly as much
    as the verb existing."""

    try:
        from ai_engineering import cli
    except ImportError:  # pragma: no cover - only outside the suite's path
        return set()
    return set(cli.VERBS)


def problems(found: dict[str, dict], known_verbs: set[str] | None = None) -> list[str]:
    """Every way this corpus does not route. All of them, not the first: a routing defect
    found one run at a time is one run per defect."""

    known = verbs() if known_verbs is None else known_verbs
    broken: list[str] = []

    for name, skill in found.items():
        if not skill["claims"]:
            broken.append(f"{name} claims no situation, so nothing routes to it")
        if not skill["refusals"]:
            broken.append(f"{name} refuses nothing, so it is the answer to every question")

    # Two skills claiming one situation is a fork with no rule for taking it, and a phrase
    # contained in another is the same fork with the ambiguity spelled out one word longer.
    for name, skill in found.items():
        for phrase in skill["claims"]:
            for other, rival in found.items():
                if other <= name:
                    continue
                for theirs in rival["claims"]:
                    if phrase == theirs:
                        broken.append(f'{name} and {other} both claim "{phrase}"')
                    elif phrase in theirs or theirs in phrase:
                        broken.append(
                            f'{name} claims "{phrase}" and {other} claims "{theirs}"; '
                            "one contains the other and nothing decides between them"
                        )

    # The labelled cases, run. Everything above evaluates a skill's description against the
    # other descriptions; this evaluates the sample somebody wrote down as what the skill
    # must take and what it must send away — and a routing evaluation with no sample is a
    # self-consistency check wearing an evaluation's name.
    for name, skill in found.items():
        for case in skill.get("takes", []):
            for other, rival in found.items():
                if other <= name:
                    continue
                if case in rival.get("takes", []):
                    broken.append(f'{name} and {other} both take the case "{case}"')
        for case, target in skill.get("sends", []):
            if case in skill.get("takes", []):
                broken.append(f'{name} both takes and refuses the case "{case}"')
            if not target:
                continue
            if target == name:
                broken.append(f'{name} sends the case "{case}" to itself')
            elif target not in found:
                broken.append(f'{name} sends the case "{case}" to {target}, which is not a skill')
            elif any(case == theirs for theirs, _ in found[target].get("sends", [])):
                # The one this exists to catch. Two skills refusing the same case leaves the
                # person who wrote it with nowhere to go, and each file is defensible on its
                # own — which is why nothing that reads one file at a time can see it.
                broken.append(f'{name} sends the case "{case}" to {target}, which refuses it too')

    for name, skill in found.items():
        for subject, target in skill["refusals"]:
            to_skill = _SKILL_TARGET.search(target)
            to_verb = _VERB_TARGET.search(target)
            if to_skill:
                if to_skill.group(1) == name:
                    broken.append(f'{name} refuses "{subject}" to itself')
                elif to_skill.group(1) not in found:
                    broken.append(
                        f'{name} sends "{subject}" to {to_skill.group(1)}, which is not a skill'
                    )
            elif to_verb:
                if to_verb.group(1) not in known:
                    broken.append(
                        f'{name} sends "{subject}" to `ai-eng {to_verb.group(1)}`, '
                        "which is not a verb this CLI has"
                    )
            elif not target.strip():
                broken.append(f'{name} refuses "{subject}" and names nowhere to take it')
            # A destination outside the catalogue is legal and stays legal. Three of them
            # are written today — the repository's own docs, the person saying go, and the
            # gate in CI — and none of the three has a skill, because no skill owns them.
            # Requiring one would have made this harness demand a fake route to satisfy
            # itself, which is worse than the silence it replaced. What it does instead is
            # count them and print them, so a hand-off out of the framework is something a
            # reader sees rather than something that reads as an absence.

            # And the corpus has to agree with itself: a refusal naming one destination
            # while a third skill claims that same situation leaves the reader with two
            # answers and the file that is wrong is not identifiable from either side.
            destination = to_skill.group(1) if to_skill else None
            for other, rival in found.items():
                if other in (name, destination):
                    continue
                for theirs in rival["claims"]:
                    if theirs in subject or (len(subject) > 12 and subject in theirs):
                        broken.append(
                            f'{name} sends "{subject}" to {target}, but {other} claims "{theirs}"'
                        )
    return broken


def main() -> int:
    try:
        found = corpus()
    except OSError as why:  # pragma: no cover - a corpus that cannot be read
        print(f"  the skill corpus could not be read: {type(why).__name__}", file=sys.stderr)
        return 1

    if not found:
        print("  no skills were found, so this evaluated nothing", file=sys.stderr)
        return 1

    # The manifest is the only file that enumerates the capabilities, and a skill it never
    # declared is one nothing admitted. Read here rather than restated: the two files
    # disagreeing is the contradiction an audit found between them once already.
    declared = tomllib.loads((ROOT / "policy" / "capabilities.toml").read_text(encoding="utf-8"))
    names = {str(row["id"]) for row in declared["capabilities"]}
    undeclared = sorted(set(found) - names)
    if undeclared:
        print(f"  skills the manifest never declared: {undeclared}", file=sys.stderr)
        return 1

    broken = problems(found)
    if broken:
        for line in sorted(set(broken)):
            print(f"  {line}", file=sys.stderr)
        return 1

    claims = sum(len(skill["claims"]) for skill in found.values())
    refusals = [row for skill in found.values() for row in skill["refusals"]]
    leaves = [
        row
        for row in refusals
        if not _SKILL_TARGET.search(row[1]) and not _VERB_TARGET.search(row[1])
    ]
    takes = sum(len(skill["takes"]) for skill in found.values())
    sends = sum(len(skill["sends"]) for skill in found.values())
    labelled = [
        (case, target) for skill in found.values() for case, target in skill["sends"] if target
    ]
    print(f"  {len(found)} skills route {claims} situations and hand off {len(refusals)} more,")
    print(
        f"  measured against {takes + sends} labelled cases beside them — {takes} a skill must "
        f"take, {sends} it must refuse, {len(labelled)} of those naming the skill that has it —"
    )
    print("  with no situation claimed twice and no refusal naming a place that is not there.")
    print(f"  {len(leaves)} of those hand-offs leave the framework rather than naming a skill:")
    for subject, target in leaves:
        print(f"    elsewhere      {subject} — {target}")

    # The map, which is the only reason the manifest carries a phase at all. It was declared
    # for a person meeting the catalogue with no idea what any of it is for, and a field no
    # command ever shows that person is a field that answers nobody. This is the command
    # that shows it.
    by_phase: dict[str, list[str]] = {}
    for row in declared["capabilities"]:
        by_phase.setdefault(str(row["phase"]), []).append(str(row["id"]))
    print(f"  the {len(by_phase)} phases the catalogue is arranged in:")
    for phase in ("discover", "decide", "plan", "build", "verify"):
        print(f"    {phase:<14} {', '.join(sorted(by_phase.get(phase, ['—'])))}")

    print("  Nothing here evaluates whether a skill's instructions are any good.")
    print(f"RAN skilleval={claims + len(refusals) + takes + sends}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
