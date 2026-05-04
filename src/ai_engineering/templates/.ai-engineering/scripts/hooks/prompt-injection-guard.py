#!/usr/bin/env python3
"""PreToolUse hook: scan tool inputs for prompt injection patterns + IOC matches.

Blocks CRITICAL injection matches (exit 2), warns on HIGH matches (exit 0).
Applies to Bash, Write, Edit, and MultiEdit tools.

spec-105 G-12: ``ai-eng risk accept`` and ``ai-eng risk accept-all`` are
explicitly whitelisted because their inputs (gate-findings.json fixtures)
intentionally embed rule names like ``aws-access-token`` /
``stripe-key`` / etc. that the injection-pattern set classifies as
CRITICAL. Whitelisted invocations bypass the pattern scan but still emit
a telemetry event so the bypass is auditable.

spec-107 D-107-05/06/07 (Phase 4): the hook also matches tool inputs
against a vendored IOC catalog (``.ai-engineering/references/iocs.json``)
and emits a 3-valued verdict per IOC match:

- ``allow``: no IOC match (default, fast path).
- ``deny``: IOC match without an active risk-acceptance — blocks the tool
  call (exit 2) with a remediation banner.
- ``warn``: IOC match WITH an active risk-acceptance for the canonical
  ``finding_id = sentinel-<category>-<pattern_normalized>`` — execution is
  permitted but a telemetry event is emitted so the bypass is auditable.

The IOC loader is fail-open: missing or corrupt ``iocs.json`` returns an
empty dict, which downstream evaluator treats as "no IOC layer active"
(``allow``-only) so a missing catalog never crashes the host.

The hook is intentionally stdlib-only (no ``ai_engineering.*`` imports)
mirroring the spec-105/spec-107 mcp-health.py contract — direct raw-JSON
parsing of decision-store.json keeps the hook independent of the
installer's runtime.
"""

import contextlib
import hashlib
import json
import os
import re
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from _lib import risk_accumulator
from _lib.audit import is_debug_mode, passthrough_stdin
from _lib.hook_common import get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.injection_patterns import PATTERNS
from _lib.observability import (
    emit_control_outcome,
    emit_framework_error,
    emit_framework_operation,
)

# spec-120 follow-up: PRISM-style risk accumulator wiring. Disable
# entirely with ``AIENG_RISK_ACCUMULATOR_DISABLED=1`` (e.g. tests that
# do not want risk-state.json side effects).
RISK_DISABLED = (os.environ.get("AIENG_RISK_ACCUMULATOR_DISABLED") or "").strip() == "1"
_RISK_COMPONENT = "hook.prompt-injection-guard"


def _apply_risk(
    project_root: Path,
    *,
    session_id: str | None,
    severity: str,
    ioc_id: str,
    correlation_id: str,
) -> None:
    """Add a finding to the per-session risk accumulator and act on the threshold.

    Pipeline:
    1. ``risk_accumulator.add(...)`` to bump the running score (writes
       ``runtime/risk-score.json``).
    2. ``risk_accumulator.threshold_action(...)`` maps the new score
       to one of ``silent | warn | block | force_stop``.
    3. ``warn`` emits a ``framework_operation`` (``risk_warn``) so the
       audit chain records the elevation. The hook does NOT block.
    4. ``block`` emits a ``framework_error`` (``risk_threshold_block``)
       and exits 2 — Claude Code interprets that as deny.
    5. ``force_stop`` emits ``risk_force_stop``, writes a ``decision:
       block`` JSON to stdout (so the user sees a deterministic
       termination message), and exits 2.

    Defensive: any exception inside the accumulator (corrupt state,
    write race) is swallowed — the host hook MUST keep running.
    Disable with ``AIENG_RISK_ACCUMULATOR_DISABLED=1``.
    """
    if RISK_DISABLED:
        return
    try:
        state = risk_accumulator.add(
            project_root,
            session_id=session_id or "unknown",
            severity=severity,
            ioc_id=ioc_id,
        )
        action = risk_accumulator.threshold_action(state.score)
    except Exception:
        return  # fail-open: never let risk telemetry break the host hook.
    if action == "warn":
        with contextlib.suppress(Exception):
            emit_framework_operation(
                project_root,
                operation="risk_warn",
                component=_RISK_COMPONENT,
                source="hook",
                correlation_id=correlation_id,
                metadata={"score": round(state.score, 2), "ioc_id": ioc_id},
            )
    elif action == "block":
        with contextlib.suppress(Exception):
            emit_framework_error(
                project_root,
                engine="ai_engineering",
                component=_RISK_COMPONENT,
                error_code="risk_threshold_block",
                source="hook",
                session_id=session_id,
                correlation_id=correlation_id,
                metadata={"score": round(state.score, 2), "ioc_id": ioc_id},
            )
        sys.exit(2)
    elif action == "force_stop":
        with contextlib.suppress(Exception):
            emit_framework_error(
                project_root,
                engine="ai_engineering",
                component=_RISK_COMPONENT,
                error_code="risk_force_stop",
                source="hook",
                session_id=session_id,
                correlation_id=correlation_id,
                metadata={"score": round(state.score, 2), "ioc_id": ioc_id},
            )
        sys.stdout.write(
            json.dumps(
                {
                    "decision": "block",
                    "additionalContext": (
                        f"Session terminated — accumulated risk "
                        f"{state.score:.1f} exceeds force_stop threshold."
                    ),
                }
            )
        )
        sys.stdout.flush()
        sys.exit(2)


