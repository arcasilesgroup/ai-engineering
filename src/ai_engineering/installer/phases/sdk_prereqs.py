"""SDK prereq gate -- spec-101 D-101-14.

Runs BEFORE the tools phase. Iterates the project's declared stacks,
filters to the canonical 9 SDK-required set
(:data:`ai_engineering.state.manifest.SDK_REQUIRED_STACKS`), and probes each
via :func:`ai_engineering.prereqs.sdk.probe_sdk`. Any absent SDK or
``meets_min_version=False`` outcome is collected into a single multi-line
:class:`PrereqMissing` so the install CLI surfaces EXIT 81 with one
actionable message naming every missing SDK.

Per spec D-101-14 the message MUST include, per failing stack:
* the stack name,
* the SDK name (from ``prereqs.sdk_per_stack.<stack>.name``),
* the install link (from ``prereqs.sdk_per_stack.<stack>.install_link``),
* the exact ``<probe>`` command the user runs to verify after install.

D-101-13 carve-out: stacks whose ``platform_unsupported_stack`` covers the
current OS are NOT probed -- the stack is filtered out at the tools phase
and the SDK prereq is moot.

NG-11 (do-not-install) is honoured: this module ONLY probes; it never
shells out to install/upgrade an SDK.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Final

from ai_engineering.cli_commands._exit_codes import PrereqMissing
from ai_engineering.installer.templates import get_ai_engineering_template_root
from ai_engineering.prereqs.sdk import probe_sdk
from ai_engineering.state.manifest import (
    SDK_REQUIRED_STACKS,
    load_required_tools,
    load_sdk_prereqs,
)

__all__ = ("PROBE_COMMAND_BY_STACK", "check_sdk_prereqs")


# Path under the project root and template root where the manifest lives.
_MANIFEST_REL = Path(".ai-engineering") / "manifest.yml"


# Canonical user-facing probe commands per spec.md D-101-14 (the verify
# command displayed after the install link). Mirrors
# :data:`ai_engineering.prereqs.sdk._PROBE_ARGV` but rendered as a string
# the user can copy-paste.
PROBE_COMMAND_BY_STACK: Final[dict[str, str]] = {
    "java": "java -version",
    "kotlin": "java -version",
    "swift": "swift --version",
    "dart": "dart --version",
    "csharp": "dotnet --version",
    "go": "go version",
    "rust": "rustc --version",
    "php": "php --version",
    "cpp": "clang --version",
}


def _manifest_root_for_loader(root: Path) -> Path:
    """Return the project root if it carries a manifest, else the template root.

    The SDK gate runs BEFORE the governance phase copies the template manifest
    into the project. On a fresh install the project root has no manifest yet,
    so ``load_required_tools`` would return an empty result and the D-101-13
    carve-out would never apply. Falling back to the bundled template root
    gives the gate a stable view of every stack's ``platform_unsupported_stack``
    without depending on install ordering.
    """
    if (root / _MANIFEST_REL).is_file():
        return root
    try:
        template_root = get_ai_engineering_template_root()
    except FileNotFoundError:
        return root
    # ``get_ai_engineering_template_root`` returns the ``.ai-engineering`` dir
    # itself; ``load_required_tools`` expects the parent project root.
    return template_root.parent


def _resolve_skipped_stacks(
    stacks: Iterable[str],
    *,
    root: Path,
    current_os: str | None,
) -> set[str]:
    """Return the set of stacks filtered out by ``platform_unsupported_stack``.

    Delegates to :func:`load_required_tools` so the loader's stack-skip logic
    is the single source of truth -- the SDK gate can then trust the carve-out
    is consistent with what the tools phase actually runs. Falls back to the
    template manifest when the project manifest does not yet exist so the
    carve-out applies on first-install too.
    """
    loader_root = _manifest_root_for_loader(root)
    load_result = load_required_tools(stacks, root=loader_root, current_os=current_os)
    return {marker.stack for marker in load_result.skipped_stacks}


def _format_failure_line(
    *,
    stack: str,
    sdk_name: str,
    install_link: str,
    probe_cmd: str,
    failure_reason: str,
) -> str:
    """Render a single failing-stack block for the EXIT 81 message."""
    return (
        f"  - stack {stack!r}: {failure_reason}. "
        f"{sdk_name} install: {install_link} "
        f"(verify with `{probe_cmd}`)"
    )


def check_sdk_prereqs(
    stacks: Iterable[str],
    *,
    root: Path,
    current_os: str | None = None,
) -> None:
    """Probe SDKs for the project's declared SDK-required stacks.

    Parameters
    ----------
    stacks:
        The project's declared stacks (``providers.stacks``).
    root:
        Repository root containing ``.ai-engineering/manifest.yml``.
    current_os:
        Optional override for the current OS (defaults to
        ``platform.system()``); useful for tests.

    Raises
    ------
    PrereqMissing
        Aggregated when one or more SDK-required stacks have an absent or
        out-of-range SDK. The message is multi-line and names every failing
        stack so the user has a single shopping list.
    """
    declared = list(stacks)

    # Filter to SDK-required stacks first -- non-SDK stacks (python,
    # typescript, etc.) bypass the gate entirely.
    sdk_stacks = [s for s in declared if s in SDK_REQUIRED_STACKS]
    if not sdk_stacks:
        return

    # Apply D-101-13 carve-out: stacks whose platform_unsupported_stack
    # covers the current OS are filtered out before the SDK probe runs.
    skipped = _resolve_skipped_stacks(declared, root=root, current_os=current_os)
    candidates = [s for s in sdk_stacks if s not in skipped]
    if not candidates:
        return

    # Look up SDK metadata (name + install_link). The loader returns one
    # SdkPrereq per SDK-required stack in the input list.
    prereqs = {p_obj.name: p_obj for p_obj in load_sdk_prereqs(candidates, root=root)}

    # The loader keys by SDK name (e.g. "JDK"); we need a per-stack map.
    # Re-resolve via the canonical metadata source so the lookup is keyed
    # by stack rather than SDK display-name.
    from ai_engineering.state.manifest import (
        _CANONICAL_SDK_PREREQS,
    )

    failure_lines: list[str] = []
    for stack in candidates:
        result = probe_sdk(stack)
        if result.present and result.meets_min_version:
            continue

        canonical = _CANONICAL_SDK_PREREQS[stack]
        sdk_name = canonical["name"]
        install_link = canonical["install_link"]
        probe_cmd = PROBE_COMMAND_BY_STACK[stack]

        if not result.present:
            reason = result.error_message or f"{sdk_name} not found on PATH"
        else:
            reason = (
                f"{sdk_name} version {result.version!r} is below the "
                f"minimum required by spec D-101-14"
            )

        failure_lines.append(
            _format_failure_line(
                stack=stack,
                sdk_name=sdk_name,
                install_link=install_link,
                probe_cmd=probe_cmd,
                failure_reason=reason,
            )
        )
        # Reference `prereqs` so static analysis doesn't strip the lookup;
        # the canonical fallback is used above, but downstream consumers
        # may want the loaded SdkPrereq instances later.
        _ = prereqs.get(sdk_name)

    if not failure_lines:
        return

    header = (
        "prereq missing: one or more language SDKs are absent or out-of-range "
        "(D-101-14). Install the missing SDK manually, then re-run "
        "`ai-eng install`:"
    )
    raise PrereqMissing("\n".join([header, *failure_lines]))
