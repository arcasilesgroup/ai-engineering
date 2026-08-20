"""What an image carries besides the picture, removed before it is written.

`EP-254` asks that imagery output lose its metadata, pass a scan, and be sanitised when it
is vector. It was prose in a skill file and nothing did any of the three, and the audit
deliberately declined to close it by pinning that prose: stripping metadata is a mechanical
act, and a mechanical act written as an instruction is a control that runs when somebody
remembers.

The three formats here are the three a design capability produces, and that limit is stated
rather than hidden: PNG, JPEG and SVG. Anything else is returned unchanged and reported as
unscanned, which is not the same as clean — a format nobody taught this module about is a
format whose metadata nobody looked at.

Two halves, and both are needed. `stripped` removes what should never have travelled, and
`findings` says what is still there. Without the second, the first is a function nobody can
falsify; without the first, the second is a refusal with no cure.
"""

from __future__ import annotations

import re
import struct
import xml.etree.ElementTree as ElementTree

PNG = b"\x89PNG\r\n\x1a\n"
JPEG = b"\xff\xd8\xff"

# Chunks a PNG needs, or that describe how to render it. Everything else goes: `tEXt`,
# `zTXt` and `iTXt` are free text, `eXIf` is a camera's record of where somebody stood, and
# `tIME` is when the file was made. An allowlist rather than a blocklist, because the next
# chunk type somebody invents should not arrive by default.
PNG_KEPT = frozenset(
    (
        b"IHDR",
        b"PLTE",
        b"IDAT",
        b"IEND",
        b"tRNS",
        b"gAMA",
        b"cHRM",
        b"sRGB",
        b"iCCP",
        b"sBIT",
        b"pHYs",
        b"bKGD",
        b"hIST",
        b"acTL",
        b"fcTL",
        b"fdAT",
    )
)

# JPEG application segments. APP0 is JFIF — density and a thumbnail flag, no author and no
# location — and dropping it makes some decoders guess at the aspect ratio. APP1 is EXIF and
# XMP, which is the segment this function exists for. `COM` is a free-text comment.
JPEG_DROPPED = frozenset([0xFE, *range(0xE1, 0xF0)])

# What a vector file must not carry. An SVG is a document a browser executes, so "sanitise"
# here means the same thing it means for HTML: no script, no event handler, no reference out
# to somewhere else that a viewer will fetch.
SVG_NAMESPACE = b"http://www.w3.org/2000/svg"
SVG_SCRIPT = re.compile(r"^\{http://www\.w3\.org/2000/svg\}(script|foreignObject)$")
SVG_EVENT = re.compile(r"^on[a-z]+$", re.IGNORECASE)
SVG_REMOTE = re.compile(r"^\s*(?:https?:|//|file:|javascript:)", re.IGNORECASE)


def kind(payload: bytes) -> str:
    """Which of the three this is, by its bytes and never by its name.

    A file called `diagram.png` that is a JPEG is a file whose extension is a claim. The
    magic number is the only thing here that is not somebody's assertion.
    """

    if payload.startswith(PNG):
        return "png"
    if payload.startswith(JPEG):
        return "jpeg"
    head = payload[:512].lstrip()
    if head.startswith(b"<?xml") or head.startswith(b"<svg"):
        # The tag or the namespace. A sanitised file is re-serialised by ElementTree, and a
        # check for the literal `<svg` alone would call the output of this very module
        # unreadable — which is how a scan comes back "nothing here looked at it" for the
        # one file that was definitely looked at.
        opening = payload[:4096]
        return "svg" if b"<svg" in opening or SVG_NAMESPACE in opening else ""
    return ""


def _png_chunks(payload: bytes):
    at = len(PNG)
    while at + 8 <= len(payload):
        (length,) = struct.unpack(">I", payload[at : at + 4])
        name = payload[at + 4 : at + 8]
        end = at + 12 + length
        if length > len(payload) or end > len(payload):
            return  # a truncated file: what is left is not a chunk anybody can read
        yield name, payload[at:end]
        at = end


