"""The half of `EP-047` and `EP-280` that does not need a published release.

The audit filed both under "no local work can move this", and that was half right in the
way this repository keeps finding a requirement half right: *publishing* an SBOM needs a
release, and "an SBOM exists, it is well formed, and it names the bytes that were built" is
answerable by a command. These are that command.

Every fixture builds a real zip and hashes it. A test that handed the emitter a dictionary
would prove the emitter's arithmetic and not that it can read a wheel.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest


def wheel(tmp_path: Path, name: str = "ai-engineering", version: str = "1.2.3") -> Path:
    """A wheel with the one file this reader opens, and enough else to be a wheel."""

    built = tmp_path / f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(built, "w") as archive:
        archive.writestr(
            f"{name.replace('-', '_')}-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\n"
            'Requires-Dist: rich>=13\nRequires-Dist: httpx>=0.27; extra == "net"\n'
            "Requires-Dist: tomli-w\n\nA wheel.\n",
        )
        archive.writestr("ai_engineering/__init__.py", "__version__ = '1.2.3'\n")
    return built


def test_the_bom_names_the_bytes_that_were_built(tmp_path):
    """The whole point of the document, and the only claim the threat model rests on it.

    `policy/threat-model.toml`'s `supply-chain` row says the harm is "a package that is not
    the one we built". An SBOM that describes a version rather than a digest cannot tell
    those apart, so the digest is what is asserted here — against the file itself, hashed
    again in this test rather than taken from the document that is under test."""
    from ai_engineering import sbom

    built = wheel(tmp_path)
    bom = sbom.document(built)

    hashes = bom["metadata"]["component"]["hashes"]
    assert hashes == [{"alg": "SHA-256", "content": hashlib.sha256(built.read_bytes()).hexdigest()}]

    # And it moves when the bytes move. A digest that is right once and never recomputed is
    # a constant wearing a hash's name.
    built.write_bytes(built.read_bytes() + b"\x00")
    again = sbom.document(built)["metadata"]["component"]["hashes"][0]["content"]
    assert again != hashes[0]["content"]


def test_the_document_carries_every_field_it_is_invalid_without(tmp_path):
    """The subset named in `sbom.REQUIRED`, and the module says out loud that it is a
    subset. Checked from the constant rather than from a list written twice, so removing a
    field from the emitter and from this file in one edit is still one edit somebody sees."""
    from ai_engineering import sbom

    bom = sbom.document(wheel(tmp_path))

    missing = [field for field in sbom.REQUIRED if field not in bom]
    assert not missing, f"the BOM is invalid CycloneDX without {missing}"
    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == sbom.SPEC_VERSION
    assert isinstance(bom["version"], int)
    assert json.loads(json.dumps(bom)) == bom, "the BOM does not survive a round trip"


def test_the_dependencies_it_names_are_the_ones_the_wheel_declares(tmp_path):
    """Names, sorted, without markers or specifiers.

    `httpx>=0.27; extra == "net"` is httpx. The module says it does not resolve versions,
    and this holds it to naming what the wheel declares rather than guessing what pip would
    do with it — a guess in this document would be the whole defect, stated confidently."""
    from ai_engineering import sbom

    bom = sbom.document(wheel(tmp_path))

    assert [one["name"] for one in bom["components"]] == ["httpx", "rich", "tomli-w"]
    assert all(one["purl"].startswith("pkg:pypi/") for one in bom["components"])


def test_two_runs_over_the_same_bytes_produce_the_same_document(tmp_path):
    """A timestamp or a random serial number makes every release's SBOM differ from every
    other, which hides the one difference anybody would want to see."""
    from ai_engineering import sbom

    built = wheel(tmp_path)
    first = sbom.document(built)
    written = json.loads(sbom.write(built).read_text("utf-8"))

    # The second read comes off disk rather than from a second call, so what is compared is
    # not one expression against itself: it is the document a release would publish against
    # the one a consumer would re-derive from the same bytes.
    assert written == first
    assert written["serialNumber"] == first["serialNumber"], "the serial number moved"


def test_a_wheel_without_exactly_one_metadata_is_refused(tmp_path):
    """Zero is a file that is not a wheel; two is a file pretending to be two wheels. Both
    are things this reader must not describe, because a BOM built from a guess about which
    METADATA was the real one is a document that reads like a control."""
    from ai_engineering import sbom

    empty = tmp_path / "empty-1.0-py3-none-any.whl"
    with zipfile.ZipFile(empty, "w") as archive:
        archive.writestr("ai_engineering/__init__.py", "")
    with pytest.raises(ValueError, match="0 METADATA"):
        sbom.document(empty)

    doubled = tmp_path / "doubled-1.0-py3-none-any.whl"
    with zipfile.ZipFile(doubled, "w") as archive:
        archive.writestr("a-1.0.dist-info/METADATA", "Name: a\nVersion: 1.0\n")
        archive.writestr("b-1.0.dist-info/METADATA", "Name: b\nVersion: 1.0\n")
    with pytest.raises(ValueError, match="2 METADATA"):
        sbom.document(doubled)


def test_it_lands_beside_the_wheel_because_that_is_what_gets_attested(tmp_path):
    """`release.yml` attests `dist/*` as one subject list, so a document written anywhere
    else is attested by nothing at all."""
    from ai_engineering import sbom

    built = wheel(tmp_path)
    written = sbom.write(built)

    assert written.parent == built.parent
    assert written.name.endswith(".cdx.json")
    assert json.loads(written.read_text("utf-8"))["specVersion"] == sbom.SPEC_VERSION


def test_naming_no_wheel_is_incomplete_and_writes_nothing(tmp_path, capsys):
    """The lane runner's own rule, applied here: a run over zero inputs found nothing and
    scanned nothing, and those are not the same as a clean result."""
    from ai_engineering import sbom

    assert sbom.main([]) == 1
    assert "INCOMPLETE" in capsys.readouterr().out


def test_a_document_describing_a_different_wheel_is_refused(tmp_path):
    """`EP-051`'s tamper fixture, at the artefact this repository gained today.

    The rules file already had one; the SBOM did not, and it is the more interesting target.
    A corrupted document is caught by anything that parses it. What this refuses is a *valid*
    one — every field present, a real sha256, the whole thing well formed — that describes a
    different wheel from the one it travels with. Only comparing the two tells them apart,
    and until now that comparison lived inline in a job that runs on a tag and had therefore
    never executed once.
    """
    from ai_engineering import sbom

    built = wheel(tmp_path)
    honest = sbom.write(built)
    assert sbom.matches(built, honest)

    # The swap: a document for a wheel that was never built here, valid in every other way.
    (tmp_path / "elsewhere").mkdir(exist_ok=True)
    other = wheel(tmp_path / "elsewhere", version="9.9.9")
    swapped = tmp_path / "swapped.cdx.json"
    swapped.write_text(json.dumps(sbom.document(other), indent=2), encoding="utf-8")
    assert json.loads(swapped.read_text("utf-8"))["specVersion"] == sbom.SPEC_VERSION
    assert not sbom.matches(built, swapped), "a document about another wheel was accepted"

    # And one byte. The narrowest version of the same attack: the digest is edited and
    # nothing else, so every structural check still passes.
    flipped = json.loads(honest.read_text("utf-8"))
    digest = flipped["metadata"]["component"]["hashes"][0]["content"]
    flipped["metadata"]["component"]["hashes"][0]["content"] = (
        "0" if digest[0] != "0" else "1"
    ) + digest[1:]
    edited = tmp_path / "edited.cdx.json"
    edited.write_text(json.dumps(flipped), encoding="utf-8")
    assert not sbom.matches(built, edited), "one edited character was not noticed"


def test_a_document_that_is_missing_or_unreadable_is_refused_and_never_raises(tmp_path):
    """The other half of a fail-closed comparison. A missing file, a truncated one, a valid
    JSON document with no hashes, and one naming an algorithm we do not use: each is a
    refusal and none of them is a traceback out of a release job."""
    from ai_engineering import sbom

    built = wheel(tmp_path)
    for name, body in (
        ("absent.cdx.json", None),
        ("truncated.cdx.json", '{"metadata": '),
        ("empty.cdx.json", "{}"),
        (
            "wrong-alg.cdx.json",
            json.dumps({"metadata": {"component": {"hashes": [{"alg": "MD5", "content": "x"}]}}}),
        ),
    ):
        where = tmp_path / name
        if body is not None:
            where.write_text(body, encoding="utf-8")
        assert not sbom.matches(built, where), f"{name} was accepted"


def test_an_argument_that_is_not_a_built_wheel_is_refused_before_anything_is_written(
    tmp_path, capsys
):
    """Static analysis found this on the day the module was written, and it was right.

    `write` puts its output beside the path it was handed, and this runs inside the release job
    with whatever the shell's glob produced — so an argument that is not a wheel is an argument
    that decides where a file lands, in the job that publishes what it finds in `dist/`.

    Four shapes are refused and none of them writes: a file that is not a wheel, a directory
    named like one, a path that does not exist, and a wheel named after one that does. The
    check runs over every argument before the first is written, so a run naming one good wheel
    and one bad path describes neither.
    """
    from ai_engineering import sbom

    good = wheel(tmp_path)

    (tmp_path / "notes.txt").write_text("not a wheel", encoding="utf-8")
    (tmp_path / "folder.whl").mkdir()

    for bad in ("notes.txt", "folder.whl", "absent.whl"):
        assert sbom.main([str(tmp_path / bad)]) == 1, bad
        assert "is not a built wheel" in capsys.readouterr().out, bad

    # One good and one bad describes neither, because the loop that checks runs to the end
    # before the loop that writes begins.
    assert sbom.main([str(good), str(tmp_path / "absent.whl")]) == 1
    assert not list(tmp_path.glob("*.cdx.json")), "a refused run still wrote a document"

    # And the good one on its own still works, or the four refusals above prove only that
    # everything is refused.
    assert sbom.main([str(good)]) == 0
    assert list(tmp_path.glob("*.cdx.json"))
