"""A CycloneDX bill of materials for the wheel we just built, from the wheel itself.

`EP-047` and `EP-280` ask for an SBOM beside the published artefact. The audit filed both
under "no local work can move this", because a published release is what they name — and
that is half right in the way this repository keeps finding: the *published* half needs a
release, and the half that says "an SBOM exists, it is well formed, and it names the same
bytes that were built" is answerable here, today, by a command.

Hand-written, and that is the point rather than an economy. This document describes the
boundary `policy/threat-model.toml` calls `supply-chain`: the wheel a stranger installs. A
generator pulled from an index at release time is one more thing that can be swapped for
something else on the machine that builds what gets published — which is the harm the row
names. `release.yml` already refuses a tool cache on that job for the same reason. So this
reads a zip file and a metadata header with the standard library and nothing else.

What it does not do, said plainly so nobody reads more into it: it validates against the
subset of CycloneDX 1.6 named in `REQUIRED`, not against the full schema. A tool that
claims conformance it has not checked is the defect this repository exists to cure, so the
claim is the subset and the check is the subset.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from email.parser import Parser
from pathlib import Path

# The fields a CycloneDX 1.6 document is invalid without, plus the two this repository
# actually relies on: the component the BOM is about, and a hash naming its bytes. Read by
# `tests/test_sbom.py`, so removing one from `document()` turns the suite red by name.
REQUIRED = ("bomFormat", "specVersion", "version", "metadata", "components")
SPEC_VERSION = "1.6"


def _metadata(wheel: Path) -> tuple[str, str, list[str]]:
    """Name, version and declared dependencies, read out of the wheel's own METADATA."""

    with zipfile.ZipFile(wheel) as archive:
        found = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        if len(found) != 1:
            raise ValueError(f"{wheel.name} carries {len(found)} METADATA files, not one")
        header = Parser().parsestr(archive.read(found[0]).decode("utf-8", "replace"))
    # A tuple and not a dictionary of `object`: the caller iterates the requirements, and
    # a `dict[str, object]` makes that untypeable — mypy said so, and widening the value type
    # to satisfy it would have moved the looseness one line over instead of removing it.
    return (
        str(header.get("Name", "")),
        str(header.get("Version", "")),
        [str(one) for one in header.get_all("Requires-Dist") or [] if one],
    )


def _requirement_name(line: str) -> str:
    """The distribution a `Requires-Dist` line names, without its markers or extras.

    `httpx>=0.27; extra == "net"` is httpx. Splitting is enough here because the name is
    the first token by grammar, and a parser that resolved versions would be claiming to
    know what pip will install, which this document does not claim.
    """

    for stop in (";", "[", "(", "=", "<", ">", "!", "~", " "):
        line = line.split(stop, 1)[0]
    return line.strip()


def document(wheel: Path) -> dict[str, object]:
    """The BOM for one built wheel, as a dictionary.

    Deterministic: two runs over the same bytes produce the same document, because a
    timestamp or a random serial number would make every release's SBOM differ from every
    other and hide the one difference that matters.
    """

    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    name, version, requires = _metadata(wheel)
    purl = f"pkg:pypi/{name}@{version}"
    return {
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        # From the wheel's digest rather than from a clock, so the document is reproducible.
        "serialNumber": f"urn:uuid:{digest[:8]}-{digest[8:12]}-{digest[12:16]}"
        f"-{digest[16:20]}-{digest[20:32]}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "library",
                "bom-ref": purl,
                "name": name,
                "version": version,
                "purl": purl,
                # The whole reason this file exists: the SBOM names the bytes that were
                # built. `tests/test_sbom.py` hashes the wheel itself and compares.
                "hashes": [{"alg": "SHA-256", "content": digest}],
            }
        },
        "components": [
            {
                "type": "library",
                "bom-ref": f"pkg:pypi/{_requirement_name(line)}",
                "name": _requirement_name(line),
                "purl": f"pkg:pypi/{_requirement_name(line)}",
            }
            for line in sorted(requires)
            if _requirement_name(line)
        ],
    }


def write(wheel: Path, into: Path | None = None) -> Path:
    """Write the BOM beside the wheel and return where it landed.

    `.cdx.json` beside `dist/*.whl`, because `release.yml` attests `dist/*` as one subject
    list: a document that sits somewhere else is attested by nothing.
    """

    where = (into or wheel.parent) / f"{wheel.stem}.cdx.json"
    where.write_text(json.dumps(document(wheel), indent=2, sort_keys=True) + "\n", "utf-8")
    return where


def matches(wheel: Path, bom: Path) -> bool:
    """Does this document describe those bytes?

    The comparison the release job makes, extracted so something can drive it. Inline in a
    workflow it was a claim nobody could exercise: the job runs only on a tag, so the one
    check standing between a swapped SBOM and a published release had never executed and
    could not be made to.

    The attack it answers is not a corrupted file — it is a *valid* document describing a
    different wheel. Every field parses, the digest is a real sha256, and only comparing it
    to the artefact it claims to be about tells the two apart.
    """

    try:
        named = json.loads(bom.read_text("utf-8"))["metadata"]["component"]["hashes"][0]
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return False
    if named.get("alg") != "SHA-256":
        return False
    return named.get("content") == hashlib.sha256(wheel.read_bytes()).hexdigest()


def main(argv: list[str]) -> int:
    """`python -m ai_engineering.sbom dist/*.whl`, one BOM per wheel named."""

    wheels = [Path(one) for one in argv]
    if not wheels:
        print("  INCOMPLETE: no wheel was named, so nothing was described.")
        return 1
    for wheel in wheels:
        print(f"  {write(wheel)}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