_GUARDED_TOOLS = {"Bash", "Write", "Edit", "MultiEdit"}
_MIN_CONTENT_LEN = 10
_MAX_CONTENT_LEN = 4000

# spec-107 D-107-05: canonical IOC categories spec-mandated. The vendored
# upstream catalog also exposes ``suspicious_network`` and
# ``dangerous_commands`` aliases; both names index the same payload.
_IOC_CATEGORIES = ("sensitive_paths", "sensitive_env_vars", "malicious_domains", "shell_patterns")
_IOC_RELATIVE = Path(".ai-engineering") / "references" / "iocs.json"

# spec-105 G-12: commands that legitimately handle gate-findings JSON
# embedding secret-related rule names. Match by argv[0..2] joined with
# single spaces. Add new entries with care -- every whitelisted command
# bypasses the injection-pattern scan.
WHITELISTED_COMMANDS = frozenset(
    {
        "ai-eng risk accept-all",
        "ai-eng risk accept",
    }
)


def _extract_content(tool_name: str, tool_input: dict) -> str:
    """Extract scannable content from tool input based on tool type."""
    if tool_name in ("Write", "MultiEdit"):
        return tool_input.get("content", "")
    if tool_name == "Edit":
        return tool_input.get("new_string", "")
    if tool_name == "Bash":
        return tool_input.get("command", "")
    return ""


