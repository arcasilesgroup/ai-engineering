#!/usr/bin/env python3
"""Deterministic session bootstrap — JSON + markdown dashboard.

Replaces every data-shuffling step in ``/ai-start`` with a single stdlib
script. Two output modes (``--format=json`` default for tooling, and
``--format=markdown`` so the IDE agent never has to re-derive any field
to render the dashboard).

Inputs (each one fail-open per field):

* ``git`` HEAD sha + subject + branch + last N commits.
* ``.ai-engineering/specs/spec.md`` frontmatter (yaml.safe_load).
* ``.ai-engineering/specs/plan.md`` (regex count of ``[x]`` vs ``[ ]``).
* ``.ai-engineering/state/framework-events.ndjson`` tail (last 7 d window).
* ``.ai-engineering/state/decision-store.json`` decision records (active
  decisions + risk-acceptance decisions; spec-148 files-only).
* ``.ai-engineering/manifest.yml`` (``name`` + ``hooks_health`` + work_items).
* ``.ai-engineering/LESSONS.md`` line count.
* ``.claude/skills/`` + ``.claude/agents/`` filesystem counts.
* ``.ai-engineering/proposals/`` filesystem count.
* ``gh project item-list`` board fetch with hard 2 s subprocess timeout
  and stale-while-revalidate cache at ``.ai-engineering/runtime/
  board-cache.json``.

Output shape (JSON ``schema_version: 1`` — additive, backward compatible):

```
{
  "schema_version": 1,
  "elapsed_ms": 287,
  "project_name": "ai-engineering",
  "branch": "feat/spec-126-...",
  "last_commit": {"sha": "7e6a004f", "subject": "fix(...): ..."},
  "recent_commits": [{"sha": "...", "subject": "..."}, ...],
  "active_spec": {"id": "spec-126", "state": "approved", "title": "...",
                  "tasks_total": 18, "tasks_done": 14},
  "recent_events_7d": 511,
  "hooks_health": "ok",
  "lessons_count": 253,
  "skills_total": 48,
  "agents_total": 9,
  "active_decisions": 0,
  "accepted_risks": 0,
  "proposals_count": 0,
  "board_summary": {"provider": "github", "owner": "...", "number": 4,
                    "items_total": 50, "by_status": {"Done": 50},
                    "fetched_at": "...", "cache_state": "fresh"},
  "markdown": "## ◈ ai-engineering\\n..."
}
```

Time budget: < 3 s wall-clock cold path (board fetch dominates). The
no-board path stays under 300 ms. ``warnings: ["budget_exceeded"]`` is
emitted when the wall exceeds the cold-path ceiling. Stdlib only,
pyyaml is the single allowed third-party dep (already in the project
venv).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

_SKILLS_LIB_DIR = Path(__file__).resolve().parent / "skills"
if str(_SKILLS_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILLS_LIB_DIR))

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]

from skill_scripts_lib.git_activity import NoCommitsError, last_commit  # noqa: E402
from skill_scripts_lib.markdown_render import (  # noqa: E402
    InvalidFrontmatterError,
    parse_frontmatter,
)

SCHEMA_VERSION = 1
BUDGET_MS = 5000.0
RECENT_WINDOW_DAYS = 7
RECENT_COMMITS_N = 5
BOARD_TIMEOUT_S = 8.0  # paginated GraphQL across all items (~4.2s for 430 items)
BOARD_CACHE_FRESH_S = 5 * 60
BOARD_CACHE_MAX_AGE_S = 30 * 60
BOARD_PAGE_SIZE = 100

_REPO_ROOT = Path(__file__).resolve().parents[2]


# spec-142 D-142-02: surface→(skills, agents) directory map. Keys MUST stay
# in sync with the closed 6-surface enum at
# src/ai_engineering/config/mirror_inventory.py (`_PROVIDER_TREE_MAPS` keys
# plus the no-mirror-tree surfaces). CI test in
# tests/unit/scripts/test_session_bootstrap.py::TestSurfaceDirs enforces parity.
_SURFACE_DIRS: dict[str, tuple[str, str]] = {
    "claude-code": (".claude/skills", ".claude/agents"),
    "codex": (".codex/skills", ".codex/agents"),
    "github-copilot": (".github/skills", ".github/agents"),
    "opencode": (".opencode/skills", ".opencode/agents"),
    "cursor": (".cursor/skills", ".cursor/agents"),
    "antigravity": (".agents/skills", ".agents/agents"),
}
_DEFAULT_SURFACE = "claude-code"  # spec-133 D-133-16 fallback when surfaces.enabled is empty


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path, timeout: float = 2.0) -> str | None:
    try:
        result = subprocess.run(
            ("git", *args), cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _read_yaml(path: Path) -> dict | None:
    if not path.is_file() or yaml is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _read_manifest_minimal(path: Path) -> dict:
    """Stdlib-only mini-parser: extract ``name`` and ``surfaces.enabled`` only.

    Never raises.  Returns ``{}`` on any error or when fields are absent.
    Anchors: D-142-01 (≤30 LOC body), D-142-07 (2-field grammar).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # OSError, UnicodeDecodeError, etc.
        return {}

    result: dict = {}

    # --- name: unquoted or double-quoted scalar on its own line ---------------
    m = re.search(r'^name:\s+"?([^"\r\n]+?)"?\s*(?:#.*)?$', text, re.MULTILINE)
    if m:
        result["name"] = m.group(1).strip()

    # --- surfaces.enabled: flow list  [a, b, c] ------------------------------
    flow = re.search(r"^surfaces:\s*\n\s+enabled:\s*\[([^\]]*)\]", text, re.MULTILINE)
    if flow:
        items = [s.strip() for s in flow.group(1).split(",") if s.strip()]
        if items:
            result["surfaces"] = {"enabled": items}
        return result

    # --- surfaces.enabled: block list  \n  - item ----------------------------
    block = re.search(
        r"^surfaces:\s*\n\s+enabled:\s*\n((?:\s+-\s+\S[^\n]*\n?)+)",
        text,
        re.MULTILINE,
    )
    if block:
        items = re.findall(r"^\s+-\s+(\S+)", block.group(1), re.MULTILINE)
        if items:
            result["surfaces"] = {"enabled": items}

    return result


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


