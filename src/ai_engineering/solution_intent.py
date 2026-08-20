"""Render the Solution Intent a human reads, from the records a machine already keeps.

Nothing here decides anything. It reads what is already committed — spec frontmatter, plan
checkboxes, ADR headers, `.ai/intent.md`, the hook classes, the CLI verb table — and prints
one HTML page. If a fact is not in one of those files it does not appear on the page, which
is the only reason the page can be trusted after nobody has looked at it for a month.

The page carries the digest of everything it was built from. `staleness()` recomputes that
digest and says whether the file on disk is still about this tree, so `just check` can fail
on a page that quietly stopped being true. That is the whole freshness mechanism: no
timestamps, no watchers, no second copy of the data.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering import blocked as blocked_ledger
from ai_engineering import contract, outcome, readiness, spec


class Unreadable(outcome.Unreadable):
    """The tree could not be read, so there is nothing honest to render."""


PAGE = Path("docs") / "solution-intent.html"
DIGEST_MARK = "data-inputs-digest="

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_FIELD = re.compile(r"^(\w+):\s*\"?([^\"\n]*)\"?\s*$", re.M)


@dataclass
class Spec:
    ident: str
    slug: str
    title: str
    status: str
    date: str
    supersedes: str
    has_plan: bool
    done: int
    total: int
    bytes_spec: int
    bytes_plan: int
    checks: int = 0
    tasks: int = 0


@dataclass
class Decision:
    number: str
    title: str
    status: str
    path: str


@dataclass
class Tree:
    specs: list[Spec] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    intent: dict = field(default_factory=dict)
    skills: list[tuple[str, int]] = field(default_factory=list)
    guards: list[str] = field(default_factory=list)
    telemetry: list[str] = field(default_factory=list)
    verbs: dict[str, str] = field(default_factory=dict)
    src_lines: int = 0
    test_lines: int = 0
    ratio_max: float = 0.0
    boxes: list[tuple[str, str, str]] = field(default_factory=list)
    readiness_code: str = ""
    readiness_outcome: str = ""
    # What is waiting for a person, and how many candidates were looked at to find it.
    # A tuple because `Tree` is compared and replaced in tests, and both are in the
    # digest, so a halt recorded after the page was written makes it stale on the next
    # `just check` — which is the only thing that makes a recorded stop reach anybody.
    blocked: tuple[blocked_ledger.Row, ...] = ()
    considered: int = 0


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _frontmatter(body: str) -> dict[str, str]:
    found = _FRONTMATTER.match(body)
    if not found:
        return {}
    return {key: value.strip() for key, value in _FIELD.findall(found.group(1))}


def _title(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _specs(root: Path, tracked: set[str]) -> list[Spec]:
    rows: list[Spec] = []
    for folder in sorted((root / "specs").glob("*/")):
        spec_file = folder / "spec.md"
        # Tracked only. This page is committed, so an untracked or ignored directory under
        # `specs/` would be published into it — and the writer holding one would get a red
        # gate telling them to regenerate, which commits it.
        if not spec_file.is_file() or spec_file.relative_to(root).as_posix() not in tracked:
            continue
        body = _text(spec_file)
        front = _frontmatter(body)
        plan_file = folder / "plan.md"
        plan_body = _text(plan_file) if plan_file.is_file() else ""
        rows.append(
            Spec(
                ident=front.get("id", folder.name.split("-")[0]),
                slug=front.get("slug", folder.name),
                title=_title(body) or folder.name,
                status=front.get("status", "unknown"),
                date=front.get("date", ""),
                supersedes=front.get("supersedes", ""),
                has_plan=bool(plan_body),
                done=len(re.findall(r"^\s*[-*]\s*\[x\]", plan_body, re.M | re.I)),
                total=len(re.findall(r"^\s*[-*]\s*\[[ x]\]", plan_body, re.M | re.I)),
                # Counted by the module that owns the definition. Reading it here with a
                # third regex made this page say eleven where `plan_tasks` says fifteen —
                # and two of the last three blocks closed a two-definitions defect by name.
                checks=sum(1 for one in spec.plan_tasks(plan_body) if one.get("check")),
                tasks=len(spec.plan_tasks(plan_body)),
                bytes_spec=len(body.encode("utf-8")),
                bytes_plan=len(plan_body.encode("utf-8")),
            )
        )
    return rows


def _decisions(root: Path, tracked: set[str]) -> list[Decision]:
    rows: list[Decision] = []
    for found in sorted((root / "docs" / "adr").glob("*.md")):
        if found.relative_to(root).as_posix() not in tracked:
            continue
        body = _text(found)
        status = ""
        for line in body.splitlines():
            stripped = line.strip().lstrip("*- ").rstrip("*")
            if stripped.lower().startswith("status:"):
                # Quoted in eight of the thirteen, so `"accepted"` rendered grey with the
                # quote marks showing — a reader learning the opposite of the truth about
                # which decisions are settled.
                status = stripped.split(":", 1)[1].strip().strip('"').strip()
                break
        number = found.name.split("-", 1)[0]
        rows.append(
            Decision(
                number=number,
                title=_title(body) or found.stem,
                status=status or "recorded",
                path=f"docs/adr/{found.name}",
            )
        )
    return rows


def _hook_classes(root: Path) -> tuple[list[str], list[str]]:
    guards, telemetry = [], []
    for found in sorted((root / "hooks").glob("*.py")):
        if found.name.startswith("_"):
            continue
        body = _text(found)
        if "@guard" in body:
            guards.append(found.name)
        elif "@telemetry" in body:
            telemetry.append(found.name)
    return guards, telemetry


def _verbs(root: Path) -> dict[str, str]:
    body = _text(root / "src" / "ai_engineering" / "cli.py")
    block = re.search(r"VERBS[^=]*=\s*\{(.*?)\n\}", body, re.S)
    if not block:
        return {}
    return dict(re.findall(r'"([a-z-]+)":\s*"([^"]+)"', block.group(1)))


def _measured(root: Path) -> tuple[int, int]:
    """(tests, product) — counted by `contract`, never by a second walk.

    The page prints the two numbers the ratio gate enforces, so it reports the headroom the
    build actually has. An independent glob here drifted by 625 lines on its first day,
    because git's index and the filesystem disagree about anything not yet committed.

    It counted a third number until the line ceiling was deleted: the whole tree, with this
    page excluded from its own measurement so the freshness digest could settle. Nothing
    enforces that number any more, and a page that keeps printing a number nothing enforces
    is the shape this repository spends its gates refusing."""

    try:
        # Through `test_ratio`, not a count of the same names, because the ratio gate stopped
        # counting comment on either side and a page that kept counting it would print
        # headroom the build does not have — which is the drift this docstring is about.
        return contract.test_ratio(root)
    except (OSError, ValueError, subprocess.SubprocessError):
        return (0, 0)


def _readiness(root: Path, now: datetime) -> tuple[str, str, list[tuple[str, str, str]]]:
    """The eight production-ready boxes, as `readiness` verifies them.

    A missing declaration is not an empty section: it is INCOMPLETE for every box, which is
    the answer the record already gives in prose and the one this replaces with a computed
    one."""

    # ponytail: time-dependent once a declaration exists. `readiness.read` ages receipts
    # against `now`, so on a repository that has declared its boxes the page becomes a
    # function of wall-clock time and the byte comparison will red the gate when a receipt
    # crosses its window with nothing in the tree having changed. It cannot fire here — there
    # is no declaration and all eight boxes read INCOMPLETE — and the first consumer to
    # declare one will meet it. Render the age bucket rather than the verdict when that day
    # comes, or exclude the boxes from the digest and say why.
    state = readiness.read(root, now=now)
    seen = {box.id: box for box in state.boxes}
    rows = []
    for box in readiness.BOXES:
        found = seen.get(box.id)
        rows.append(
            (
                box.label,
                found.outcome if found else "INCOMPLETE",
                found.code if found else state.code,
            )
        )
    return state.result.outcome, state.code, rows


def read(root: Path, *, now: datetime | None = None) -> Tree:
    """Every fact the page shows, and nothing that is not already in the tree."""

    guards, telemetry = _hook_classes(root)
    try:
        names = set(contract.tracked(root))
    except (OSError, ValueError, subprocess.SubprocessError):
        names = set()
    if not names and (root / "specs").is_dir():
        # Refuse rather than render nothing. With an empty index every collector comes back
        # empty, `staleness` compares an empty page to the committed one and reds — which is
        # correct — and the operator's next move after a red gate is `report intent --html`,
        # which would then overwrite a correct page with an empty one. The check fails closed
        # and the write used to fail open.
        raise Unreadable("git listed no files here, so this would render a page about nothing")
    # One call, and the denominator is the two lengths of it. There was a `considered()`
    # beside `collect` that walked the tree a second time to count, which is how a
    # section's "22 of 28" comes to be measured over a different tree than its rows.
    waiting, unshown = blocked_ledger.collect(root)
    tests_lines, product_lines = _measured(root)
    verdict, code, boxes = _readiness(root, now or datetime.now(UTC))
    intent_raw = _text(root / ".ai" / "intent.md")
    try:
        intent = json.loads(intent_raw) if intent_raw else {}
    except json.JSONDecodeError:
        intent = {}
    return Tree(
        specs=_specs(root, names),
        decisions=_decisions(root, names),
        intent=intent,
        skills=sorted(
            (found.parent.name, len(_text(found).splitlines()))
            for found in (root / ".agents" / "skills").glob("*/SKILL.md")
            if found.relative_to(root).as_posix() in names
        ),
        guards=guards,
        telemetry=telemetry,
        verbs=_verbs(root),
        src_lines=product_lines,
        test_lines=tests_lines,
        ratio_max=contract.TEST_RATIO_MAX,
        boxes=boxes,
        readiness_code=code,
        readiness_outcome=verdict,
        blocked=tuple(waiting),
        considered=len(waiting) + len(unshown),
    )


# Nothing. It held `head`, which the page printed and the digest refused to cover so that a
# commit changing nothing visible would not red the gate — and that gap is precisely what
# stopped `staleness` comparing the page itself. The stamp went instead of the exclusion:
# provenance is the digest, and when the page was written is what `git log` is for.
NOT_HASHED: tuple[str, ...] = ()


def digested(tree: Tree) -> dict:
    """The payload the digest is taken over. Exposed so a test can ask what it covers
    rather than re-deriving the answer the code already knows."""

    return {name: value for name, value in asdict(tree).items() if name not in NOT_HASHED}


def digest(tree: Tree) -> str:
    """One hash over every field of the tree the page was built from.

    Derived from the dataclass rather than a hand-written list of keys, so a field added to
    `Tree` and rendered on the page cannot escape the hash — which it did once, when three
    headline numbers were printed and not covered, and the gate reported fresh over them.

    `head` is the sole exclusion: a commit that changes nothing the page shows must not make
    the page stale, or the check becomes noise and somebody turns it off.
    """

    body = json.dumps(digested(tree), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def staleness(root: Path, *, now: datetime | None = None) -> tuple[bool, str]:
    """(fresh, reason). Fresh means the page on disk is the page this tree renders.

    The first version compared a digest of the inputs to an attribute in the file, and never
    asked whether the file rendered them. A reviewer flipped nine readiness boxes to PASS and
    the skill count to 99, left the attribute alone, and the gate said PASS — a page claiming
    production readiness it does not have, and the one control that exists calling it fine.
    A hand edit is the unlikely path; a badly resolved merge conflict in a 204-line generated
    file is the likely one.

    So the comparison is the rendered page itself. It is text rather than bytes: `_text`
    reads with universal newlines, so a checkout that stores CRLF compares equal to the
    LF this renders. The content is identical either way and nothing false gets through;
    reading bytes instead would red every Windows checkout for its line endings. That is
    only possible because the page is now a pure
    function of what the digest covers: the commit it was built at and the moment it was
    written are no longer printed, because neither could be hashed without reddening the gate
    on every commit.

    The digest attribute stays, and it is what makes a failure readable — it says which tree
    the page was built from rather than only that it differs.
    """

    page = root / PAGE
    if not page.is_file():
        return False, f"{PAGE} does not exist; run `ai-eng report intent --html`"
    on_disk = _text(page)
    tree = read(root, now=now)
    if on_disk == render(tree):
        return True, f"{PAGE} matches this tree at {digest(tree)[:12]}"
    found = re.search(rf'{DIGEST_MARK}"([0-9a-f]{{64}})"', on_disk)
    if found is None:
        return False, (
            f"{PAGE} carries no {DIGEST_MARK} attribute; it was not generated by this code"
        )
    if found.group(1) != digest(tree):
        return False, (
            f"{PAGE} was built from {found.group(1)[:12]}; this tree hashes to {digest(tree)[:12]}"
        )
    return False, (
        f"{PAGE} names this tree at {found.group(1)[:12]} and is not what it renders; "
        "something edited the page rather than the records"
    )


# --- the page -------------------------------------------------------------------------

_STATUS_TONE = {
    "shipped": "good",
    "active": "good",
    "accepted": "good",
    "draft": "warn",
    "proposed": "warn",
    "superseded": "muted",
    "rejected": "bad",
    "pass": "good",
    "incomplete": "warn",
    "fail": "bad",
    "skipped": "muted",
}

_CSS = """
:root{--bg:#f4f2eb;--surface:#fcfbf7;--surface-2:#e9e6dc;--ink:#17201d;--muted:#56625c;
--line:#cac7bc;--line-strong:#989c96;--green:#166e52;--green-strong:#0d4b38;--green-soft:#dcebe4;
--amber:#89570f;--amber-soft:#f2e5cc;--red:#913b35;--red-soft:#f1dfdc;
--blue:#315e7d;--blue-soft:#dce8ef;
--shadow:0 20px 54px rgba(22,31,27,.09);--radius:14px;--max:1180px;
--sans:"Avenir Next",Avenir,"Segoe UI",Inter,system-ui,sans-serif;
--mono:"SFMono-Regular",Consolas,"Liberation Mono",monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d1412;--surface:#151e1b;
--surface-2:#1e2a26;--ink:#eaf0ec;--muted:#a7b3ad;--line:#2d3b36;
--line-strong:#52635c;--green:#70d0aa;
--green-strong:#a6e8ce;--green-soft:#17382d;--amber:#efb869;--amber-soft:#3a2d19;--red:#f0958c;
--red-soft:#3a2422;--blue:#8bc1e3;--blue-soft:#1b3040;--shadow:0 24px 60px rgba(0,0,0,.28)}}
:root[data-theme="dark"]{--bg:#0d1412;--surface:#151e1b;--surface-2:#1e2a26;
--ink:#eaf0ec;--muted:#a7b3ad;
--line:#2d3b36;--line-strong:#52635c;--green:#70d0aa;--green-strong:#a6e8ce;--green-soft:#17382d;
--amber:#efb869;--amber-soft:#3a2d19;--red:#f0958c;--red-soft:#3a2422;
--blue:#8bc1e3;--blue-soft:#1b3040;
--shadow:0 24px 60px rgba(0,0,0,.28)}
*{box-sizing:border-box}
body{margin:0;min-width:320px;background:var(--bg);color:var(--ink);font-family:var(--sans);
font-size:16.5px;line-height:1.62;-webkit-font-smoothing:antialiased}
a{color:var(--green-strong);text-underline-offset:3px}
code,.mono{font-family:var(--mono);font-size:.88em}
code{background:var(--surface-2);border-radius:5px;padding:.1em .34em}
.wrap{width:min(100% - 40px,var(--max));margin:0 auto}
header.hero{border-bottom:1px solid var(--line);padding:52px 0 34px;margin-bottom:34px}
h1{font-size:clamp(30px,4.4vw,46px);line-height:1.12;margin:0 0 12px;letter-spacing:-.02em}
.lead{font-size:1.12em;color:var(--muted);max-width:70ch;margin:0}
.stamp{margin-top:20px;font-family:var(--mono);font-size:.8em;color:var(--muted);
display:flex;flex-wrap:wrap;gap:6px 20px}
section{margin:0 0 46px;scroll-margin-top:20px}
h2{font-size:1.42em;margin:0 0 6px;letter-spacing:-.01em}
h2+p.note{margin:0 0 18px;color:var(--muted);max-width:76ch}
h3{font-size:1.02em;margin:26px 0 8px;text-transform:uppercase;
letter-spacing:.07em;color:var(--muted)}
.cards{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(168px,1fr))}
.card{border:1px solid var(--line);border-radius:var(--radius);
background:var(--surface);padding:16px 18px}
.card .n{font-size:1.85em;font-weight:600;line-height:1.1;letter-spacing:-.02em;display:block}
.card .k{font-size:.82em;color:var(--muted);display:block;margin-top:3px}
.card .s{font-size:.78em;color:var(--muted);display:block;margin-top:8px;font-family:var(--mono)}
.scroll{overflow-x:auto;border:1px solid var(--line);
border-radius:var(--radius);background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.9em;min-width:640px}
th,td{text-align:left;padding:9px 14px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.76em;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
background:var(--surface-2);position:sticky;top:0}
tbody tr:last-child td{border-bottom:0}
td.num,th.num{font-family:var(--mono);white-space:nowrap}
.tag{display:inline-block;border-radius:999px;padding:1px 9px;font-size:.76em;font-weight:600;
white-space:nowrap;border:1px solid transparent}
.tag.good{background:var(--green-soft);color:var(--green);border-color:var(--green)}
.tag.warn{background:var(--amber-soft);color:var(--amber);border-color:var(--amber)}
.tag.bad{background:var(--red-soft);color:var(--red);border-color:var(--red)}
.tag.muted{background:var(--surface-2);color:var(--muted);border-color:var(--line-strong)}
.bar{height:5px;border-radius:3px;background:var(--surface-2);
overflow:hidden;min-width:74px;margin-top:5px}
.bar i{display:block;height:100%;background:var(--green)}
ul.plain{margin:0;padding-left:1.15em}
ul.plain li{margin:0 0 6px}
.panel{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);
padding:18px 20px;box-shadow:var(--shadow)}
.panel.warn{border-color:var(--amber);background:var(--amber-soft)}
.split{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
figure{margin:0}
svg{max-width:100%;height:auto;display:block}
footer{border-top:1px solid var(--line);margin-top:20px;padding:26px 0 60px;
color:var(--muted);font-size:.88em}
@media print{body{font-size:11pt}.scroll{overflow:visible}th{position:static}}
"""

_FLOW = [
    ("idea", "una petición"),
    ("research", "/ai-research"),
    ("spec", "/ai-spec"),
    ("challenge", "/ai-challenge"),
    ("council", "/ai-council"),
    ("decide", "ai-eng decide"),
    ("plan", "/ai-plan"),
    ("build", "/ai-build"),
    ("review", "/ai-review"),
    ("verify", "/ai-verify"),
    ("security", "/ai-security"),
    ("audit", "ai-eng audit"),
    ("ship", "/ai-ship"),
]


def _flow_svg(present: dict[str, bool]) -> str:
    """The lifecycle, with a filled box for a stage that has a home and a dashed one for a
    stage that is still a conversation."""

    box_w, box_h, gap, pad = 148, 56, 16, 10
    per_row = 5
    rows = (len(_FLOW) + per_row - 1) // per_row
    width = per_row * box_w + (per_row - 1) * gap + pad * 2
    height = rows * (box_h + 34) + pad * 2
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Ciclo de vida: {", ".join(name for name, _ in _FLOW)}">'
    ]
    for index, (name, home) in enumerate(_FLOW):
        row, col = divmod(index, per_row)
        x = pad + col * (box_w + gap)
        y = pad + row * (box_h + 34)
        live = present.get(name, False)
        fill = "var(--green-soft)" if live else "var(--surface-2)"
        stroke = "var(--green)" if live else "var(--line-strong)"
        dash = "" if live else ' stroke-dasharray="5 4"'
        parts.append(
            f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="10" fill="{fill}" '
            f'stroke="{stroke}"{dash}/>'
            f'<text x="{x + box_w / 2}" y="{y + 23}" text-anchor="middle" fill="var(--ink)" '
            f'font-size="14" font-weight="600" font-family="system-ui">{html.escape(name)}</text>'
            f'<text x="{x + box_w / 2}" y="{y + 41}" text-anchor="middle" fill="var(--muted)" '
            f'font-size="11" font-family="monospace">{html.escape(home)}</text>'
        )
        if index + 1 < len(_FLOW) and col + 1 < per_row:
            mid = y + box_h / 2
            parts.append(
                f'<path d="M{x + box_w + 2} {mid} L{x + box_w + gap - 3} {mid}" '
                f'stroke="var(--line-strong)" stroke-width="1.5" marker-end="url(#a)"/>'
            )
    parts.append(
        '<defs><marker id="a" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" '
        'orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="var(--line-strong)"/></marker></defs></svg>'
    )
    return "".join(parts)


def _tag(status: str) -> str:
    tone = _STATUS_TONE.get(status.lower().split()[0] if status else "", "muted")
    return f'<span class="tag {tone}">{html.escape(status or "—")}</span>'


_KIND = {
    "halt": ("una parada", "bad"),
    "draft": ("una spec sin aprobar", "warn"),
    "verdict": ("un requisito inalcanzable", "muted"),
}


def _waiting(rows: tuple[blocked_ledger.Row, ...], considered: int) -> str:
    """The section a person opens this page for.

    The two numbers are the collector's rather than recounted from the rows below, so a
    renderer that silently drops one is caught by the count disagreeing with the table. And
    the sentence beside them says what the difference is: a filter that hides itself is the
    thing this section was built to remove, arriving one level up.

    Nothing waiting renders a sentence, not an empty table. A table with a header and no body
    reads as broken, and the answer to "what is waiting for me" being "nothing" is a sentence.
    """

    if not rows:
        # Two sentences, because "nothing is waiting" and "nothing that was looked at said
        # enough" are different facts and only one of them is good news. The first version
        # printed the first over the second, so a tree where every candidate was refused —
        # several of which really do wait on a person — read as clear.
        if not considered:
            return '  <p class="note">Nada espera a una persona ahora mismo.</p>'
        one = "candidato" if considered == 1 else "candidatos"
        return (
            f'  <p class="note">Se miraron {considered} {one} y ninguno dice las cuatro '
            "cosas, así que no se pinta ninguno. Eso no quiere decir que no haya nada "
            "esperando: quiere decir que nada dice qué hacer.</p>"
        )
    body = ""
    for row in rows:
        # `.get` with the kind itself as the label. A kind this renderer has not met yet is
        # printed as it is rather than raising: the page's job is to show what is waiting, and
        # refusing a row because its label is unknown would hide the row.
        label, tone = _KIND.get(row.kind, (row.kind, "muted"))
        body += (
            "<tr>"
            f'<td><span class="tag {tone}">{html.escape(label)}</span></td>'
            # The id beside what is waiting. Three requirement rows on this tree phrase
            # themselves identically, so without it the table shows what reads as one item
            # three times and the reader cannot act on them separately.
            f"<td>{html.escape(row.what)}<br>"
            f'<span class="mono" style="font-size:.78em;color:var(--muted)">'
            f"{html.escape(row.id)}</span></td>"
            f'<td class="num">{html.escape(row.since)}</td>'
            f"<td>{html.escape(row.why)}</td>"
            f"<td><code>{html.escape(row.action)}</code></td>"
            "</tr>"
        )
    # The clause states the invariant the collector actually enforces, which took three tries.
    # It said the others "esperan al build: son borradores sin plan" — the commonest reason
    # and not the only one. Then it said they "no nombran un literal que puedas copiar" — the
    # fourth field, when `_rows` drops on any of the four: a draft with a plan and no `date`
    # in its frontmatter has a perfect action and no `since`, and the page called it actionless.
    #
    # Both were the same mistake and it is the one this section exists to stop: a true number
    # with a false reason. Five times now, by the count kept in `blocked.py` — twice inside
    # the section written to prevent it.
    return f"""  <p class="note"><b>{len(rows)} de {considered}</b> · los otros
  {considered - len(rows)} no dicen las cuatro cosas — qué espera, desde cuándo, por qué y
  qué hacer — así que no se pintan. Casi siempre son borradores sin plan, que esperan al
  build y no a ti; pero no siempre, y por eso el total está aquí y no sólo la tabla.</p>
  <div class="scroll"><table>
    <thead><tr><th>qué es</th><th>qué espera</th><th class="num">desde</th><th>por qué paró</th>
    <th>qué lo desbloquea</th></tr></thead>
    <tbody>{body}</tbody>
  </table></div>"""


def _card(number: object, key: str, sub: str = "") -> str:
    tail = f'<span class="s">{html.escape(sub)}</span>' if sub else ""
    return (
        f'<div class="card"><span class="n">{html.escape(str(number))}</span>'
        f'<span class="k">{html.escape(key)}</span>{tail}</div>'
    )


def render(tree: Tree, *, now: datetime | None = None) -> str:
    """The page. Every number in it came out of `read`; none of it is written by hand."""

    counts: dict[str, int] = {}
    for row in tree.specs:
        counts[row.status] = counts.get(row.status, 0) + 1
    # What the tree actually carries, over the whole population the label names. This card
    # printed `18/18` at 100% for months: it counted `- [x]` list checkboxes, which exactly
    # two of sixteen plans use, so the other fourteen left the numerator AND the denominator
    # in silence and a true number read as a finished project. The small print said "in 2 of
    # 14 plans" underneath, which nobody reads before the headline.
    #
    # A percentage is only honest when its denominator is the whole population its label
    # names, and the "of how many" belongs inside the number rather than under it.
    with_check = sum(s.checks for s in tree.specs)
    numbered = sum(s.tasks for s in tree.specs)
    plans_with_tasks = sum(1 for s in tree.specs if s.tasks)
    plans_total = sum(1 for s in tree.specs if s.has_plan)
    solution = tree.intent.get("solution_intent", {})
    lifecycle = tree.intent.get("lifecycle", {})
    identity = tree.intent.get("identity", {})
    skill_names = {name for name, _ in tree.skills}
    present = {
        "idea": True,
        "research": "ai-research" in skill_names,
        "spec": "ai-spec" in skill_names,
        "challenge": "ai-challenge" in skill_names,
        "council": "ai-council" in skill_names,
        "decide": "decide" in tree.verbs,
        "plan": "ai-plan" in skill_names,
        "build": "ai-build" in skill_names,
        "review": "ai-review" in skill_names,
        # The skill, not a verb. There is no `verify` verb and there never was — the ten
        # are frozen — so this box read dashed while the thirteenth skill sat on disk.
        "verify": "ai-verify" in skill_names,
        "security": "ai-security" in skill_names,
        "audit": "audit" in tree.verbs,
        "ship": "ai-ship" in skill_names,
    }

    rows = []
    for row in tree.specs:
        progress = ""
        if row.total:
            pct = round(100 * row.done / row.total)
            progress = f'{row.done}/{row.total}<div class="bar"><i style="width:{pct}%"></i></div>'
        elif row.checks:
            progress = f'<span class="tag good">{row.checks} tareas con check</span>'
        elif row.has_plan:
            # Not a formatting preference. A plan whose tasks a script cannot enumerate is a
            # plan no envelope can be extracted from, which is why the executor has to read
            # all of it every time.
            progress = '<span class="tag warn">plan sin tareas legibles por máquina</span>'
        else:
            progress = '<span class="tag muted">sin plan</span>'
        supersedes = f"sustituye {html.escape(row.supersedes)}" if row.supersedes else ""
        rows.append(
            "<tr>"
            f'<td class="num">{html.escape(row.ident)}</td>'
            f"<td>{html.escape(row.title)}<br>"
            f'<span class="mono" style="color:var(--muted)">'
            f"specs/{html.escape(row.slug)}/</span></td>"
            f"<td>{_tag(row.status)}"
            + (
                f'<br><span class="mono" style="font-size:.78em;'
                f'color:var(--muted)">{supersedes}</span>'
                if supersedes
                else ""
            )
            + f'</td><td class="num">{html.escape(row.date)}</td>'
            f'<td class="num">{progress}</td>'
            f'<td class="num">{row.bytes_spec // 1024} KB'
            + (f" + {row.bytes_plan // 1024} KB" if row.bytes_plan else "")
            + "</td></tr>"
        )

    decision_rows = "".join(
        f'<tr><td class="num">{html.escape(d.number)}</td>'
        f'<td>{html.escape(d.title)}<br><span class="mono" style="color:var(--muted)">'
        f"{html.escape(d.path)}</span></td>"
        f"<td>{_tag(d.status)}</td></tr>"
        for d in tree.decisions
    )

    def bullets(key: str) -> str:
        items = solution.get(key, []) or ["—"]
        return "".join(f"<li>{html.escape(str(item))}</li>" for item in items)

    verb_rows = "".join(
        f'<tr><td class="num">ai-eng {html.escape(verb)}</td><td>{html.escape(text)}</td></tr>'
        for verb, text in sorted(tree.verbs.items())
    )
    skill_rows = "".join(
        f'<tr><td class="num">/{html.escape(name)}</td>'
        f'<td class="num">{lines} líneas</td>'
        f"<td>{'' if lines <= 80 else _tag('sobre el techo de 80')}</td></tr>"
        for name, lines in tree.skills
    )
    missing = [name for name, live in present.items() if not live]
    box_rows = "".join(
        f"<tr><td>{html.escape(label)}</td><td>{_tag(verdict)}</td>"
        f'<td class="num">{html.escape(code or "—")}</td></tr>'
        for label, verdict, code in tree.boxes
    )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="description" content="Solution Intent de ai-engineering: qué es, en qué
estado está cada especificación y qué lo gobierna.">
<title>ai-engineering | Solution Intent</title>
<style>{_CSS}</style>
</head>
<body {DIGEST_MARK}"{digest(tree)}">
<div class="wrap">
<header class="hero">
  <h1>{html.escape(identity.get("title", "Solution Intent"))}</h1>
  <p class="lead">Esta página es el estado del proyecto para una persona: qué existe, qué está
  a medias, qué lo decide y qué todavía no tiene prueba. La genera un comando a partir de los
  ficheros del repositorio, así que no puede envejecer sin que el gate lo diga.</p>
  <div class="stamp">
    <span>estado del Intent: {html.escape(lifecycle.get("status", "desconocido"))}</span>
    <span>{DIGEST_MARK[5:-1]} {digest(tree)[:16]}…</span>
    <span>sin fecha ni HEAD: lo que no se puede firmar no se imprime</span>
  </div>
</header>

<section id="resumen">
  <h2>De un vistazo</h2>
  <p class="note">Cada número sale de un fichero del árbol. Ninguno está escrito a mano.</p>
  <div class="cards">
    {
        _card(
            len(tree.specs),
            "especificaciones",
            " · ".join(f"{n} {k}" for k, n in sorted(counts.items())),
        )
    }
    {
        _card(
            f"{with_check}/{numbered}",
            "tareas con un comando que las decide",
            f"en {plans_with_tasks} de {plans_total} planes · "
            f"los otros {plans_total - plans_with_tasks} no llevan tareas que un script "
            f"pueda enumerar, y no cuentan en ninguno de los dos números",
        )
    }
    {_card(len(tree.decisions), "decisiones registradas", "docs/adr/")}
    {_card(len(tree.skills), "skills", f"techo de {80} líneas cada una")}
    {_card(len(tree.guards), "guards que fallan cerrados", f"+{len(tree.telemetry)} de telemetría")}
    {_card(len(tree.verbs), "verbos de CLI", "src/ai_engineering/cli.py")}
    {
        _card(
            f"{tree.test_lines / max(tree.src_lines, 1):.2f}:1",
            "prueba frente a producto",
            f"máximo {tree.ratio_max}:1 · {tree.test_lines:,} / {tree.src_lines:,}".replace(
                ",", "."
            ),
        )
    }
    {
        _card(
            f"{sum(1 for _, verdict, _ in tree.boxes if verdict == 'PASS')}/8",
            "cajas de producción probadas",
            html.escape(tree.readiness_code or "sin código"),
        )
    }
  </div>
</section>

<section id="bloqueos">
  <h2>Qué te está esperando</h2>
{_waiting(tree.blocked, tree.considered)}
</section>

<section id="ciclo">
  <h2>El ciclo de vida, y dónde vive cada paso</h2>
  <p class="note">Caja continua: el paso tiene una skill o un verbo que lo ejecuta. Caja
  discontinua: todavía es una conversación.{
        " Sin huecos." if not missing else " Sin casa: " + html.escape(", ".join(missing)) + "."
    }</p>
  <figure class="panel">{_flow_svg(present)}</figure>
</section>

<section id="intent">
  <h2>El Solution Intent que gobierna</h2>
  <p class="note">Copiado literalmente de <code>.ai/intent.md</code>. Es el documento del
  propietario del repositorio; nada de esta página puede contradecirlo.</p>
  <div class="split">
    <div class="panel"><h3>Restricciones fijas</h3>
      <ul class="plain">{bullets("fixed_constraints")}</ul></div>
    <div class="panel"><h3>Resultados buscados</h3>
      <ul class="plain">{bullets("intended_outcomes")}</ul></div>
    <div class="panel warn"><h3>Hechos actuales</h3>
      <ul class="plain">{bullets("current_facts")}</ul></div>
    <div class="panel"><h3>Variables</h3>
      <ul class="plain">{bullets("variables")}</ul></div>
  </div>
</section>

<section id="specs">
  <h2>Dónde está cada especificación</h2>
  <p class="note">Sólo las specs que están en git: una sin commitear no se publica en un
  documento que sí lo está. El estado sale del frontmatter de cada <code>spec.md</code>. El progreso
  cuenta las casillas de su <code>plan.md</code>; una casilla no es una prueba, sólo dice qué
  se marcó.</p>
  <div class="scroll"><table>
    <thead><tr><th class="num">id</th><th>título</th><th>estado</th><th class="num">fecha</th>
    <th class="num">tareas</th><th class="num">tamaño</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>

<section id="decisiones">
  <h2>Decisiones que atan al futuro</h2>
  <p class="note">Un ADR es inmutable: se sustituye, no se reescribe.</p>
  <div class="scroll"><table>
    <thead><tr><th class="num">nº</th><th>decisión</th><th>estado</th></tr></thead>
    <tbody>{decision_rows}</tbody>
  </table></div>
</section>

<section id="produccion">
  <h2>¿Está lista para producción?</h2>
  <p class="note">Las ocho cajas que <code>src/ai_engineering/readiness.py</code> verifica
  contra <code>.ai/readiness.json</code>. Veredicto agregado:
  {_tag(tree.readiness_outcome)} <code>{html.escape(tree.readiness_code or "—")}</code>.
  Ninguna caja se marca sin un recibo; una declaración ausente es INCOMPLETE, no un hueco.</p>
  <div class="scroll"><table style="min-width:0">
    <thead><tr><th>caja</th><th>resultado</th><th>código</th></tr></thead>
    <tbody>{box_rows}</tbody>
  </table></div>
</section>

<section id="superficie">
  <h2>Lo que el producto expone</h2>
  <div class="split">
    <div>
      <h3>Verbos</h3>
      <div class="scroll"><table style="min-width:0">
        <thead><tr><th class="num">verbo</th><th>qué hace</th></tr></thead>
        <tbody>{verb_rows}</tbody>
      </table></div>
    </div>
    <div>
      <h3>Skills</h3>
      <div class="scroll"><table style="min-width:0">
        <thead><tr><th class="num">skill</th><th class="num">tamaño</th><th></th></tr></thead>
        <tbody>{skill_rows}</tbody>
      </table></div>
    </div>
  </div>
  <h3>Guards</h3>
  <p>Fallan cerrados: <code>{html.escape(", ".join(tree.guards) or "ninguno")}</code>.
  Telemetría, que observa y nunca decide:
  <code>{html.escape(", ".join(tree.telemetry) or "ninguna")}</code>.</p>
</section>

<footer class="wrap">
  <p>Generada por <code>src/ai_engineering/solution_intent.py</code> a partir de
  <code>specs/</code>, <code>docs/adr/</code>, <code>.ai/intent.md</code>, <code>hooks/</code>
  y <code>src/ai_engineering/cli.py</code>. Para regenerarla, ejecuta el comando que la
  escribe; para saber si está caducada, <code>solution_intent.staleness()</code> compara el
  digest de arriba con el árbol actual.</p>
  <p>Un estado en esta página es lo que el fichero dice, no una prueba de que algo funcione.
  La prueba es un recibo de un check que se ejecutó.</p>
</footer>
</div>
</body>
</html>
"""


def write(root: Path, *, now: datetime | None = None) -> Path:
    page = root / PAGE
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(render(read(root, now=now), now=now), encoding="utf-8")
    return page


def main(argv: list[str]) -> int:
    """`--check` reports and writes nothing; without it, regenerate.

    Two modes and not one, because the gate must not repair what it is checking. A gate that
    rewrites the page and then finds it fresh has asserted nothing at all, which is the shape
    this whole repository is named for."""

    here = Path(".")
    try:
        if "--check" in argv:
            fresh, why = staleness(here)
            print(f"  {'PASS' if fresh else 'FAIL'}  {why}")
            if not fresh:
                print("  Next action: run `ai-eng report intent --html`, then read the diff.")
            return 0 if fresh else 1
        written = write(here)
        fresh, why = staleness(here)
        print(f"  RAN intent-page={written}")
        return 0 if fresh else 1
    except (Unreadable, blocked_ledger.Unreadable) as refused:
        # The exit code was already 1, so the gate was already red. What was missing is the
        # shape: a named refusal reaching the operator as a traceback full of absolute paths
        # reads as a crash, and the first thing anybody does with a crash is re-run it.
        print(f"  FAIL  {refused}")
        print("  Next action: fix that file, or move it aside and re-run.")
        return 1


# No coverage pragma here. Every other entry point in this repository carries one and
# they all live under `tests/`, which the semantic lane does not scan; `src/` is held to
# rule 3, and the lane found this the moment it shipped. Three uncovered lines against
# eight points of slack under the floor is cheaper than a suppression comment.
if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
