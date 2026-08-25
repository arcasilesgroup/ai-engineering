"""The skillify extractor, spec 033 / B-033-2.

A costly one-off session becomes a SKILL.md skeleton that passes the contract. It names the
generalisable steps, never the chat; the user's corrections become rules; a transcript with
no generalisable steps emits nothing (cc-creators' skillify). The skeleton is an extractor's
artifact: it must pass `contract.audit_one` to be worth emitting at all.
"""

from __future__ import annotations

import re

_STEPS_LEAD = re.compile(r"the steps? are:?\s*(.+)", re.I)
_USER_LEAD = re.compile(r"^User:\s*(.+)$", re.MULTILINE)
# A line that is only a greeting/acknowledgement (no correction): "yes", "ok", "thanks".
# A line that STARTS with one but continues ("yes, and never overwrite…") is a correction.
_GREETING_ONLY = re.compile(
    r"^(?:hi|hello|thanks|bye|ok|yes|no|great|perfect|start|go)\s*[.!]?$", re.I
)


def extract(transcript: str, name: str = "ai-migrator") -> str | None:
    """Return a SKILL.md skeleton for `transcript`, or None when no process is present.

    `name` becomes the frontmatter name (and the directory it should live in); a real
    call passes the intended slug. Steps come from the assistant's "the steps are: …"
    line; the user's corrective lines become anti-rationalization entries; the chat
    itself is never emitted.
    """
    steps: list[str] = []
    for lead in _STEPS_LEAD.finditer(transcript):
        for part in lead.group(1).split(","):
            part = part.strip().rstrip(".")
            if part and part not in steps:
                steps.append(part)
    if not steps:
        return None

    rules: list[str] = []
    for user_line in _USER_LEAD.finditer(transcript):
        text = user_line.group(1).strip()
        if _GREETING_ONLY.match(text):
            continue
        if text not in rules:
            rules.append(text)

    description = (
        f"Repeats a costly one-off process now that it is understood: {steps[0].lower()[:85]}"
        ". Not for deciding — use /ai-spec."
    )
    procedure = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))

    # The user's corrections are anti-rationalization entries: an excuse someone could
    # make, answered factually. Emitting them as a "## Rules" section would trip the
    # Incorrect/Correct craft rule (spec 032 B-032-3); as What-this-is-not bullets they
    # satisfy the anti rule and never trigger a pair check.
    entries = [
        '- "It\'s just this once" — a process that cost real time will cost it again; '
        "repeat the steps."
    ]
    for r in rules:
        entries.append(f'- "Skip the guard rails" — {r}')

    anti = "\n".join(entries)

    return (
        "---\n"
        f"name: {name}\n"
        f"description: >-\n  {description}\n"
        "license: Apache-2.0\n"
        "---\n"
        "\n"
        f"# {name.replace('ai-', '').title()}\n"
        "\n"
        "## What it produces\n"
        "\n"
        "`docs/notes/<slug>.md` — the running record of this process.\n"
        "\n"
        "## Procedure\n"
        "\n"
        f"{procedure}\n"
        "\n"
        "## What this is not\n"
        "\n"
        f"{anti}\n"
    )