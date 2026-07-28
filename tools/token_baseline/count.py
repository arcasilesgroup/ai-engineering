"""spec-187 W1 (T-1) — canonical token-baseline snapshot counter.

Records per-file + total token counts over the CANONICAL surface ONLY so
later waves can diff against it and prove the >=25% canonical-token
reduction target (spec-187 D-187-02). Re-running the counter is
deterministic: the same corpus yields the same total.

CANONICAL surface (nothing else — mirrors are derived and excluded):

* ``.claude/skills/**/SKILL.md``
* ``.claude/agents/*.md``
* top-level rulebook: ``CLAUDE.md``, ``AGENTS.md``, ``CONSTITUTION.md``,
  ``SOUL.md``
* ``.ai-engineering/reference/*.md``

Tokeniser: tiktoken ``cl100k_base`` (optional extra — ``uv sync --extra
tokens``). If tiktoken is unavailable the counter falls back to a documented
``len(text) / 4`` heuristic, which measured roughly 3.6% off a real BPE count.

spec-201 D-201-19: the fallback is labelled AT THE VALUE, not only in the
header — ``grand_total_tokens_are_estimated`` rides beside the total and the
summary line prints ``grand_total=~N`` — so an estimate can never be read as a
measurement. The label describes the number; it never changes it.

Tool choice is DEFERRED (spec-187 Open Question — build vs buy): this
thin in-repo counter vs the external ``token-baseline`` CLI. Both are
recorded in the snapshot header; W1 only needs one reproducible number.

Usage::

    python -m tools.token_baseline.count            # write + print total
    python -m tools.token_baseline.count --stdout   # print JSON, no write

Pure-ASCII stdout on non-tty / raw streams (spec-187 D-187-10).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_DEFAULT_OUTPUT = (
    _REPO_ROOT / ".ai-engineering" / "runtime" / "research" / "spec-187-token-baseline.json"
)

# Both candidate tools recorded so the Open Question resolution is
# traceable in the artifact itself (spec-187 References / Open Questions).
_CANDIDATE_TOOLS = {
    "in_repo_counter": "tools/token_baseline/count.py (this thin tiktoken counter)",
    "external_cli": "token-baseline (per-file tiktoken snapshots, dup detection)",
    "final_choice": "DEFERRED — spec-187 Open Question (build vs buy)",
}


def canonical_files(repo_root: Path) -> list[Path]:
    """Return the sorted CANONICAL surface file list (mirrors excluded)."""
    files: list[Path] = []

    skills_root = repo_root / ".claude" / "skills"
    if skills_root.is_dir():
        files.extend(sorted(skills_root.glob("*/SKILL.md")))

    agents_root = repo_root / ".claude" / "agents"
    if agents_root.is_dir():
        files.extend(sorted(agents_root.glob("*.md")))

    for name in ("CLAUDE.md", "AGENTS.md", "CONSTITUTION.md", "SOUL.md"):
        candidate = repo_root / name
        if candidate.is_file():
            files.append(candidate)

    reference_root = repo_root / ".ai-engineering" / "reference"
    if reference_root.is_dir():
        files.extend(sorted(reference_root.glob("*.md")))

    return files


_HEURISTIC_LABEL = "char4-heuristic"

_ESTIMATE_NOTE = (
    "APPROXIMATE (~): token counts come from the char4-heuristic fallback, "
    "measured roughly 3.6% off a real BPE count. Install the optional extra "
    "(uv sync --extra tokens) for an exact cl100k_base count."
)


def _load_encoder():
    """Return ``(counter, tokenizer_label)``.

    Prefers tiktoken ``cl100k_base``; falls back to a documented
    ``len(text) / 4`` heuristic when tiktoken is unavailable. tiktoken is an
    OPTIONAL extra (D-201-19), so the fallback is the default path.
    """
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return (lambda text: len(enc.encode(text))), "cl100k_base"
    except Exception:
        return (lambda text: (len(text) + 3) // 4), _HEURISTIC_LABEL


def build_snapshot(repo_root: Path) -> dict:
    """Compute the token snapshot dict over the canonical surface."""
    counter, tokenizer = _load_encoder()
    estimated = tokenizer == _HEURISTIC_LABEL

    per_file: dict[str, int] = {}
    total = 0
    for path in canonical_files(repo_root):
        text = path.read_text(encoding="utf-8")
        tokens = counter(text)
        per_file[path.relative_to(repo_root).as_posix()] = tokens
        total += tokens

    header: dict[str, object] = {
        "spec": "spec-187",
        "task": "T-1",
        "purpose": (
            "Canonical token-baseline snapshot; later waves diff against "
            "this to prove the >=25% reduction target (D-187-02)."
        ),
        "surface": "CANONICAL only (mirrors excluded)",
        "tokenizer": tokenizer,
        "estimated": estimated,
        "candidate_tools": _CANDIDATE_TOOLS,
        "reproducible": "Re-running the counter over the same corpus yields the same total.",
    }
    if estimated:
        header["estimate_note"] = _ESTIMATE_NOTE

    return {
        "_header": header,
        "grand_total_tokens": total,
        "grand_total_tokens_are_estimated": estimated,
        "file_count": len(per_file),
        "per_file_tokens": per_file,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="token_baseline",
        description="spec-187 canonical token-baseline snapshot counter.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Repo root to scan (default: this checkout).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="Snapshot JSON path (default: runtime/research/spec-187-token-baseline.json).",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout instead of writing the snapshot file.",
    )
    args = parser.parse_args(argv)

    snapshot = build_snapshot(args.repo_root)
    payload = json.dumps(snapshot, indent=2, sort_keys=False) + "\n"

    if args.stdout:
        sys.stdout.write(payload)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        # Pure-ASCII summary line (D-187-10 — safe on cp1252 / non-tty).
        # `~` marks an unmeasured count at the value itself (D-201-19).
        marker = "~" if snapshot["grand_total_tokens_are_estimated"] else ""
        sys.stdout.write(
            f"token-baseline: {snapshot['file_count']} canonical files "
            f"({snapshot['_header']['tokenizer']}) "
            f"grand_total={marker}{snapshot['grand_total_tokens']} tokens "
            f"-> {args.output.relative_to(args.repo_root).as_posix()}\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
