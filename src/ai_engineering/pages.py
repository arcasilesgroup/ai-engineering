"""The renderer behind `ai-eng report view|recap`: fenced `visual` blocks to one page.

Specification 046 puts the review surfaces of the cycle — spec, plan, recap — into
self-contained HTML, and grill round 1 decided the shape of this module: the skills author
content, this file owns the *form*, and nothing authored here may execute. The output is
one HTML document with no `<script>`, no external URL and no network; it opens from disk
in any browser and it renders the same in five years, because it depends on no toolchain
that can move under it.

The grammar is a fenced block inside ordinary Markdown::

    ```visual
    {"block": "diagram", "title": "…", "steps": […]}
    ```

A plain reader sees a fenced JSON note; this module sees a surface. An unknown block name
is never dropped: it lands in a visible warning section on the page, because a renderer
that quietly loses a block is the silent-coercion bug this repository exists to delete.
"""

from __future__ import annotations

import html
import json
import re
from importlib import resources
from typing import Any

from . import contract, spec

# The block vocabulary, one renderer each. Harvested from the MIT block taxonomy of
# Builder.io's visual-plan/visual-recap skills (attribution in policy/visual-pages.md);
# the budgets are `contract`'s, never numbers repeated here.
KNOWN_BLOCKS = frozenset(
    {
        "diagram",
        "file-tree",
        "decision-table",
        "open-questions",
        "checklist",
        "wireframe-before-after",
        "diff",
        "narrative",
    }
)


class PageError(ValueError):
    """A page that cannot be rendered honestly. Never a partial page, never a warning."""


def _is_visual(info: str) -> bool:
    return info.split()[0] == "visual" if info.split() else False