def _parsed_command_prefix(command: str) -> str | None:
    """Return the first three argv tokens joined with single spaces.

    Used to match against ``WHITELISTED_COMMANDS``. Returns ``None`` when
    parsing fails (malformed quoting) or the command has fewer than two
    tokens (top-level only -- never enough to be a whitelisted invocation).
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) < 2:
        return None
    return " ".join(tokens[:3])


def _is_whitelisted(tool_name: str, content: str) -> str | None:
    """Return the matched whitelist key, or ``None`` if not whitelisted.

    Only Bash invocations can be whitelisted; Write/Edit/MultiEdit always
    pass through the pattern scan because the whitelist contract is
    ``ai-eng risk *`` CLI invocations -- not file edits.
    """
    if tool_name != "Bash":
        return None
    prefix = _parsed_command_prefix(content)
    if prefix is None:
        return None
    if prefix in WHITELISTED_COMMANDS:
        return prefix
    return None


def _is_test_fixture_target(tool_name: str, tool_input: dict) -> str | None:
    """Return the file_path when Write/Edit targets a test fixture, else None.

    spec-107 D-107-06: IOC patterns embedded in test files (under ``tests/``,
    ``test_*.py``, or fixture directories) are legitimate. Without this
    bypass the hook would block writing IOC test fixtures via the very
    same patterns those tests exist to validate. The bypass emits a
    telemetry event so the audit trail records every test-fixture-bypassed
    write, preserving the spec-105 G-12 auditable-bypass contract.
    """
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return None
    file_path = tool_input.get("file_path") or ""
    if not isinstance(file_path, str) or not file_path:
        return None
    # Match repo-relative tests/ trees and pytest-style filenames.
    parts = Path(file_path).parts
    if "tests" in parts or "test_data" in parts or "fixtures" in parts:
        return file_path
    name = Path(file_path).name
    if name.startswith("test_") or name.endswith("_test.py"):
        return file_path
    return None


# ---------------------------------------------------------------------------
# spec-107 D-107-05/06/07: IOC catalog loading + 3-valued evaluation
# ---------------------------------------------------------------------------


def _ioc_catalog_path(project_root: Path) -> Path:
    """Resolve the vendored IOC catalog path."""
    return project_root / _IOC_RELATIVE


def load_iocs(project_root: Path) -> dict[str, Any]:
    """Load the vendored IOC catalog (fail-open).

    Returns an empty dict when the file is missing or corrupt — downstream
    callers treat empty as "no IOC layer active" so a missing or broken
    catalog never blocks the host. This is the deliberate fail-open
    posture: spec-107 D-107-05 prefers availability over secret-leak
    blocking when the catalog itself is absent (e.g. fresh checkout).
    """
    path = _ioc_catalog_path(project_root)
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _decision_store_path(project_root: Path) -> Path:
    """Resolve the project decision-store.json location."""
    return project_root / ".ai-engineering" / "state" / "decision-store.json"


def _parse_decision_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp; return None when missing/unparseable.

    ``None`` means "no expiry" (matches Pydantic Decision.expires_at
    semantics where None is perpetual).
    """
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_pattern(pattern: str) -> str:
    """Lower-case + replace `/` with `_` for canonical finding-id slug.

    spec-107 D-107-07: the canonical sentinel finding_id format is
    ``f"sentinel-{category}-{pattern_normalized}"``. Pattern normalization
    ensures idempotent lookups even when upstream IOC patterns contain
    path separators or upper-case characters.
    """
    return pattern.lower().replace("/", "_")


def canonical_finding_id(category: str, pattern: str) -> str:
    """Build the canonical sentinel finding_id used for risk-accept lookup."""
    return f"sentinel-{category}-{_normalize_pattern(pattern)}"


def find_active_risk_acceptance(
    project_root: Path,
    finding_id: str,
    *,
    now: datetime | None = None,
) -> dict | None:
    """Look up an active risk-acceptance entry by ``finding_id``.

    Mirrors the spec-105 ``find_active_risk_acceptance`` lookup primitive
    used by ``mcp-health.py`` (spec-107 D-107-01). Operates on raw JSON
    because the hook intentionally avoids ``ai_engineering.*`` imports
    (stdlib-only contract per ``_lib/observability.py`` header).

    A match must satisfy ALL of:
    - ``finding_id`` (or alias ``findingId``) equals the requested id
    - ``status`` equals ``"active"`` (case-insensitive)
    - ``risk_category`` (or ``riskCategory``) equals ``"risk-acceptance"``
    - ``expires_at`` (or ``expiresAt``) is absent OR strictly greater than ``now``

    Returns the matching decision dict, or ``None``. Failures opening or
    parsing the store are treated as "no acceptance" — the hook never
    crashes the host on malformed state.
    """
    reference = now or datetime.now(UTC)
    store_path = _decision_store_path(project_root)
    if not store_path.exists():
        return None
    try:
        raw = store_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        return None
    for entry in decisions:
        if not isinstance(entry, dict):
            continue
        entry_finding = entry.get("finding_id") or entry.get("findingId")
        if entry_finding != finding_id:
            continue
        status = (entry.get("status") or "").lower()
        if status != "active":
            continue
        risk_category = (entry.get("risk_category") or entry.get("riskCategory") or "").lower()
        if risk_category != "risk-acceptance":
            continue
        expires_at = _parse_decision_timestamp(entry.get("expires_at") or entry.get("expiresAt"))
        if expires_at is not None and expires_at <= reference:
            continue
        return entry
    return None


def _expand_user_path(pattern: str) -> str:
    """Expand `~` in IOC path patterns to a regex-friendly home prefix.

    The vendored catalog uses ``~/`` to denote the user's home directory.
    For matching against arbitrary tool-call content we match either the
    literal `~/` form or the expanded `$HOME/` form so the same pattern
    catches both representations a tool may use.
    """
    return pattern