def _jpeg_segments(payload: bytes):
    at = 2
    while at + 4 <= len(payload):
        if payload[at] != 0xFF:
            yield None, payload[at:]  # entropy-coded data to the end, or a malformed file
            return
        marker = payload[at + 1]
        if marker == 0xDA:  # start of scan: the rest is the image itself
            yield None, payload[at:]
            return
        (length,) = struct.unpack(">H", payload[at + 2 : at + 4])
        end = at + 2 + length
        if length < 2 or end > len(payload):
            yield None, payload[at:]
            return
        yield marker, payload[at:end]
        at = end


def stripped(payload: bytes) -> bytes:
    """The same picture, without what travelled beside it.

    Unknown formats come back untouched. That is deliberate and it is why `findings` exists:
    a silent pass-through that reported success would be this module claiming to have
    cleaned something it cannot read.
    """

    which = kind(payload)
    if which == "png":
        kept = [chunk for name, chunk in _png_chunks(payload) if name in PNG_KEPT]
        return PNG + b"".join(kept) if kept else payload
    if which == "jpeg":
        kept = [
            segment
            for marker, segment in _jpeg_segments(payload)
            if marker is None or marker not in JPEG_DROPPED
        ]
        return payload[:2] + b"".join(kept) if kept else payload
    if which == "svg":
        return _sanitised_svg(payload)
    return payload


def _sanitised_svg(payload: bytes) -> bytes:
    try:
        root = ElementTree.fromstring(payload.decode("utf-8"))
    except (ElementTree.ParseError, UnicodeDecodeError):
        return payload  # unparseable: `findings` refuses it rather than this rewriting it
    _strip_element(root)
    # Or the output comes back as `ns0:svg`, which is the same document and is not the same
    # bytes: every reader that looks for the tag, including `kind` above, stops finding it.
    ElementTree.register_namespace("", SVG_NAMESPACE.decode())
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def _strip_element(element) -> None:
    for child in list(element):
        if SVG_SCRIPT.match(child.tag or ""):
            element.remove(child)
            continue
        _strip_element(child)
    for name, value in list(element.attrib.items()):
        local = name.rsplit("}", 1)[-1]
        if SVG_EVENT.match(local) or (
            local in ("href", "src") and SVG_REMOTE.match(str(value) or "")
        ):
            del element.attrib[name]


def findings(payload: bytes) -> list[str]:
    """What is still in these bytes that should not be, in words a person can act on.

    An empty list means scanned and clean. A format this module cannot read says so as a
    finding, because "nothing was found" and "nothing was looked at" are the two answers
    this repository spends its time keeping apart.
    """

    which = kind(payload)
    if which == "png":
        carried = sorted(
            {name.decode("latin-1") for name, _ in _png_chunks(payload) if name not in PNG_KEPT}
        )
        return [f"the PNG carries {one}, which is metadata and not picture" for one in carried]
    if which == "jpeg":
        carried = sorted(
            {marker for marker, _ in _jpeg_segments(payload) if marker in JPEG_DROPPED}
        )
        return [
            f"the JPEG carries segment 0x{one:02X}, which is EXIF, XMP or a comment"
            for one in carried
        ]
    if which == "svg":
        return _svg_findings(payload)
    return ["these bytes are not a PNG, a JPEG or an SVG, so nothing here scanned them"]


def _svg_findings(payload: bytes) -> list[str]:
    try:
        root = ElementTree.fromstring(payload.decode("utf-8"))
    except (ElementTree.ParseError, UnicodeDecodeError):
        return ["the SVG could not be parsed, so nothing here could scan it"]
    problems: list[str] = []
    for element in root.iter():
        if SVG_SCRIPT.match(element.tag or ""):
            problems.append(f"the SVG carries {element.tag.rsplit('}', 1)[-1]}, which executes")
        for name, value in element.attrib.items():
            local = name.rsplit("}", 1)[-1]
            if SVG_EVENT.match(local):
                problems.append(f"the SVG carries {local}, which is an event handler")
            elif local in ("href", "src") and SVG_REMOTE.match(str(value) or ""):
                problems.append(f"the SVG references {str(value)[:40]}, which a viewer fetches")
    return problems
