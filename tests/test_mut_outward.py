"""Nothing may reach outward without a human being asked, including the thing not built yet.

`EP-176` asks that self-grant be refused and that publication, secrets and deploy stay gated.
Three of the four execute and are tested elsewhere. The fourth had no test and could not have
one, because there is no deploy verb — so the row sat INCOMPLETE on an absence, which is the
weakest possible state: an absence nothing watches is indistinguishable from a gap nobody has
noticed yet, and it closes the day somebody adds the verb without anybody being told.

So the absence is executed. Every declared mode is read; any that carries a secret, a network
destination or a deploy-shaped purpose must declare a human gate, and today's answer is
printed as a count rather than as silence. Zero deploy modes and zero unscanned modes are
different facts and used to print the same word.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES = ROOT / "policy" / "capabilities.toml"

# What "reaching outward" means, in the words the table itself uses. A purpose or a host
# matching any of these is an action whose consequence leaves this machine.
OUTWARD = ("deploy", "release", "publish", "upload", "provision")


def modes() -> list[tuple[str, dict]]:
    declared = tomllib.loads(CAPABILITIES.read_text(encoding="utf-8"))["capabilities"]
    return [(f"{one['id']}.{mode['id']}", mode) for one in declared for mode in one["modes"]]


def test_every_mode_that_leaves_this_machine_asks_a_person_first():
    """The rule, over the fourteen modes that exist and any that arrive later.

    A mode reaches outward if it carries a secret, names a network destination, or writes a
    purpose that says so. Each one must declare a gate other than `never` — the gate is what
    a person is asked through, and `never` is the value that means nobody is.
    """

    ungated, scanned = [], 0
    for name, mode in modes():
        purposes = " ".join(str(one.get("purpose", "")) for one in mode.get("network", []))
        reaches = bool(mode.get("secrets")) or bool(mode.get("network"))
        reaches = reaches or any(word in purposes.casefold() for word in OUTWARD)
        if not reaches:
            continue
        scanned += 1
        if str(mode.get("human_gate", "never")) == "never":
            ungated.append(name)

    assert scanned, (
        "no declared mode carries a secret, a destination or an outward purpose, so this "
        "checked nothing. Either the table stopped declaring them or this stopped reading it."
    )
    assert not ungated, (
        f"{len(ungated)} of {scanned} modes leave this machine with no human gate: {ungated}. "
        '`human_gate = "never"` is the value that means nobody is asked.'
    )


def test_nothing_deploys_here_and_this_is_what_would_notice():
    """The half of `EP-176` that is an absence, executed rather than asserted.

    There is no deploy verb and no deploy mode. That is a true statement about today and a
    worthless one to write down, because a sentence in a note does not fire when somebody
    adds one. This does: the day a mode declares a deploy purpose it is counted, and the case
    above requires it to have a gate.

    The count is asserted at zero deliberately. When it stops being zero this fails, and the
    person who added the verb reads a sentence telling them the requirement it answers to —
    which is the moment the requirement is worth anything at all.
    """

    deploying = [
        name
        for name, mode in modes()
        if any(
            "deploy" in str(one.get("purpose", "")).casefold() for one in mode.get("network", [])
        )
    ]

    assert deploying == [], (
        f"{deploying} declare a deploy purpose. `EP-176` requires deploy to be gated: give "
        'each a human_gate other than "never", then change this case to name them rather '
        "than to expect none."
    )
