"""md_mirror checker — spec-131 S1 contract for the four IDE mirrors.

Five sub-checks enforce the byte-equivalent canonical payload + the
project-identity CONSTITUTION rescope:

1. **check_sha256_equivalence** — AGENTS.md, CLAUDE.md, GEMINI.md, and
   `.github/copilot-instructions.md` share identical canonical-payload
   bytes after the ``<!-- ide-extras:start -->…<!-- ide-extras:end -->``
   fence is stripped.
2. **check_no_agents_import** — no mirror contains a bare ``@AGENTS.md``
   import directive (a Claude-only quirk that broke cross-IDE parity).
3. **check_no_gemini_orphan** — D-131-03 deletes ``<repo>/.gemini/GEMINI.md``;
   the file must not exist.
4. **check_no_codex_orphan** — Codex reads root AGENTS.md natively; an
   in-repo ``<repo>/.codex/AGENTS.md`` would shadow it.
5. **check_constitution_clean** — after D-131-04 migration,
   CONSTITUTION.md owns project identity only and must not contain any
   header from ``FORBIDDEN_CONSTITUTION_HEADERS``.

Pure-stdlib (re + pathlib + hashlib). Returns ``RubricResult`` records
that fold into the existing ``skill_lint --check`` rendering pipeline.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}


@dataclass(frozen=True)
class RubricResult:
    """Outcome of running an md_mirror sub-check."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


# ── Forbidden CONSTITUTION headers (D-131-04 migration verification) ─────
# Every header that previously lived in CONSTITUTION.md and now lives in
# CANONICAL.md (§§1-13). Presence of any of these as a ``## <name>`` (or
# ``### <name>``) heading in CONSTITUTION.md indicates an incomplete
# migration.
FORBIDDEN_CONSTITUTION_HEADERS: tuple[str, ...] = (
    "Simplicity First",
    "Plan-Mode Default",
    "Surgical Changes",
    "Goal-Driven Execution",
    "Subagent Strategy",
    "Self-Improvement Loop",
    "Demand Elegance",
    "Autonomous Bug Fixing",
    "Think Before Coding",
    "KISS",
    "YAGNI",
    "SOLID",
    "DRY",
    "TDD",
    "SDD",
    "Clean Code",
    "Hexagonal Architecture",
)

# ── Mirror surface paths (relative to repo root) ─────────────────────────
_MIRRORS: tuple[str, ...] = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
)

_FENCE_RE = re.compile(
    # Strip the fence verbatim (including its inner content). The
    # `sync_mirrors` generator places the fence at end-of-file with a
    # single trailing newline; every mirror — including the base AGENTS.md
    # — carries an empty fence placeholder so the canonical body bytes
    # match exactly after this regex runs.
    r"<!-- ide-extras:start -->.*?<!-- ide-extras:end -->",
    re.DOTALL,
)

# Bare `@AGENTS.md` import directive — a line containing only the
# directive (no surrounding code fences or prose). Inline mentions inside
# the §14 authoring-contract table are intentional documentation.
_AGENTS_IMPORT_RE = re.compile(r"^\s*@AGENTS\.md\s*$", re.MULTILINE)


def strip_ide_extras(text: str) -> str:
    """Return `text` with every ide-extras fenced block removed.

    Public helper: downstream tests (parity, idempotency) consume this so
    a single regex defines the contract.
    """
    return _FENCE_RE.sub("", text)


def _sha256_payload(path: Path) -> str:
    body = path.read_text(encoding="utf-8")
    return hashlib.sha256(strip_ide_extras(body).encode("utf-8")).hexdigest()


# ───────────────────────────── sub-checks ────────────────────────────────


def check_sha256_equivalence(repo_root: Path) -> RubricResult:
    """OK when all four mirrors share canonical payload bytes."""
    hashes: dict[str, str] = {}
    for rel in _MIRRORS:
        path = repo_root / rel
        if not path.is_file():
            return RubricResult(
                "md_mirror_sha256",
                "CRITICAL",
                f"missing mirror: {rel}",
            )
        hashes[rel] = _sha256_payload(path)
    distinct = set(hashes.values())
    if len(distinct) == 1:
        return RubricResult(
            "md_mirror_sha256",
            "OK",
            f"4 mirrors share sha256 {next(iter(distinct))[:12]}",
        )
    summary = ", ".join(f"{rel}={h[:12]}" for rel, h in hashes.items())
    return RubricResult(
        "md_mirror_sha256",
        "CRITICAL",
        f"canonical payload drift: {summary}",
    )