def _category_patterns(catalog: dict[str, Any], category: str) -> list[tuple[str, str]]:
    """Return ``[(kind, pattern), ...]`` tuples for a category.

    ``kind`` is one of ``"literal"`` (substring match) or ``"regex"``
    (re.search match). Schema mapping per upstream
    ``claude-mcp-sentinel/references/iocs.json`` (preserved verbatim):

    - ``sensitive_paths`` / ``sensitive_env_vars`` → ``patterns`` is
      LITERAL (path or env-var names); ``regex_patterns`` is REGEX.
    - ``malicious_domains`` (alias ``suspicious_network``) →
      ``known_malicious_domains`` (list[dict|str]) is LITERAL,
      ``suspicious_tlds`` / ``pastebin_style`` is LITERAL,
      ``suspicious_patterns`` is REGEX.
    - ``shell_patterns`` (alias ``dangerous_commands``) → ``patterns``
      is REGEX. There is no literal substring set for shell patterns.
    """
    section = catalog.get(category)
    if not isinstance(section, dict):
        return []
    out: list[tuple[str, str]] = []
    # `patterns` semantics differ by category (upstream schema quirk):
    # shell_patterns/dangerous_commands ships regex; the rest ship literals.
    patterns_kind = "regex" if category in ("shell_patterns", "dangerous_commands") else "literal"
    base_patterns = section.get("patterns") or []
    if isinstance(base_patterns, list):
        for p in base_patterns:
            if isinstance(p, str) and p:
                out.append((patterns_kind, p))
    regexes = section.get("regex_patterns") or []
    if isinstance(regexes, list):
        for p in regexes:
            if isinstance(p, str) and p:
                out.append(("regex", p))
    # malicious_domains-specific schema: nested dicts + alias lists.
    domains = section.get("known_malicious_domains") or []
    if isinstance(domains, list):
        for entry in domains:
            if isinstance(entry, dict):
                domain = entry.get("domain")
                if isinstance(domain, str) and domain:
                    out.append(("literal", domain))
            elif isinstance(entry, str) and entry:
                out.append(("literal", entry))
    for alias_key in ("suspicious_tlds", "pastebin_style"):
        alias = section.get(alias_key) or []
        if isinstance(alias, list):
            for p in alias:
                if isinstance(p, str) and p:
                    out.append(("literal", p))
    sus_patterns = section.get("suspicious_patterns") or []
    if isinstance(sus_patterns, list):
        for p in sus_patterns:
            if isinstance(p, str) and p:
                out.append(("regex", p))
    return out


def _match_pattern(content: str, kind: str, pattern: str) -> bool:
    """Return True when ``content`` matches ``pattern`` per ``kind`` rules."""
    if kind == "literal":
        # Path patterns starting with ~/ are also matched against the
        # literal form embedded inline (e.g. "cat ~/.ssh/id_rsa").
        return pattern in content or _expand_user_path(pattern) in content
    if kind == "regex":
        try:
            return re.search(pattern, content) is not None
        except re.error:
            return False
    return False


