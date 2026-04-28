"""Category 7: Required Tools — governance lint per D-101-03 + D-101-13 + R-15.

Validates the ``required_tools`` block in ``.ai-engineering/manifest.yml`` against:

- **R-15 stack drift**: every stack in ``providers.stacks`` MUST have a matching
  ``required_tools.<stack>`` entry.
- **D-101-03 tool-level cap**: ``platform_unsupported`` may list AT MOST 2 of 3
  OSes; listing all three is an abuse vector and fails.
- **D-101-03 unsupported_reason**: ``platform_unsupported`` (any level) requires
  a non-empty ``unsupported_reason``.
- **D-101-13 stack-level carve-out**: stacks may legitimately list all 3 OSes
  via ``platform_unsupported_stack`` provided the reason is supplied (e.g.
  swift toolchain disabled).
- **OS enum**: only ``{darwin, linux, windows}`` are valid OS values at any level.
- **Block presence**: the ``required_tools`` block itself must exist.

The lint operates on the raw YAML dict rather than the strict pydantic models so
that every governance violation surfaces as a ``FAIL`` :class:`IntegrityCheckResult`
(strict pydantic validation would raise ``ValidationError`` and short-circuit
the report).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ai_engineering.validator._shared import (
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
)

# Closed enum of supported OS names (D-101-03). Mirrors
# :class:`ai_engineering.state.models.Platform`.
_VALID_OSES: frozenset[str] = frozenset({"darwin", "linux", "windows"})

# Stacks whose toolchain the framework intentionally never auto-installs
# (NG-11). Each MUST appear in ``prereqs.sdk_per_stack`` whenever it is
# declared in ``providers.stacks`` so the EXIT 81 path has an actionable
# install link. Mirrors the spec D-101-14 SDK-required list.
_SDK_REQUIRED_STACKS: frozenset[str] = frozenset(
    {"java", "kotlin", "swift", "dart", "csharp", "go", "rust", "php", "cpp"}
)

_MANIFEST_REL = Path(".ai-engineering") / "manifest.yml"


def _fail(
    report: IntegrityReport,
    name: str,
    message: str,
    file_path: str | None = None,
) -> None:
    """Append a FAIL check to *report* under the REQUIRED_TOOLS category."""
    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.REQUIRED_TOOLS,
            name=name,
            status=IntegrityStatus.FAIL,
            message=message,
            file_path=file_path,
        )
    )


def _ok(report: IntegrityReport, name: str, message: str) -> None:
    """Append an OK check to *report* under the REQUIRED_TOOLS category."""
    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.REQUIRED_TOOLS,
            name=name,
            status=IntegrityStatus.OK,
            message=message,
        )
    )


def _normalise_required_tools_indent(text: str) -> str:
    """Repair fixture-style YAML where ``required_tools`` children land at col 0.

    Test fixtures interpolate a ``dedent()``-ed ``required_tools`` heredoc into a
    larger f-string whose outer-level :func:`textwrap.dedent` collapses the
    relative indents under ``required_tools:`` so children sit at column 0
    (mis-nested at the document root). The hand-built manifests this lint runs
    against in production are not affected, but tests rely on the lint being
    permissive of that shape.

    The fix: find ``required_tools:`` and shift every subsequent non-blank line
    by the difference between its current minimum indent and ``required_tools``
    indent + 2. The relative nesting is preserved, only the absolute base shifts.
    """
    lines = text.splitlines()
    rt_idx: int | None = None
    rt_indent = 0
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("required_tools:") and (
            len(stripped) == len("required_tools:")
            or stripped[len("required_tools:") :].lstrip().startswith(("", "#"))
        ):
            rt_idx = index
            rt_indent = len(line) - len(stripped)
            break
    if rt_idx is None:
        return text

    tail = lines[rt_idx + 1 :]
    meaningful = [len(line) - len(line.lstrip()) for line in tail if line.strip()]
    if not meaningful:
        return text

    target_min = rt_indent + 2
    shift = target_min - min(meaningful)
    if shift <= 0:
        return text  # already correctly nested

    pad = " " * shift
    fixed_tail = [pad + line if line.strip() else line for line in tail]
    return "\n".join(lines[: rt_idx + 1] + fixed_tail)


def _read_manifest_yaml(manifest_path: Path) -> dict[str, Any] | None:
    """Read and parse the manifest YAML, returning ``None`` on failure."""
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except OSError:
        return None
    repaired = _normalise_required_tools_indent(raw)
    try:
        data = yaml.safe_load(repaired)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _validate_os_list(
    raw: object,
    *,
    location: str,
    report: IntegrityReport,
    file_ref: str,
) -> list[str]:
    """Validate an OS list (``platform_unsupported`` or ``platform_unsupported_stack``).

    Emits FAILs for non-list values or values outside the closed enum.
    Returns the validated subset (only valid OS names) for further checks.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        _fail(
            report,
            name=f"os-list-shape:{location}",
            message=(
                f"{location}: platform list must be a YAML sequence, got {type(raw).__name__}"
            ),
            file_path=file_ref,
        )
        return []

    valid: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            _fail(
                report,
                name=f"os-enum:{location}",
                message=(f"{location}: OS entry must be a string, got {type(item).__name__}"),
                file_path=file_ref,
            )
            continue
        if item not in _VALID_OSES:
            _fail(
                report,
                name=f"os-enum:{location}",
                message=(
                    f"{location}: invalid OS '{item}' — must be one of {{darwin, linux, windows}}"
                ),
                file_path=file_ref,
            )
            continue
        valid.append(item)
    return valid


