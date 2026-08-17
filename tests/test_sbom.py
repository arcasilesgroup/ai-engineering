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
    assert sbom.document(built) == sbom.document(built)


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