def visual_blocks(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """The `visual` blocks one document carries, and the warnings their flaws earned.

    The fence walk is `spec.fence_records` — the same CommonMark-aware reader the plan
    parser uses, so a `visual` example shown inside an ordinary fence stays content and
    an unclosed fence runs to the end instead of swallowing a closing delimiter. A
    malformed JSON body is a warning, not a crash — one bad block must not swallow the
    page — and an unknown block name keeps its raw payload for the warning section, so
    the reader sees what was dropped rather than trusting that nothing was.
    """

    blocks: list[dict[str, Any]] = []
    warnings: list[str] = []
    for record in spec.fence_records(text):
        if not _is_visual(record.info):
            continue
        body = text[record.body : record.end]
        # Drop the closing fence line, if the record carries one.
        closing = re.search(r"\n {0,3}(`{3,}|~{3,})[ \t]*$", body)
        if closing:
            body = body[: closing.start()]
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as bad:
            warnings.append(f"a `visual` block is not valid JSON ({bad}): rendering nothing")
            continue
        if not isinstance(payload, dict) or not isinstance(payload.get("block"), str):
            warnings.append('a `visual` block carries no `"block"` name: rendering nothing')
            continue
        if payload["block"] not in KNOWN_BLOCKS:
            warnings.append(
                f"unknown visual block `{payload['block']}`: kept visible, rendered nowhere"
            )
            blocks.append({"block": "!unknown", "name": payload["block"], "raw": payload})
        else:
            blocks.append(payload)
    return blocks, warnings


def strip_visual_fences(text: str) -> str:
    """The document with its `visual` fences removed, so prose renders without them."""

    out, cut = [], 0
    for record in spec.fence_records(text):
        if not _is_visual(record.info):
            continue
        out.append(text[cut : record.start])
        cut = record.end
    out.append(text[cut:])
    return "".join(out)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


_INLINE = re.compile(r"`([^`]+)`|\*\*([^*]+)\*\*|\*([^*\n]+)\*")


def _span(line: str) -> str:
    """One line to markup: escaped first, then the four inline shapes, nothing else."""

    result, at = [], 0
    for hit in _INLINE.finditer(line):
        result.append(esc(line[at : hit.start()]))
        code, strong, em = hit.groups()
        if code is not None:
            result.append(f"<code>{esc(code)}</code>")
        elif strong is not None:
            result.append(f"<strong>{esc(strong)}</strong>")
        else:
            result.append(f"<em>{esc(em)}</em>")
        at = hit.end()
    result.append(esc(line[at:]))
    return "".join(result)


def _render_markdown(text: str) -> str:
    """A deliberate markdown subset: paragraphs, headings, lists, quotes, inline marks.

    Not a dependency. The narrative a skill writes is a few paragraphs and a list; a
    general parser would be a second source of truth about what renders, and this one is
    forty lines a reviewer can read whole. Everything escapes before any markup is
    assembled, so no authored string reaches the page as markup except the shapes below.
    """

    out: list[str] = []
    list_open = False

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            out.append("</ul>")
            list_open = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            close_list()
            continue
        if hit := re.match(r"^(#{1,4}) (.+)$", line):
            close_list()
            level = len(hit.group(1)) + 1
            out.append(f"<h{level}>{_span(hit.group(2))}</h{level}>")
        elif hit := re.match(r"^[-*] (.+)$", line):
            if not list_open:
                out.append("<ul>")
                list_open = True
            out.append(f"<li>{_span(hit.group(1))}</li>")
        elif hit := re.match(r"^> (.+)$", line):
            close_list()
            out.append(f"<blockquote><p>{_span(hit.group(1))}</p></blockquote>")
        else:
            close_list()
            out.append(f"<p>{_span(line)}</p>")
    close_list()
    return "\n".join(out)


def sanitize_fragment(fragment: str) -> str:
    """Wireframe HTML, stripped of everything that could execute or phone home.

    A wireframe is the one block whose payload is markup — a mock screen is markup — so it
    is not escaped but filtered: no script, style sheet, frame, object, event handler,
    external reference or `javascript:` URL. What survives is shape and inline style,
    which is all a mockup needs and all a reviewer's browser should get from a file on
    disk.
    """

    fragment = re.sub(
        r"<(script|style|link|meta|iframe|object|embed)\b.*?</\1>",
        "",
        fragment,
        flags=re.S | re.I,
    )
    fragment = re.sub(
        r"<(script|style|link|meta|iframe|object|embed|base|form)\b[^>]*/?>",
        "",
        fragment,
        flags=re.I,
    )
    fragment = re.sub(r"\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", fragment, flags=re.I)
    fragment = re.sub(
        r"\s(src|href|srcset|formaction|action|data|background)\s*="
        r"(\"[^\"]*\"|'[^']*'|[^\s>]+)",
        "",
        fragment,
        flags=re.I,
    )
    return re.sub(r"(?<![\w-])(javascript|vbscript|data)\s*:", "", fragment, flags=re.I)


def _title_of(data: dict[str, Any]) -> str:
    return f"<h2>{esc(data['title'])}</h2>" if data.get("title") else ""


def _block_diagram(data: dict[str, Any]) -> str:
    steps = data.get("steps") or []
    if not steps:
        raise PageError("a diagram block carries no steps")
    rows = []
    for at, step in enumerate(steps):
        label = esc(step.get("label", "")) if isinstance(step, dict) else esc(step)
        note = esc(step.get("note", "")) if isinstance(step, dict) else ""
        arrow = "" if at == len(steps) - 1 else "<div class='sub' style='text-align:center'>↓</div>"
        rows.append(
            "<div class='callout ok' style='border-left-color:var(--accent)'>"
            f"<strong>{at + 1}. {label}</strong>"
            + (f"<div class='sub'>{note}</div>" if note else "")
            + "</div>"
            + arrow
        )
    return _title_of(data) + "".join(rows)


def _block_file_tree(data: dict[str, Any]) -> str:
    def walk(entries: list[dict[str, Any]]) -> str:
        rows = []
        for entry in entries:
            flag = (entry.get("change") or " ")[0].upper()
            badge = (
                f"<span class='flag f-{esc(flag)}'>{esc(flag)}</span>" if flag in "AMRDCT" else ""
            )
            rows.append(f"<li>{badge}{esc(entry.get('path', ''))}</li>")
            children = entry.get("children") or []
            if children:
                rows.append(walk(children))
        return "<ul class='tree'>" + "".join(rows) + "</ul>"

    return _title_of(data) + walk(data.get("entries") or [])


def _block_decision_table(data: dict[str, Any]) -> str:
    rows = data.get("rows") or []
    head = data.get("headers") or (
        list(rows[0].keys()) if rows and isinstance(rows[0], dict) else []
    )
    out = [
        "<table><thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in head) + "</tr></thead><tbody>"
    ]
    for row in rows:
        cells = [row.get(h, "") for h in head] if isinstance(row, dict) else list(row)
        out.append(
            "<tr>" + "".join(f"<td>{_render_markdown(str(c))}</td>" for c in cells) + "</tr>"
        )
    out.append("</tbody></table>")
    return _title_of(data) + "".join(out)


def _block_open_questions(data: dict[str, Any]) -> str:
    items = []
    for question in data.get("questions") or []:
        options = "".join(
            "<li>"
            + esc(o.get("label", o) if isinstance(o, dict) else o)
            + (
                f" <span class='sub'>({esc(o['detail'])})</span>"
                if isinstance(o, dict) and o.get("detail")
                else ""
            )
            + "</li>"
            for o in question.get("options") or []
        )
        rec = (
            f"<p class='sub'>Recommended: <strong>{esc(question['recommendation'])}</strong></p>"
            if question.get("recommendation")
            else ""
        )
        items.append(
            "<div class='callout warn'>"
            f"<h3 style='margin-top:0'>{esc(question.get('title', '?'))}</h3>"
            + (f"<ul>{options}</ul>" if options else "")
            + rec
            + "</div>"
        )
    title = _title_of(data) or "<h2>Open questions</h2>"
    return title + "".join(items)


def _block_checklist(data: dict[str, Any]) -> str:
    rows = []
    for item in data.get("items") or []:
        if isinstance(item, dict):
            label, done = str(item.get("label", "")), bool(item.get("done"))
        else:
            label, done = str(item), False
        mark = "☑" if done else "☐"
        css = "done" if done else ""
        rows.append(f"<li class='{css}'>{mark} {_render_markdown(label)}</li>")
    body = "".join(rows)
    return (
        _title_of(data)
        + f"<ul class='checklist' style='list-style:none;padding-left:4px'>{body}</ul>"
    )


def _block_wireframe(data: dict[str, Any]) -> str:
    def side(name: str) -> str:
        panel = data.get(name) or {}
        body = sanitize_fragment(str(panel.get("html", "")))
        caption = f"<p class='sub'>{esc(panel['caption'])}</p>" if panel.get("caption") else ""
        return (
            f"<div><h3>{esc(name.title())}</h3>"
            + f"<div class='wireframe'><div class='wf-body'>{body}</div></div>{caption}</div>"
        )

    if data.get("before") and data.get("after"):
        return _title_of(data) + f"<div class='wf-pair'>{side('before')}{side('after')}</div>"
    return _title_of(data) + side("after" if data.get("after") else "before")


def _block_diff(data: dict[str, Any]) -> str:
    text = str(data.get("text", ""))
    if len(text.splitlines()) > contract.RECAP_EXCERPT_LINES_MAX:
        raise PageError(
            f"a diff excerpt for `{data.get('path', '?')}` carries {len(text.splitlines())} "
            f"lines, over the budget of {contract.RECAP_EXCERPT_LINES_MAX}"
        )
    lines = []
    for line in text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(f"<span class='add'>{esc(line)}</span>\n")
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(f"<span class='del'>{esc(line)}</span>\n")
        elif line.startswith("@@"):
            lines.append(f"<span class='hunk'>{esc(line)}</span>\n")
        else:
            lines.append(esc(line) + "\n")
    summary = f"<p class='sub'>{esc(data['summary'])}</p>" if data.get("summary") else ""
    path = esc(data.get("path", "diff"))
    return f"<h3><code>{path}</code></h3>{summary}<pre class='diff'>{''.join(lines)}</pre>"


def _block_narrative(data: dict[str, Any]) -> str:
    return _render_markdown(str(data.get("text", "")))


_RENDERERS = {
    "diagram": _block_diagram,
    "file-tree": _block_file_tree,
    "decision-table": _block_decision_table,
    "open-questions": _block_open_questions,
    "checklist": _block_checklist,
    "wireframe-before-after": _block_wireframe,
    "diff": _block_diff,
    "narrative": _block_narrative,
}


def render_block(data: dict[str, Any]) -> str:
    """One block to markup. An unknown block renders into the warnings, never the body."""

    if data.get("block") == "!unknown":
        return ""
    renderer = _RENDERERS.get(data.get("block", ""))
    if renderer is None:  # unreachable through visual_blocks; a direct caller gets the refusal
        raise PageError(f"no renderer is registered for block `{data.get('block')}`")
    return renderer(data)


def warnings_section(warnings: list[str]) -> str:
    if not warnings:
        return ""
    rows = "".join(f"<li>{esc(one)}</li>" for one in warnings)
    return (
        "<div class='callout bad'><strong>The page could not render everything.</strong>"
        f"<ul>{rows}</ul></div>"
    )


def render_page(
    kicker: str, title: str, sub: str, meta: str, body: str, warnings: list[str]
) -> str:
    """The template filled. The title budget is enforced here, at the one door pages pass."""

    if len(title) > contract.PAGE_TITLE_MAX:
        raise PageError(
            f"a page title carries {len(title)} chars, over the budget of {contract.PAGE_TITLE_MAX}"
        )
    template = (
        resources.files("ai_engineering")
        .joinpath("templates/page.html")
        .read_text(encoding="utf-8")
    )
    page = (
        template.replace("@@KICKER@@", esc(kicker))
        .replace("@@TITLE@@", esc(title))
        .replace("@@SUB@@", esc(sub))
        .replace("@@META@@", meta)
        .replace("@@WARNINGS@@", warnings_section(warnings))
        .replace("@@BODY@@", body)
    )
    # A diff's empty context line is one space, and a page that carries it fails the
    # repository's own whitespace gate on the way in — the record of a change cannot be
    # committed. Trailing blanks end a rendered line; nothing here needs them.
    return "\n".join(line.rstrip(" \t") for line in page.split("\n"))


def render_document(text: str, kicker: str, title: str, sub: str, meta: str) -> str:
    """A Markdown document as one page: its prose and its `visual` blocks, in order.

    Prose between blocks is not silently dropped — a review page that shows only the
    pretty parts of a plan is a page nobody should approve from — so the document renders
    whole, with the fenced blocks lifted out and their surfaces appended in place.
    """

    blocks, warnings = visual_blocks(text)
    stripped = strip_visual_fences(text)
    body = _render_markdown(stripped) + "".join(render_block(one) for one in blocks)
    return render_page(kicker, title, sub, meta, body, warnings)