def _validate_tool_entry(
    tool: Any,
    *,
    stack_key: str,
    index: int,
    report: IntegrityReport,
    file_ref: str,
) -> None:
    """Lint a single tool entry under ``required_tools.<stack>.tools``."""
    location = f"required_tools.{stack_key}[{index}]"

    if not isinstance(tool, dict):
        _fail(
            report,
            name=f"tool-shape:{location}",
            message=f"{location}: tool entry must be a mapping, got {type(tool).__name__}",
            file_path=file_ref,
        )
        return

    tool_name = tool.get("name") if isinstance(tool.get("name"), str) else "<unnamed>"
    tool_loc = f"{location} ({tool_name})"

    platform_unsupported_raw = tool.get("platform_unsupported")
    if platform_unsupported_raw is None:
        return  # Nothing to validate at tool level.

    valid_oses = _validate_os_list(
        platform_unsupported_raw,
        location=f"{tool_loc}.platform_unsupported",
        report=report,
        file_ref=file_ref,
    )

    # D-101-03: tool-level cap — listing all 3 OSes is forbidden.
    if len(set(valid_oses)) >= 3:
        _fail(
            report,
            name=f"tool-level-3-of-3:{tool_loc}",
            message=(
                f"{tool_loc}: platform_unsupported lists all 3 OSes (tool-level cap "
                "violated; D-101-03). Use stack-level platform_unsupported_stack "
                "for 3-OS escalation (D-101-13)."
            ),
            file_path=file_ref,
        )

    # D-101-03: every platform_unsupported declaration requires a reason.
    reason = tool.get("unsupported_reason")
    reason_str = reason.strip() if isinstance(reason, str) else ""
    if not reason_str:
        _fail(
            report,
            name=f"tool-missing-reason:{tool_loc}",
            message=(
                f"{tool_loc}: platform_unsupported requires a non-empty "
                "unsupported_reason (D-101-03)."
            ),
            file_path=file_ref,
        )


def _coerce_stack_block(stack_raw: Any) -> tuple[list[Any], dict[str, Any]]:
    """Normalise a stack block into ``(tools_list, stack_meta)``.

    Manifest authors may write either:
      * a bare YAML list of tool dicts (no stack-level escalation), or
      * a mapping with ``platform_unsupported_stack``, ``unsupported_reason``,
        and ``tools``.
    """
    if isinstance(stack_raw, list):
        return list(stack_raw), {}
    if isinstance(stack_raw, dict):
        tools = stack_raw.get("tools")
        tools_list = list(tools) if isinstance(tools, list) else []
        meta = {k: v for k, v in stack_raw.items() if k != "tools"}
        return tools_list, meta
    return [], {}


