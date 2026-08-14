"""The privacy checks an acceptance candidate must clear before it is published.

The repository already has one executable secret scanner. It has never had an executable
personal-data or machine-path scanner, so the acceptance writer could not truthfully claim
that a candidate was privacy-safe: a human checkpoint is not a check. These two
deterministic checks close that gap and say so plainly when they cannot decide.

Nothing here echoes the candidate. A scanner that quotes what it found writes the datum it
was built to keep out of the record, so every verdict names a class and never a value.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# The specification's evidence bound. Refusing at the bound is the point: a scanner that
# gives up quietly and reports clean has turned a bound into a bypass.
MAX_BYTES = 100_000


@dataclass(frozen=True, slots=True)
class Verdict:
    """One stable machine result for a privacy check. Never carries candidate text."""

    outcome: str
    code: str = ""
    reason: str = ""

    def as_dict(self) -> dict[str, str]:
        result = {"outcome": self.outcome}
        if self.outcome != "PASS":
            result.update(code=self.code, reason=self.reason)
        return result


CLEAN = Verdict("PASS")

# The local part is bounded at its real 64-character maximum. An unbounded run before the
# `@` makes this scan quadratic on hostile text, which is the one input a scanner gets.
_EMAIL = re.compile(r"[^\s@]{1,64}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63}){1,8}")
_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\b"
)
# Only the full eight-group form and the `::` form. A looser pattern reads 12:30:45 as an
# address, and a check that refuses a clock is a check people route around.
_IPV6 = re.compile(
    r"\b(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}\b|\b[0-9A-Fa-f]{0,4}::[0-9A-Fa-f:]{0,39}\b"
)
_ISO_DATE = re.compile(r"\b[0-9]{4}-[0-9]{2}-[0-9]{2}\b")
_PHONE = re.compile(r"(?:\+[0-9][0-9 ()\-.]{7,17}[0-9])|(?:\([0-9]{3}\)[0-9 \-.]{6,14}[0-9])")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SENTENCE_START = re.compile(r"(?:\A|[.!?:;]\s+|\n)\s*")
_CAPITALIZED = re.compile(r"\b[A-Z][a-z]+\b")


def readable_text(candidate: object) -> Verdict | str:
    """Return the candidate as text, or the verdict saying why it could not be read.

    Shared by both deterministic checks, because "I could not read it" must be one answer
    and not two that drift apart.
    """

    if not isinstance(candidate, str):
        return Verdict(
            "INCOMPLETE",
            "ACCEPTANCE_PRIVACY_UNSUPPORTED_INPUT",
            "the candidate is not text, so no privacy check could run",
        )
    try:
        encoded = candidate.encode("utf-8")
    except UnicodeEncodeError:
        return Verdict(
            "INCOMPLETE",
            "ACCEPTANCE_PRIVACY_UNDECODABLE",
            "the candidate holds bytes that are not valid text",
        )
    if len(encoded) > MAX_BYTES:
        return Verdict(
            "INCOMPLETE",
            "ACCEPTANCE_PRIVACY_OVER_BOUND",
            f"the candidate exceeds the {MAX_BYTES}-byte scanning bound",
        )
    if _CONTROL.search(candidate) is not None:
        return Verdict(
            "INCOMPLETE",
            "ACCEPTANCE_PRIVACY_CONTROL_CHARACTER",
            "the candidate holds a control character, so its words cannot be read",
        )
    return candidate


def _names_a_person(candidate: str) -> bool:
    """Two capitalized words in a row may be a person or a product, and this check cannot
    tell them apart. Undecidable is reported as undecidable; guessing would be worse than
    either answer. Capitalization that grammar forces is not evidence, so a sentence's
    first word never starts a pair."""

    grammatical = {match.end() for match in _SENTENCE_START.finditer(candidate)}
    matches = list(_CAPITALIZED.finditer(candidate))
    return any(
        first.start() not in grammatical
        and second.start() not in grammatical
        and 0 < second.start() - first.end() <= 2
        for first, second in zip(matches, matches[1:], strict=False)
    )


def acceptance_pii_v1(candidate: object) -> Verdict:
    """Decide whether one candidate text carries a personal datum.

    `FAIL` is a conclusive match, `INCOMPLETE` is input this check cannot classify, and
    `PASS` is reached only by actually deciding. A conclusive match outranks an ambiguity:
    text holding both an address and an unclear name is already disqualified.
    """

    text = readable_text(candidate)
    if isinstance(text, Verdict):
        return text

    for pattern, code in (
        (_EMAIL, "ACCEPTANCE_PII_EMAIL"),
        (_IPV4, "ACCEPTANCE_PII_IP_ADDRESS"),
        (_IPV6, "ACCEPTANCE_PII_IP_ADDRESS"),
    ):
        if pattern.search(text) is not None:
            kind = "email address" if code.endswith("EMAIL") else "IP address"
            return Verdict("FAIL", code, f"an {kind} appears in the candidate")
    if _PHONE.search(_ISO_DATE.sub(" ", text)) is not None:
        return Verdict(
            "FAIL", "ACCEPTANCE_PII_PHONE_LIKE", "a telephone-like number appears in the candidate"
        )
    if _names_a_person(text):
        return Verdict(
            "INCOMPLETE",
            "ACCEPTANCE_PII_NAME_AMBIGUOUS",
            "the candidate holds a capitalized pair that may name a person",
        )
    return CLEAN


# A machine path names a place on one host's filesystem. A repository-relative path names a
# place in this repository and is the only shape an acceptance record may carry.
_HOME = re.compile(r"(?<![A-Za-z0-9._~-])(?:~/|/(?:home|Users|root)/)")
_WINDOWS_DRIVE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
_UNC = re.compile(r"(?<!\\)\\\\[A-Za-z0-9._-]+\\")
# Any other absolute POSIX path may or may not be one host's; this check will not guess.
# A URL's authority is not an absolute path, so `:` and `/` also close the lookbehind.
_ABSOLUTE = re.compile(r"(?<![A-Za-z0-9._~:/-])/[A-Za-z0-9._-]+/")


def acceptance_machine_path_v1(candidate: object) -> Verdict:
    """Decide whether one candidate text carries a path belonging to one machine.

    The three families the specification names are conclusive `FAIL`. Any other absolute
    path is `INCOMPLETE`, because this check cannot tell a shared system path from one
    host's own; guessing clean there would be the failure the record exists to prevent.
    Repository-relative text is the only thing that reaches `PASS`.
    """

    text = readable_text(candidate)
    if isinstance(text, Verdict):
        return text

    for pattern, code, kind in (
        (_HOME, "ACCEPTANCE_MACHINE_PATH_HOME", "a home directory path"),
        (_WINDOWS_DRIVE, "ACCEPTANCE_MACHINE_PATH_WINDOWS_DRIVE", "a Windows drive path"),
        (_UNC, "ACCEPTANCE_MACHINE_PATH_UNC", "a UNC network path"),
    ):
        if pattern.search(text) is not None:
            return Verdict("FAIL", code, f"{kind} appears in the candidate")
    if _ABSOLUTE.search(text) is not None:
        return Verdict(
            "INCOMPLETE",
            "ACCEPTANCE_MACHINE_PATH_ABSOLUTE",
            "the candidate holds an absolute path this check cannot attribute to a machine",
        )
    return CLEAN


# The one executable secret scanner this repository already has, pinned exactly. A scanner
# whose version is not the one we tested is a scanner whose answer we cannot read.
GITLEAKS_VERSION = "8.30.1"
GITLEAKS_ARGV = ("gitleaks", "dir", ".", "--redact", "--no-banner", "--exit-code", "1")
_TIMEOUT_SECONDS = 120


def _run(argv: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
    """One bounded subprocess call. Separated so a test can stand in for the scanner
    without the product growing an injection parameter it would never use in production."""

    return subprocess.run(
        list(argv), cwd=cwd, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS, check=False
    )


def _unavailable(reason: str) -> Verdict:
    return Verdict("INCOMPLETE", "ACCEPTANCE_GITLEAKS_UNAVAILABLE", reason)


def gitleaks_v1(directory: Path) -> Verdict:
    """Scan one unpublished record directory with the exact pinned scanner.

    Exit 1 is a conclusive `FAIL`, exit 0 is clean, and absence, version drift, a timeout
    or any other exit is `INCOMPLETE`. The scanner's output is read for none of this and
    kept nowhere: the verdict names a class, and `record.json` is the only artifact.
    """

    try:
        version = _run(("gitleaks", "version"), directory)
    except FileNotFoundError:
        return _unavailable("the pinned secret scanner is not installed")
    except (OSError, subprocess.SubprocessError):
        return _unavailable("the pinned secret scanner could not be executed")
    if version.returncode != 0 or version.stdout.strip() != GITLEAKS_VERSION:
        return _unavailable(f"the secret scanner is not exactly version {GITLEAKS_VERSION}")

    try:
        scan = _run(GITLEAKS_ARGV, directory)
    except (OSError, subprocess.SubprocessError):
        return _unavailable("the pinned secret scanner could not complete its scan")
    if scan.returncode == 1:
        return Verdict(
            "FAIL", "ACCEPTANCE_GITLEAKS_SECRET", "the pinned secret scanner found a secret"
        )
    if scan.returncode != 0:
        return _unavailable("the secret scanner returned an exit code with no defined meaning")
    return CLEAN


def acceptance_privacy_gate(directory: Path, candidates: Sequence[str]) -> Verdict:
    """All three checks, and the rule that only three clean results reach publication.

    A conclusive `FAIL` outranks an `INCOMPLETE`, because a candidate already known to
    carry a secret, a personal datum or a machine path does not become publishable by a
    second check being unable to decide. Neither outcome publishes anything.
    """

    verdicts = [gitleaks_v1(directory)]
    for candidate in candidates:
        verdicts.append(acceptance_pii_v1(candidate))
        verdicts.append(acceptance_machine_path_v1(candidate))
    for outcome in ("FAIL", "INCOMPLETE"):
        blocking = next((verdict for verdict in verdicts if verdict.outcome == outcome), None)
        if blocking is not None:
            return blocking
    return CLEAN