def evaluate_against_iocs(
    project_root: Path,
    content: str,
    *,
    catalog: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate ``content`` against the vendored IOC catalog.

    Returns a dict with at minimum:
    - ``verdict``: one of ``"allow"`` | ``"deny"`` | ``"warn"``
    - ``matches``: list of dicts with keys
      ``category``, ``pattern``, ``finding_id``, ``kind``, ``accepted``,
      ``dec_id``
    - ``reason``: human-readable string when verdict != allow

    Decision logic:
    - No IOC match → ``allow``.
    - At least one IOC match without an active risk-acceptance for its
      ``finding_id`` → ``deny``.
    - All IOC matches have active risk-acceptance entries → ``warn``
      (allow execution + every match emits a telemetry event so the
      audit trail records the bypass).

    The evaluator is pure (no I/O when ``catalog`` is supplied); pass a
    pre-loaded catalog from tests to avoid filesystem overhead.
    """
    cat = catalog if catalog is not None else load_iocs(project_root)
    if not cat:
        return {"verdict": "allow", "matches": [], "reason": ""}

    matches: list[dict[str, Any]] = []
    any_unaccepted = False
    for category in _IOC_CATEGORIES:
        for kind, pattern in _category_patterns(cat, category):
            if not _match_pattern(content, kind, pattern):
                continue
            finding = canonical_finding_id(category, pattern)
            decision = find_active_risk_acceptance(project_root, finding, now=now)
            accepted = decision is not None
            if not accepted:
                any_unaccepted = True
            matches.append(
                {
                    "category": category,
                    "pattern": pattern,
                    "kind": kind,
                    "finding_id": finding,
                    "accepted": accepted,
                    "dec_id": decision.get("id") or decision.get("decision_id")
                    if decision
                    else None,
                }
            )
    if not matches:
        return {"verdict": "allow", "matches": [], "reason": ""}
    if any_unaccepted:
        names = ", ".join(f"{m['category']}:{m['pattern']}" for m in matches if not m["accepted"])
        return {
            "verdict": "deny",
            "matches": matches,
            "reason": (
                f"Sentinel IOC match: {names}. "
                f"To accept this risk: ai-eng risk accept --finding-id "
                f"{matches[0]['finding_id']} --severity medium "
                '--justification "..." --spec spec-107'
            ),
        }
    # All matches accepted via active DEC → warn (allow + audit).
    accepted_names = ", ".join(f"{m['category']}:{m['pattern']}" for m in matches)
    return {
        "verdict": "warn",
        "matches": matches,
        "reason": f"Sentinel IOC match accepted via DEC: {accepted_names}",
    }


def _emit_ioc_outcomes(project_root: Path, tool_name: str, result: dict[str, Any]) -> None:
    """Emit one control_outcome event per IOC match.

    - verdict=deny → one ``ioc-match-deny`` event per unaccepted match.
    - verdict=warn → one ``ioc-match-allowed-via-dec`` event per accepted
      match (D-107-06 mandates per-match emission for compliance trace).
    """
    verdict = result.get("verdict")
    matches = result.get("matches") or []
    for match in matches:
        if not isinstance(match, dict):
            continue
        accepted = match.get("accepted")
        if verdict == "deny" and not accepted:
            control = "ioc-match-deny"
            outcome = "failure"
        elif verdict == "warn" and accepted:
            control = "ioc-match-allowed-via-dec"
            outcome = "warning"
        else:
            continue
        meta = {
            "tool": tool_name,
            "category": match.get("category"),
            "pattern": match.get("pattern"),
            "finding_id": match.get("finding_id"),
            "kind": match.get("kind"),
            "dec_id": match.get("dec_id"),
        }
        with contextlib.suppress(Exception):
            emit_control_outcome(
                project_root,
                category="mcp-sentinel",
                control=control,
                component="hook.prompt-injection-guard",
                outcome=outcome,
                source="hook",
                metadata=meta,
            )
        # spec-120 #17: feed risk accumulator. Severity inferred from the
        # match category. CRITICAL on deny (un-accepted), HIGH otherwise.
        finding_id = match.get("finding_id") or match.get("pattern") or "unknown"
        severity = "CRITICAL" if (verdict == "deny" and not accepted) else "HIGH"
        with contextlib.suppress(Exception):
            _apply_risk(
                project_root,
                session_id=None,
                severity=severity,
                ioc_id=str(finding_id),
                correlation_id=get_correlation_id(),
            )


def main() -> None:
    ctx = get_hook_context()
    tool_name = ctx.data.get("tool_name", "")

    if tool_name not in _GUARDED_TOOLS:
        passthrough_stdin(ctx.data)
        return

    tool_input = ctx.data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}

    content = _extract_content(tool_name, tool_input)

    if len(content) < _MIN_CONTENT_LEN:
        passthrough_stdin(ctx.data)
        return

    # spec-105 G-12: short-circuit pattern scan for whitelisted CLI
    # invocations. The findings.json payload embeds rule names like
    # ``aws-access-token`` / ``stripe-key`` that the CRITICAL pattern set
    # would otherwise flag. Emit telemetry so the bypass remains auditable.
    matched_command = _is_whitelisted(tool_name, content)
    if matched_command is not None:
        argv_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        emit_control_outcome(
            ctx.project_root,
            category="security",
            control="prompt-guard-whitelisted",
            component="hook.prompt-injection-guard",
            outcome="success",
            source="hook",
            metadata={
                "tool": tool_name,
                "command": matched_command,
                "argv_hash": argv_hash,
            },
        )
        passthrough_stdin(ctx.data)
        return

    scan_content = content[:_MAX_CONTENT_LEN]

    # spec-107 D-107-06: Write/Edit operations targeting test fixtures
    # legitimately embed IOC patterns (the catalog itself, IOC test
    # fixtures, etc.). Bypass the IOC scan for those targets but emit a
    # telemetry event so every bypass is auditable.
    fixture_path = _is_test_fixture_target(tool_name, tool_input)
    if fixture_path is not None:
        argv_hash = hashlib.sha256(scan_content.encode("utf-8")).hexdigest()
        with contextlib.suppress(Exception):
            emit_control_outcome(
                ctx.project_root,
                category="security",
                control="ioc-scan-test-fixture-bypass",
                component="hook.prompt-injection-guard",
                outcome="success",
                source="hook",
                metadata={
                    "tool": tool_name,
                    "file_path": fixture_path,
                    "content_hash": argv_hash,
                },
            )
        passthrough_stdin(ctx.data)
        return

    # spec-107 D-107-05/06/07: IOC catalog evaluation. Runs BEFORE the
    # injection-pattern scan so a sentinel-classified payload never
    # reaches the (looser) prompt-injection layer. Fail-open: missing
    # catalog returns verdict=allow + matches=[] which is a no-op.
    ioc_result = evaluate_against_iocs(ctx.project_root, scan_content)
    if ioc_result["verdict"] in ("deny", "warn"):
        _emit_ioc_outcomes(ctx.project_root, tool_name, ioc_result)
    if ioc_result["verdict"] == "deny":
        feedback = {
            "decision": "block",
            "reason": ioc_result["reason"],
        }
        sys.stdout.write(json.dumps(feedback))
        sys.stdout.flush()
        sys.exit(2)
    if ioc_result["verdict"] == "warn":
        sys.stderr.write(
            f"[prompt-injection-guard] WARN sentinel IOC accepted via risk-acceptance: "
            f"{ioc_result['reason']}\n"
        )
        sys.stderr.flush()

    critical_matches = []
    high_matches = []

    for pattern in PATTERNS:
        if pattern.regex.search(scan_content):
            match_info = {"pattern": pattern.name, "severity": pattern.severity}
            if pattern.severity == "CRITICAL":
                critical_matches.append(match_info)
            else:
                high_matches.append(match_info)

    all_matches = critical_matches + high_matches

    if all_matches:
        emit_control_outcome(
            ctx.project_root,
            category="security",
            control="prompt-injection-guard",
            component="hook.prompt-injection-guard",
            outcome="failure" if critical_matches else "warning",
            source="hook",
            metadata={
                "tool": tool_name,
                "matches": all_matches,
                "action": "blocked" if critical_matches else "warned",
            },
        )

        if is_debug_mode():
            debug_log = ctx.project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
            try:
                timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                names = ", ".join(m["pattern"] for m in all_matches)
                with open(debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] injection scan: tool={tool_name} matches=[{names}]\n")
            except Exception:
                pass

    if critical_matches:
        pattern_names = ", ".join(m["pattern"] for m in critical_matches)
        feedback = {
            "decision": "block",
            "reason": (
                f"Prompt injection detected: {pattern_names}. "
                "This tool call has been blocked for security. "
                "Please rephrase your request without injection patterns."
            ),
        }
        sys.stdout.write(json.dumps(feedback))
        sys.stdout.flush()
        sys.exit(2)

    if high_matches:
        pattern_names = ", ".join(m["pattern"] for m in high_matches)
        sys.stderr.write(
            f"[prompt-injection-guard] WARNING: Suspicious pattern detected: {pattern_names}. "
            "Allowing tool call but logging for review.\n"
        )
        sys.stderr.flush()

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component="hook.prompt-injection-guard",
        hook_kind="pre-tool-use",
        script_path=__file__,
    )
