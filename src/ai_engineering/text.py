"""Reading the record.

Decisions and risk acceptances live as yaml blocks inside the spec markdown: GitHub
renders them, this reads them, and the diff reviews them. That is the whole storage
layer — there is no decision store to rebuild and no three-way disagreement about which
file was canonical.

The parser is strict on purpose. A partitioning parser that guesses is how a malformed
block passes a gate and then fails a human six weeks later.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

KEY = re.compile(r"^([a-zA-Z][\w.-]*):\s*(.*)$")


def flat_yaml(text: str, *, strict: bool = False) -> dict:
    """Flat mappings, one level, with folded scalars. Anything else raises, because the
    formats this reads are ones we defined and a surprise in them is a defect.

    `strict` adds the acceptance recognizer's refusals: a container (`-`, `?`, `[`, `{`)
    where a value belongs, and a repeated key. The frozen acceptance blocks are parsed
    with the same loop the record reads with, so the two cannot drift (spec 044)."""
    data: dict[str, str] = {}
    key = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")):
            if key is None:
                raise ValueError(f"indents a line with no key above: {raw.strip()!r}")
            if strict and raw.lstrip().startswith(("-", "?")):
                raise ValueError(f"holds a container where a value: {raw.strip()!r}")
            data[key] = (data[key] + " " + raw.strip()).strip()
            continue
        found = KEY.match(raw)
        if not found:
            raise ValueError(f"holds a line that is not a key: {raw!r}")
        key, value = found.group(1), found.group(2).strip()
        if strict and key in data:
            raise ValueError(f"repeats the key {key}")
        if strict and value.startswith(("[", "{")):
            raise ValueError(f"holds a container where a value: {raw.strip()!r}")
        data[key] = "" if value in (">", ">-", "|", "|-") else value.strip("\"'")
    return data


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} has no frontmatter")
    _, block, _ = text.split("---\n", 2)
    return flat_yaml(block)


def yaml_blocks(text: str, where: str = "") -> list[dict]:
    """A block that cannot be parsed raises. It used to be caught and skipped, so an
    acceptance whose YAML was slightly wrong vanished from the expiry check that both
    `pre-push` and `doctor` read, and the gate reported green over a risk that had run
    out. Silence on a parse failure is the exact shape of a false green, and this product
    is sold on not producing them: undecidable is an answer, invisible is not."""
    out = []
    for block in re.findall(r"^```yaml\n(.*?)^```", text, re.S | re.M):
        try:
            out.append(flat_yaml(block))
        except ValueError as why:
            raise ValueError(f"{where or 'a record block'} cannot be read: {why}") from why
    return out


WIDTH = 96


def render(fields: dict) -> str:
    """Long values are folded onto indented continuation lines, which `flat_yaml` above
    already reads back by joining them with a single space. Written on one physical line, a
    four-hundred-character rationale is invisible in a diff — and a governance record
    nobody can read in a diff is a record nobody reviews."""
    lines = []
    for key, value in fields.items():
        # Neither break: a word cut in half comes back with a space inside it, and the
        # round trip through `flat_yaml` is what makes this format survive being edited.
        lines += textwrap.wrap(
            f"{key}: {value}",
            WIDTH,
            subsequent_indent="  ",
            break_long_words=False,
            break_on_hyphens=False,
        )
    return "```yaml\n{}\n```\n".format("\n".join(lines))