def _read_git(cwd: Path) -> dict:
    out: dict = {"branch": None, "last_commit": None}
    branch = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    if branch:
        out["branch"] = branch.strip()
    original = Path.cwd()
    commit = None
    try:
        os.chdir(cwd)
        commit = last_commit()
    except (NoCommitsError, OSError, FileNotFoundError):
        commit = None
    finally:
        with contextlib.suppress(OSError):
            os.chdir(original)
    if commit is not None:
        out["last_commit"] = {"sha": commit.sha[:8], "subject": commit.subject}
    return out


def _read_recent_commits(cwd: Path, n: int = RECENT_COMMITS_N) -> list[dict]:
    raw = _git("log", f"-{n}", "--format=%h%x00%s", cwd=cwd)
    if not raw:
        return []
    out: list[dict] = []
    for line in raw.splitlines():
        if "\x00" not in line:
            continue
        sha, subject = line.split("\x00", 1)
        sha = sha.strip()
        if sha:
            out.append({"sha": sha, "subject": subject.strip()})
    return out


# ---------------------------------------------------------------------------
# Specs / plan
# ---------------------------------------------------------------------------


def _read_spec(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.strip() or "no active spec" in text.lower()[:200]:
        return None
    try:
        fm = parse_frontmatter(text)
    except InvalidFrontmatterError:
        return None
    if not fm:
        return None
    spec_id = fm.get("id") or fm.get("spec_id") or fm.get("spec")
    state = fm.get("status") or fm.get("state")
    title = fm.get("title")
    if not (spec_id or state or title):
        return None
    return {"id": spec_id, "state": state, "title": title}


_TASK_RE = re.compile(r"^\s*-\s*\[([ xX])\]", re.MULTILINE)


def _read_plan(path: Path) -> dict:
    """Return ``{tasks_total, tasks_done, status}``.

    ``status`` is the plan.md frontmatter ``status`` field (or
    ``None``). The plan's own status is independent of the parent
    spec's status — a spec stays ``approved`` while its plan can
    transition to ``shipped-pending-pr-merge`` between PR open and
    merge.
    """
    empty = {"tasks_total": 0, "tasks_done": 0, "status": None}
    if not path.is_file():
        return empty
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return empty
    matches = _TASK_RE.findall(text)
    total = len(matches)
    done = sum(1 for m in matches if m in ("x", "X"))
    status = None
    try:
        fm = parse_frontmatter(text)
        if fm:
            raw = fm.get("status") or fm.get("state")
            if isinstance(raw, str) and raw.strip():
                status = raw.strip()
    except InvalidFrontmatterError:
        pass
    return {"tasks_total": total, "tasks_done": done, "status": status}


# ---------------------------------------------------------------------------
# Audit chain
# ---------------------------------------------------------------------------


def _read_recent_events(path: Path, window_days: int = RECENT_WINDOW_DAYS) -> int:
    if not path.is_file():
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    count = 0
    try:
        with path.open("rb") as fh:
            try:
                fh.seek(0, 2)
                size = fh.tell()
                read = min(size, 256 * 1024)
                fh.seek(size - read)
                tail = fh.read().decode("utf-8", errors="replace")
            except OSError:
                return 0
    except OSError:
        return 0
    for line in tail.splitlines()[-1000:]:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = evt.get("ts") or evt.get("timestamp")
        if not isinstance(ts, str):
            continue
        try:
            when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        if when >= cutoff:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def _read_manifest(root: Path) -> dict:
    path = root / ".ai-engineering" / "manifest.yml"
    data = _read_yaml(path)
    if data is not None:
        return data
    return _read_manifest_minimal(path)


def _project_name(manifest: dict) -> str:
    name = manifest.get("name")
    return name if isinstance(name, str) and name.strip() else "(unnamed)"


def _hooks_health(root: Path) -> str:
    """Compare hooks-manifest.json sha256s vs on-disk bytes.

    Returns ``ok`` when every entry matches, ``drift(N)`` when N hooks
    diverged or vanished, ``unknown`` when the manifest is unreadable.
    Reads sha pinning from ``.ai-engineering/state/hooks-manifest.json``
    (regenerated by ``regenerate-hooks-manifest.py``). Hashes are
    computed with CRLF→LF normalisation so the answer is identical
    across Windows / Linux / macOS checkouts.
    """
    manifest_path = root / ".ai-engineering" / "state" / "hooks-manifest.json"
    scripts_dir = root / ".ai-engineering" / "scripts" / "hooks"
    if not manifest_path.is_file():
        if scripts_dir.is_dir() and any(scripts_dir.iterdir()):
            return "unverified"
        return "unknown"
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    hooks = data.get("hooks")
    if not isinstance(hooks, dict) or not hooks:
        return "unknown"
    drift = 0
    for rel, expected in hooks.items():
        if not isinstance(expected, str):
            continue
        path = root / rel
        if not path.is_file():
            drift += 1
            continue
        try:
            content = path.read_bytes().replace(b"\r\n", b"\n")
        except OSError:
            drift += 1
            continue
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected:
            drift += 1
    return "ok" if drift == 0 else f"drift({drift})"


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------


def _primary_surface(manifest: dict) -> str:
    surfaces = manifest.get("surfaces") or {}
    enabled = surfaces.get("enabled") if isinstance(surfaces, dict) else None
    if isinstance(enabled, list) and enabled:
        first = enabled[0]
        if isinstance(first, str) and first in _SURFACE_DIRS:
            return first
    return _DEFAULT_SURFACE


def _resolved_surface_or_none(manifest: dict) -> str | None:
    """spec-142 D-142-06 / R-142-06: emit the raw first surface only if it
    is in the closed enum; otherwise None for tooling detection."""
    surfaces = manifest.get("surfaces") or {}
    enabled = surfaces.get("enabled") if isinstance(surfaces, dict) else None
    if isinstance(enabled, list) and enabled:
        first = enabled[0]
        if isinstance(first, str) and first in _SURFACE_DIRS:
            return first
    return None


def _count_skills(root: Path, manifest: dict) -> int:
    skills_rel, _ = _SURFACE_DIRS.get(_primary_surface(manifest), _SURFACE_DIRS[_DEFAULT_SURFACE])
    base = root / skills_rel
    if not base.is_dir():
        return 0
    return sum(1 for p in base.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def _count_agents(root: Path, manifest: dict) -> int:
    surface = _primary_surface(manifest)
    _, agents_rel = _SURFACE_DIRS.get(surface, _SURFACE_DIRS[_DEFAULT_SURFACE])
    base = root / agents_rel
    if not base.is_dir():
        return 0
    if surface == "github-copilot":
        pattern = "*.agent.md"
    elif surface == "cursor":
        pattern = "ai-*.mdc"
    else:
        pattern = "ai-*.md"
    return sum(1 for p in base.glob(pattern) if p.is_file())


def _count_lessons(path: Path) -> int:
    """Count ``### `` H3 headers — one per lesson in LESSONS.md.

    The file mixes meta H2 sections (``## Rules & Patterns``, ``## How
    to Add Lessons``, ``## Patterns``) with one H3 per individual
    lesson. Total line count is meaningless because lessons span
    multiple lines (context + learning + rule + example); the H3
    count is the right unit.
    """
    if not path.is_file():
        return 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for line in fh if line.startswith("### "))
    except OSError:
        return 0


def _count_proposals(root: Path) -> int:
    base = root / ".ai-engineering" / "proposals"
    if not base.is_dir():
        return 0
    return sum(1 for p in base.glob("**/*.md") if p.is_file())


def _read_decision_records(root: Path) -> list[dict]:
    """Load decision records from ``decision-store.json`` (stdlib; spec-148).

    Files-only: the dashboard counts come straight from the JSON decision
    store (the canonical SoT), not a SQLite projection. Returns ``[]`` on
    any read/parse error.
    """
    path = root / ".ai-engineering" / "state" / "decision-store.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    decisions = data.get("decisions") if isinstance(data, dict) else None
    if not isinstance(decisions, list):
        return []
    return [d for d in decisions if isinstance(d, dict)]


def _count_active_decisions(root: Path) -> int:
    return sum(1 for d in _read_decision_records(root) if d.get("status") == "active")


def _count_accepted_risks(root: Path) -> int:
    # spec-148: the risk_acceptances table was dead (zero writers); risk
    # acceptances are decision records with riskCategory == 'risk-acceptance'.
    return sum(
        1
        for d in _read_decision_records(root)
        if d.get("riskCategory") == "risk-acceptance" and d.get("status") == "active"
    )


# ---------------------------------------------------------------------------
# Observation backlog (delta vs last extract_instincts run)
# ---------------------------------------------------------------------------


def _count_unconsolidated_events(root: Path) -> dict:
    """Return ``{pending, threshold}`` for the observation pipeline.

    Reads ``.ai-engineering/observations/meta.json`` for the last
    ``extract_instincts`` checkpoint and ``deltaThreshold``, then tails
    ``state/observation-events.ndjson`` counting events with
    ``ts > lastExtractedAt``. The Stop hook auto-consolidates these on
    session end; the count is surfaced in the dashboard so the operator
    knows when ``/ai-session-watch --review`` is worthwhile.
    """
    out = {"pending": 0, "threshold": 10}
    meta = root / ".ai-engineering" / "observations" / "meta.json"
    if not meta.is_file():
        return out
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    threshold = data.get("deltaThreshold")
    if isinstance(threshold, int) and threshold > 0:
        out["threshold"] = threshold
    last_extracted = data.get("lastExtractedAt")
    if not isinstance(last_extracted, str):
        return out
    try:
        cutoff = datetime.fromisoformat(last_extracted.replace("Z", "+00:00"))
    except ValueError:
        return out
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    ndjson = root / ".ai-engineering" / "state" / "observation-events.ndjson"
    if not ndjson.is_file():
        return out
    try:
        with ndjson.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            read = min(size, 512 * 1024)
            fh.seek(size - read)
            tail = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return out
    pending = 0
    for line in tail.splitlines()[-2000:]:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = evt.get("ts") or evt.get("timestamp")
        if not isinstance(ts, str):
            continue
        try:
            when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        if when > cutoff:
            pending += 1
    out["pending"] = pending
    return out


# ---------------------------------------------------------------------------
# Recent lessons (last N H3 headers + first body line)
# ---------------------------------------------------------------------------


_LESSON_PREFIX_RE = re.compile(r"^\*\*[^*]+\*\*:\s*")


def _top_lessons(path: Path, n: int = 3) -> list[dict]:
    """Return up to ``n`` most recent lessons as ``[{title, gist}, ...]``.

    "Most recent" = bottom of LESSONS.md (lessons are appended). Each
    entry carries the ``### `` heading text and the first non-empty
    body line as a gist. Strips conventional ``**Context**:`` /
    ``**Learning**:`` / ``**Rule**:`` bold prefixes so the dashboard
    reads cleanly; truncates to 120 chars.
    """
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    lines = text.splitlines()
    lessons: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("### "):
            title = line[4:].strip()
            gist = ""
            for j in range(i + 1, min(i + 8, len(lines))):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                if candidate.startswith("### "):
                    break
                gist = _LESSON_PREFIX_RE.sub("", candidate)
                break
            lessons.append({"title": title, "gist": gist[:120]})
        i += 1
    return lessons[-n:]


# ---------------------------------------------------------------------------
# CONSTITUTION mission (one-liner)
# ---------------------------------------------------------------------------


def _constitution_mission(path: Path) -> str | None:
    """Return the first sentence of ``## Mission`` section, or None.

    CONSTITUTION.md is the project-identity contract (spec-131 D-131-04).
    The mission's first sentence summarises the project in one breath —
    perfect for a dashboard tagline. Read fail-open: a missing or
    malformed CONSTITUTION just drops the tagline.
    """
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = text.splitlines()
    in_mission = False
    body: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("## "):
            if in_mission:
                break
            if stripped[3:].strip().lower() == "mission":
                in_mission = True
            continue
        if in_mission and stripped:
            body.append(stripped)
        elif in_mission and body:
            break
    if not body:
        return None
    paragraph = " ".join(body)
    if "." in paragraph:
        first = paragraph.split(".", 1)[0].strip()
        return (first + ".") if first else None
    return paragraph[:140]


# ---------------------------------------------------------------------------
# Manifest summary + compatibility warnings
# ---------------------------------------------------------------------------


def _manifest_summary(manifest: dict) -> dict:
    """Surface ``providers.ides``, ``ai_providers.primary``, ``gates.mode``."""
    out: dict = {"ides": [], "ai_primary": None, "gates_mode": None}
    providers = manifest.get("providers")
    if isinstance(providers, dict):
        ides = providers.get("ides")
        if isinstance(ides, list):
            out["ides"] = [s for s in ides if isinstance(s, str)]
    ai = manifest.get("ai_providers")
    if isinstance(ai, dict):
        primary = ai.get("primary")
        if isinstance(primary, str):
            out["ai_primary"] = primary
    gates = manifest.get("gates")
    if isinstance(gates, dict):
        mode = gates.get("mode")
        if isinstance(mode, str):
            out["gates_mode"] = mode
    return out


def _compat_warnings(manifest: dict) -> list[str]:
    """Return warnings about non-default risk-relevant manifest settings.

    Today: only ``gates.mode != 'regulated'`` is flagged — the framework
    targets regulated environments (CONSTITUTION mission). Other modes
    (``prototyping``) skip Tier-2 governance checks and are acceptable
    on short-lived feature branches but should be surfaced so the
    operator knows the posture they are running under.
    """
    warnings: list[str] = []
    gates = manifest.get("gates")
    if isinstance(gates, dict):
        mode = gates.get("mode")
        if isinstance(mode, str) and mode != "regulated":
            warnings.append(
                f"gates.mode={mode!r} (Tier-2 governance skipped; "
                f"regulated mode is the framework default)"
            )
    return warnings


# ---------------------------------------------------------------------------
# Board (gh w/ timeout + stale-while-revalidate cache)
# ---------------------------------------------------------------------------


def _board_cache_path(root: Path) -> Path:
    return root / ".ai-engineering" / "runtime" / "board-cache.json"


def _read_board_cache(root: Path) -> dict | None:
    path = _board_cache_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_board_cache(root: Path, payload: dict) -> None:
    path = _board_cache_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


def _now_ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _cache_age_s(cached: dict) -> float | None:
    fetched = cached.get("fetched_at")
    if not isinstance(fetched, str):
        return None
    try:
        when = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return (datetime.now(UTC) - when).total_seconds()


_BOARD_GRAPHQL_TEMPLATES = (
    "query($endCursor: String){{"
    '{holder}(login:"{owner}"){{'
    "projectV2(number:{number}){{"
    "items(first:{page_size},after:$endCursor){{"
    "pageInfo{{hasNextPage endCursor}}"
    "nodes{{"
    'fieldValueByName(name:"Status"){{'
    "... on ProjectV2ItemFieldSingleSelectValue{{name}}"
    "}}"
    "}}"
    "}}"
    "}}"
    "}}"
    "}}"
)


def _gh_project_all_items(
    owner: str,
    number: int,
    timeout: float = BOARD_TIMEOUT_S,
    page_size: int = BOARD_PAGE_SIZE,
) -> dict | None:
    """Fetch every project item's Status via paginated GraphQL.

    Uses ``gh api graphql --paginate --slurp`` so we get accurate totals
    + per-status breakdown in a single subprocess call (~25ms/item;
    ~4.2 s wall for 430 items). Returns ``{items_total, by_status}`` or
    ``None`` when both ``organization`` and ``user`` GraphQL roots fail.
    """
    for holder in ("organization", "user"):
        query = _BOARD_GRAPHQL_TEMPLATES.format(
            holder=holder,
            owner=owner,
            number=number,
            page_size=page_size,
        )
        try:
            result = subprocess.run(
                (
                    "gh",
                    "api",
                    "graphql",
                    "--paginate",
                    "--slurp",
                    "-f",
                    f"query={query}",
                ),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if result.returncode != 0:
            continue
        try:
            pages = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
        if not isinstance(pages, list) or not pages:
            continue
        first_proj = ((pages[0].get("data") or {}).get(holder) or {}).get("projectV2")
        if not first_proj:
            continue
        by_status: dict[str, int] = {}
        total = 0
        for page in pages:
            proj = ((page.get("data") or {}).get(holder) or {}).get("projectV2") or {}
            nodes = (proj.get("items") or {}).get("nodes") or []
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                field = node.get("fieldValueByName")
                status = (field or {}).get("name") if isinstance(field, dict) else None
                if not isinstance(status, str) or not status:
                    status = "—"
                by_status[status] = by_status.get(status, 0) + 1
                total += 1
        return {"items_total": total, "by_status": by_status}
    return None


def _fetch_board_github(owner: str, number: int, timeout: float = BOARD_TIMEOUT_S) -> dict | None:
    """Single paginated GraphQL call returning total + accurate by_status."""
    items = _gh_project_all_items(owner, number, timeout=timeout)
    if items is None:
        return None
    return {
        "provider": "github",
        "owner": owner,
        "number": number,
        "items_total": items["items_total"],
        "by_status": items["by_status"],
    }


def _board_summary(root: Path, manifest: dict) -> dict:
    work_items = manifest.get("work_items")
    if not isinstance(work_items, dict):
        return {"unavailable": True, "reason": "work_items missing — run /ai-board discover"}

    provider = work_items.get("provider")

    if provider == "github":
        gp = work_items.get("github_project")
        if not isinstance(gp, dict):
            return {"provider": "github", "unavailable": True, "reason": "github_project unset"}
        owner = gp.get("owner")
        number = gp.get("number")
        if not (isinstance(owner, str) and isinstance(number, int)):
            return {"provider": "github", "unavailable": True, "reason": "github_project unset"}
        cached = _read_board_cache(root)
        age = _cache_age_s(cached) if cached else None
        if cached and age is not None and age < BOARD_CACHE_FRESH_S:
            return {**cached, "cache_state": "fresh"}
        fetched = _fetch_board_github(owner, number)
        if fetched is not None:
            payload = {**fetched, "fetched_at": _now_ts(), "cache_state": "fresh"}
            _write_board_cache(root, payload)
            return payload
        if cached and age is not None and age < BOARD_CACHE_MAX_AGE_S:
            return {**cached, "cache_state": "stale"}
        return {"provider": "github", "unavailable": True, "reason": "fetch_failed"}

    if provider == "azure_devops":
        return {
            "provider": "azure_devops",
            "unavailable": True,
            "reason": "ado_runtime_not_implemented",
        }

    if provider is None:
        return {"unavailable": True, "reason": "work_items.provider unset"}

    return {"provider": provider, "unavailable": True, "reason": "unknown_provider"}


# ---------------------------------------------------------------------------
# Markdown render
# ---------------------------------------------------------------------------


def _version_status() -> dict | None:
    """Update-available status for the dashboard, or None when unknowable.

    Reuses the CLI's single-source resolver (``resolve_latest_known`` — the
    newer of the bundled registry and the PyPI cache) so the dashboard agrees
    with ``ai-eng version`` and the inline notice. Fail-open: any import/IO
    error (e.g. ai_engineering not importable in a bare checkout) yields None so
    the dashboard renders without a version line rather than breaking.
    """
    try:
        from ai_engineering import __version__
        from ai_engineering.version import resolve_latest_known
        from ai_engineering.version.compare import is_newer

        latest = resolve_latest_known()
        if not isinstance(latest, str) or not latest:
            return None
        return {
            "installed": __version__,
            "latest": latest,
            "update_available": bool(is_newer(latest, __version__)),
        }
    except Exception:
        return None


def _render_markdown(d: dict) -> str:
    lines: list[str] = []
    name = d.get("project_name") or "(unnamed)"
    lines.append(f"## ◈ {name}")
    lines.append("")

    mission = d.get("mission")
    if mission:
        lines.append(f"> *{mission}*")

    meta = [
        f"LESSONS ({d.get('lessons_count', 0)})",
        "CONSTITUTION",
        f"manifest ({d.get('skills_total', 0)} skills, {d.get('agents_total', 0)} agents)",
        f"decisions ({d.get('active_decisions', 0)} active, {d.get('accepted_risks', 0)} risks)",
    ]
    lines.append("> " + " · ".join(meta))

    ms = d.get("manifest_summary") or {}
    stack_parts: list[str] = []
    ides = ms.get("ides") or []
    if ides:
        stack_parts.append(f"stack: {', '.join(ides)}")
    if ms.get("ai_primary"):
        stack_parts.append(f"ai: {ms['ai_primary']}")
    if ms.get("gates_mode"):
        stack_parts.append(f"gates: {ms['gates_mode']}")
    if stack_parts:
        lines.append("> " + " · ".join(stack_parts))

    state = []
    branch = d.get("branch")
    if branch:
        state.append(f"branch `{branch}`")
    lc = d.get("last_commit")
    if isinstance(lc, dict) and lc.get("sha"):
        state.append(f"last `{lc['sha']}`")
    state.append(f"events 7d: {d.get('recent_events_7d', 0)}")
    backlog = d.get("observation_backlog") or {}
    pending = int(backlog.get("pending") or 0)
    threshold = int(backlog.get("threshold") or 10)
    if pending >= threshold:
        state.append(f"**{pending} to review** → `/ai-session-watch --review`")
    elif pending:
        state.append(f"{pending} pending review")
    hh = d.get("hooks_health", "unknown")
    if hh == "unverified":
        state.append("hooks: unverified — run `regenerate-hooks-manifest.py`")
    else:
        state.append(f"hooks: {hh}")
    lines.append("> " + " · ".join(state))
    vs = d.get("version_status") or {}
    installed = vs.get("installed")
    if installed:
        if vs.get("update_available"):
            lines.append(
                f"> ◈ ai-engineering {installed} → {vs.get('latest')}"
                " · run `ai-eng version upgrade`"
            )
        else:
            lines.append(f"> ◈ ai-engineering {installed} · up to date")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("### ▸ Active Work")
    lines.append("")
    spec = d.get("active_spec")
    if isinstance(spec, dict) and (spec.get("id") or spec.get("title")):
        sid = spec.get("id") or "—"
        title = spec.get("title") or "(untitled)"
        sstate = spec.get("state") or "—"
        lines.append(f"- **Spec {sid}** — {title} · `{sstate}`")
        done = spec.get("tasks_done", 0)
        total = spec.get("tasks_total", 0)
        plan_status = (spec.get("plan_status") or "").strip()
        plan_lc = plan_status.lower()
        shipped = "shipped" in plan_lc or plan_lc in {"done", "merged", "closed"}
        if shipped and total == 0:
            lines.append(f"- **Plan** — `{plan_status}` (no active tasks)")
        else:
            marker = " ✓" if total > 0 and done == total else ""
            lines.append(f"- **Plan** — {done}/{total} tasks{marker}")
    else:
        lines.append("- no active spec — run `/ai-brainstorm`")
    lines.append("")

    lines.append("### ▸ Recent")
    lines.append("")
    commits = d.get("recent_commits") or []
    if commits:
        for c in commits:
            sha = c.get("sha", "—")
            subject = c.get("subject", "")
            lines.append(f"- `{sha}` {subject}")
    else:
        lines.append("- (no commits)")
    lines.append("")

    top = d.get("top_lessons") or []
    if top:
        lines.append("### ▸ Recent Lessons")
        lines.append("")
        for lesson in top:
            title = lesson.get("title", "")
            gist = lesson.get("gist", "")
            if gist:
                lines.append(f"- **{title}** — {gist}")
            else:
                lines.append(f"- **{title}**")
        lines.append("")

    board = d.get("board_summary") or {}
    provider = board.get("provider", "—")
    if board.get("unavailable"):
        reason = board.get("reason", "unavailable")
        header = f"### ▸ Board · {provider}" if provider != "—" else "### ▸ Board"
        lines.append(header)
        lines.append("")
        if "missing" in reason or "discover" in reason or "unset" in reason:
            lines.append(f"- {reason}")
        else:
            lines.append(f"- board unavailable ({reason})")
    else:
        owner = board.get("owner")
        number = board.get("number")
        header = f"### ▸ Board · {provider}"
        if owner and number:
            header += f" {owner}#{number}"
        lines.append(header)
        lines.append("")
        items_total = board.get("items_total", 0)
        by_status = board.get("by_status") or {}
        ordered = sorted(by_status.items(), key=lambda kv: (-kv[1], kv[0]))
        status_str = " · ".join(f"{k}: {v}" for k, v in ordered) or "(empty)"
        cache_state = board.get("cache_state", "fresh")
        cache_suffix = "" if cache_state == "fresh" else f" *(cache {cache_state})*"
        lines.append(f"- {items_total} items — {status_str}{cache_suffix}")

    pc = d.get("proposals_count", 0)
    if pc:
        lines.append("")
        lines.append("### ▸ Proposals")
        lines.append("")
        lines.append(f"- {pc} pending — run `/ai-branch-cleanup` to review")

    warnings = d.get("compat_warnings") or []
    if warnings:
        lines.append("")
        lines.append("### ⚠ Compatibility")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "`/ai-brainstorm` design · `/ai-debug` fix · `/ai-onboard` explore · `/ai-commit` save"
    )
    lines.append(
        "`/ai-review` review · `/ai-pr` ship · `/ai-test` verify · `/ai-branch-cleanup` tidy"
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Build dashboard
# ---------------------------------------------------------------------------


def build_dashboard(repo_root: Path | None = None) -> dict:
    started = time.perf_counter()
    root = repo_root or _REPO_ROOT

    manifest = _read_manifest(root)
    git_info = _read_git(root)
    spec = _read_spec(root / ".ai-engineering" / "specs" / "spec.md")
    plan = _read_plan(root / ".ai-engineering" / "specs" / "plan.md")
    recent_events = _read_recent_events(
        root / ".ai-engineering" / "state" / "framework-events.ndjson"
    )
    dashboard: dict = {
        "schema_version": SCHEMA_VERSION,
        "project_name": _project_name(manifest),
        "branch": git_info.get("branch"),
        "last_commit": git_info.get("last_commit"),
        "recent_commits": _read_recent_commits(root),
        "active_spec": (
            None
            if spec is None
            else {
                "id": spec.get("id"),
                "state": spec.get("state"),
                "title": spec.get("title"),
                "tasks_total": plan["tasks_total"],
                "tasks_done": plan["tasks_done"],
                "plan_status": plan.get("status"),
            }
        ),
        "recent_events_7d": recent_events,
        "hooks_health": _hooks_health(root),
        "lessons_count": _count_lessons(root / ".ai-engineering" / "LESSONS.md"),
        "skills_total": _count_skills(root, manifest),
        "agents_total": _count_agents(root, manifest),
        "surface_resolved": _resolved_surface_or_none(manifest),
        "active_decisions": _count_active_decisions(root),
        "accepted_risks": _count_accepted_risks(root),
        "proposals_count": _count_proposals(root),
        "board_summary": _board_summary(root, manifest),
        "observation_backlog": _count_unconsolidated_events(root),
        "top_lessons": _top_lessons(root / ".ai-engineering" / "LESSONS.md"),
        "mission": _constitution_mission(root / "CONSTITUTION.md"),
        "manifest_summary": _manifest_summary(manifest),
        "compat_warnings": _compat_warnings(manifest),
        "version_status": _version_status(),
    }

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    dashboard["elapsed_ms"] = round(elapsed_ms, 2)
    if elapsed_ms > BUDGET_MS:
        dashboard["warnings"] = ["budget_exceeded"]
    dashboard["markdown"] = _render_markdown(dashboard)
    return dashboard


def main(argv: list[str] | None = None) -> int:
    # The dashboard markdown is inherently UTF-8 (◈ brand mark, box-drawing,
    # em-dashes, →). Force a UTF-8 stdout so a legacy cp1252 console (Windows)
    # never crashes with UnicodeEncodeError. Fail-open if reconfigure is absent.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="session_bootstrap",
        description="Emit /ai-start dashboard (deterministic, <3s incl. board).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Override repo root (default: resolved from script location).",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help=(
            "Output format. Default 'json'; 'markdown' prints the "
            "ready-to-display dashboard so the IDE agent never has to "
            "re-derive any field."
        ),
    )
    args = parser.parse_args(argv)
    dashboard = build_dashboard(args.repo_root)
    if args.format == "markdown":
        md = dashboard.get("markdown", "")
        sys.stdout.write(md)
        if not md.endswith("\n"):
            sys.stdout.write("\n")
    else:
        sys.stdout.write(json.dumps(dashboard, indent=2, sort_keys=True))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