def check_no_agents_import(repo_root: Path) -> RubricResult:
    """OK when no mirror contains a bare `@AGENTS.md` import directive."""
    offenders: list[str] = []
    for rel in _MIRRORS:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if _AGENTS_IMPORT_RE.search(text):
            offenders.append(rel)
    if offenders:
        return RubricResult(
            "md_mirror_no_agents_import",
            "CRITICAL",
            f"@AGENTS.md import in {offenders}",
        )
    return RubricResult(
        "md_mirror_no_agents_import",
        "OK",
        "no @AGENTS.md import directive in any mirror",
    )


def check_no_gemini_orphan(repo_root: Path) -> RubricResult:
    """OK when `<repo>/.gemini/GEMINI.md` does not exist (D-131-03)."""
    orphan = repo_root / ".gemini" / "GEMINI.md"
    if orphan.exists():
        return RubricResult(
            "md_mirror_no_gemini_orphan",
            "CRITICAL",
            f"orphan present: {orphan.relative_to(repo_root)}",
        )
    return RubricResult(
        "md_mirror_no_gemini_orphan",
        "OK",
        ".gemini/GEMINI.md absent (D-131-03)",
    )


def check_no_codex_orphan(repo_root: Path) -> RubricResult:
    """OK when `<repo>/.codex/AGENTS.md` does not exist."""
    orphan = repo_root / ".codex" / "AGENTS.md"
    if orphan.exists():
        return RubricResult(
            "md_mirror_no_codex_orphan",
            "CRITICAL",
            f"orphan present: {orphan.relative_to(repo_root)}",
        )
    return RubricResult(
        "md_mirror_no_codex_orphan",
        "OK",
        ".codex/AGENTS.md absent (Codex reads root)",
    )


def check_constitution_clean(repo_root: Path) -> RubricResult:
    """OK when CONSTITUTION.md contains no AI-behaviour header (D-131-04)."""
    constitution = repo_root / "CONSTITUTION.md"
    if not constitution.is_file():
        return RubricResult(
            "md_mirror_constitution_clean",
            "CRITICAL",
            f"missing: {constitution.relative_to(repo_root)}",
        )
    text = constitution.read_text(encoding="utf-8")
    offenders: list[str] = []
    # Accept ASCII hyphen plus the two Unicode dash variants used in
    # legacy `Article XI -- Header` / `Article XI <endash> Header` lines.
    # Characters built via chr() so the source file stays ASCII-clean
    # (operator anti-suppression policy: no inline RUF001 markers).
    _dash_class = "[" + "-" + chr(0x2013) + chr(0x2014) + "]"
    for header in FORBIDDEN_CONSTITUTION_HEADERS:
        # Match ``## <header>`` or ``### <header>`` as a section heading.
        pattern = re.compile(
            rf"^#{{2,3}}\s+(?:[IVX]+\s+{_dash_class}\s+)?(?:§?10\.\d+\s+)?{re.escape(header)}\b",
            re.MULTILINE,
        )
        if pattern.search(text):
            offenders.append(header)
    if offenders:
        return RubricResult(
            "md_mirror_constitution_clean",
            "CRITICAL",
            f"forbidden AI-behaviour headers in CONSTITUTION.md: {offenders}",
        )
    return RubricResult(
        "md_mirror_constitution_clean",
        "OK",
        "CONSTITUTION.md carries only project-identity headers",
    )


# ───────────────────────────── driver ─────────────────────────────────────


def check_md_mirror_consistency(repo_root: Path) -> list[RubricResult]:
    """Run all five md_mirror sub-checks and return their results."""
    return [
        check_sha256_equivalence(repo_root),
        check_no_agents_import(repo_root),
        check_no_gemini_orphan(repo_root),
        check_no_codex_orphan(repo_root),
        check_constitution_clean(repo_root),
    ]