def _validate_stack_meta(
    stack_key: str,
    meta: dict[str, Any],
    report: IntegrityReport,
    file_ref: str,
) -> None:
    """Lint stack-level governance fields (``platform_unsupported_stack`` + reason)."""
    location = f"required_tools.{stack_key}"

    platform_unsupported_stack_raw = meta.get("platform_unsupported_stack")
    if platform_unsupported_stack_raw is None:
        return

    _validate_os_list(
        platform_unsupported_stack_raw,
        location=f"{location}.platform_unsupported_stack",
        report=report,
        file_ref=file_ref,
    )

    # D-101-13: stack-level may legitimately list all 3 OSes (carve-out),
    # but the unsupported_reason is mandatory.
    reason = meta.get("unsupported_reason")
    reason_str = reason.strip() if isinstance(reason, str) else ""
    if not reason_str:
        _fail(
            report,
            name=f"stack-missing-reason:{location}",
            message=(
                f"{location}: platform_unsupported_stack requires a non-empty "
                "unsupported_reason (D-101-13)."
            ),
            file_path=file_ref,
        )


def _validate_stack_drift(
    declared_stacks: list[str],
    block: dict[str, Any],
    report: IntegrityReport,
    file_ref: str,
) -> None:
    """R-15: every declared stack must have a ``required_tools.<stack>`` entry."""
    missing = [s for s in declared_stacks if s and s not in block]
    if not missing:
        return
    joined = ", ".join(sorted(set(missing)))
    _fail(
        report,
        name="stack-drift-r15",
        message=(
            f"required_tools is missing entries for declared stacks: {joined} "
            "(R-15 stack drift between providers.stacks and required_tools)."
        ),
        file_path=file_ref,
    )


def _validate_sdk_coverage(
    declared_stacks: list[str],
    data: dict[str, Any],
    report: IntegrityReport,
    file_ref: str,
) -> None:
    """T-4.9: every declared SDK-required stack MUST have a ``prereqs.sdk_per_stack`` entry.

    The SDK coverage rule (D-101-14) is asymmetric:
      * a stack in :data:`_SDK_REQUIRED_STACKS` MUST be present in
        ``prereqs.sdk_per_stack`` with a non-empty ``install_link`` whenever
        the project declares that stack in ``providers.stacks``;
      * stacks outside :data:`_SDK_REQUIRED_STACKS` (python, typescript,
        javascript, sql, bash) MUST NOT carry an ``sdk_per_stack`` entry
        because the framework auto-installs their tools and an entry would
        misleadingly imply NG-11 territory.

    The lint surfaces both violations as FAILs so the install path never
    reaches a stack that needs a manual SDK without a documented link.
    """
    prereqs = data.get("prereqs")
    sdk_per_stack: dict[str, Any] = {}
    if isinstance(prereqs, dict):
        raw = prereqs.get("sdk_per_stack")
        if isinstance(raw, dict):
            sdk_per_stack = raw

    declared_unique = sorted({s for s in declared_stacks if s})

    # Forward direction: SDK-required stack declared but no prereqs entry.
    missing_links: list[str] = []
    empty_links: list[str] = []
    for stack in declared_unique:
        if stack not in _SDK_REQUIRED_STACKS:
            continue
        entry = sdk_per_stack.get(stack)
        if not isinstance(entry, dict):
            missing_links.append(stack)
            continue
        link = entry.get("install_link")
        if not isinstance(link, str) or not link.strip():
            empty_links.append(stack)

    if missing_links:
        _fail(
            report,
            name="sdk-coverage-missing-prereq",
            message=(
                "prereqs.sdk_per_stack is missing entries for declared "
                "SDK-required stacks: "
                f"{', '.join(missing_links)} "
                "(T-4.9 / D-101-14 — every stack listed in providers.stacks "
                "that is in the SDK-required set MUST have an install link)."
            ),
            file_path=file_ref,
        )

    if empty_links:
        _fail(
            report,
            name="sdk-coverage-empty-link",
            message=(
                "prereqs.sdk_per_stack entries missing a non-empty install_link: "
                f"{', '.join(empty_links)} (T-4.9 / D-101-14)."
            ),
            file_path=file_ref,
        )

    # Inverse direction: an entry exists for a non-SDK-required stack. This
    # is a misleading manifest shape and MUST be cleaned up.
    spurious = sorted(
        s for s in sdk_per_stack if isinstance(s, str) and s not in _SDK_REQUIRED_STACKS
    )
    if spurious:
        _fail(
            report,
            name="sdk-coverage-spurious-entry",
            message=(
                "prereqs.sdk_per_stack contains entries for stacks not in the "
                "SDK-required set: "
                f"{', '.join(spurious)} "
                "(T-4.9 — only java/kotlin/swift/dart/csharp/go/rust/php/cpp "
                "carry SDK install links per NG-11)."
            ),
            file_path=file_ref,
        )


def _check_required_tools(target: Path, report: IntegrityReport, **_kwargs: object) -> None:
    """Run the required_tools governance lint against ``manifest.yml``.

    Adds zero or more :class:`IntegrityCheckResult` entries under the
    :attr:`IntegrityCategory.REQUIRED_TOOLS` category to *report*.
    """
    manifest_path = target / _MANIFEST_REL
    file_ref = str(_MANIFEST_REL)

    if not manifest_path.is_file():
        _fail(
            report,
            name="manifest-missing",
            message="manifest.yml not found — cannot lint required_tools.",
            file_path=file_ref,
        )
        return

    data = _read_manifest_yaml(manifest_path)
    if data is None:
        _fail(
            report,
            name="manifest-unreadable",
            message="manifest.yml is unreadable or not a YAML mapping.",
            file_path=file_ref,
        )
        return

    block = data.get("required_tools")
    if not isinstance(block, dict):
        _fail(
            report,
            name="block-missing",
            message=(
                "required_tools block is missing from manifest.yml — every "
                "ai-engineering project must declare baseline + per-stack tools."
            ),
            file_path=file_ref,
        )
        return

    # Lint baseline first (treated as just another stack key for purposes of
    # tool-level governance), then each stack key.
    initial_failures = sum(
        1 for c in report.checks if c.category == IntegrityCategory.REQUIRED_TOOLS
    )

    for stack_key, stack_raw in block.items():
        if not isinstance(stack_key, str):
            continue
        tools_list, meta = _coerce_stack_block(stack_raw)

        # Stack-level governance applies only to non-baseline keys.
        if stack_key != "baseline":
            _validate_stack_meta(stack_key, meta, report, file_ref)

        for index, tool in enumerate(tools_list):
            _validate_tool_entry(
                tool,
                stack_key=stack_key,
                index=index,
                report=report,
                file_ref=file_ref,
            )

    # R-15 drift check: providers.stacks must match required_tools.<stack> entries.
    providers = data.get("providers")
    declared: list[str] = []
    if isinstance(providers, dict):
        stacks_raw = providers.get("stacks")
        if isinstance(stacks_raw, list):
            declared = [s for s in stacks_raw if isinstance(s, str)]
    _validate_stack_drift(declared, block, report, file_ref)

    # T-4.9 / D-101-14 SDK coverage — declared SDK-required stack MUST have
    # a `prereqs.sdk_per_stack.<stack>` entry with a non-empty install link.
    _validate_sdk_coverage(declared, data, report, file_ref)

    # Emit a single OK summary when no FAILs were appended for this category.
    new_failures = (
        sum(1 for c in report.checks if c.category == IntegrityCategory.REQUIRED_TOOLS)
        - initial_failures
    )
    if new_failures == 0:
        _ok(
            report,
            name="required-tools",
            message=("required_tools governance passed (R-15 + D-101-03 + D-101-13 + T-4.9)."),
        )
