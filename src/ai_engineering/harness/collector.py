"""Read-only context collector (spec-194 D-194-01).

Collects metrics from roots, skills, commands, hooks and MCP configuration.
Never reads secret values; parses structure only.
"""

from __future__ import annotations

import re
from pathlib import Path

from .schema import (
    CatalogMetrics,
    HookMetrics,
    McpResidue,
    RootMetrics,
)

# Rough token estimate: words * 4/3 (covers typical BPE overhead)
_WORD_TO_TOKEN_RATIO = 4 / 3

# Patterns that indicate mandatory-read directives
_MANDATORY_READ_PATTERNS = [
    re.compile(r"read every session", re.IGNORECASE),
    re.compile(r"every session.*read", re.IGNORECASE),
    re.compile(r"mandatory.*read", re.IGNORECASE),
    re.compile(r"must read before", re.IGNORECASE),
]


def collect_root_metrics(root: Path) -> RootMetrics:
    """Measure a single root instruction file.

    Returns byte count, estimated token count, and mandatory-read count.
    """
    if not root.exists():
        return RootMetrics(
            bytes=0,
            estimated_tokens=0,
            mandatory_reads=0,
            source_path=str(root),
        )

    content = root.read_text(encoding="utf-8")
    content_bytes = len(content.encode("utf-8"))
    words = len(content.split())
    estimated_tokens = int(words * _WORD_TO_TOKEN_RATIO)

    mandatory_reads = 0
    for pattern in _MANDATORY_READ_PATTERNS:
        mandatory_reads += len(pattern.findall(content))

    return RootMetrics(
        bytes=content_bytes,
        estimated_tokens=estimated_tokens,
        mandatory_reads=mandatory_reads,
        source_path=str(root),
    )


def collect_catalog_metrics(skills_dir: Path) -> CatalogMetrics:
    """Count unique and duplicate skill IDs from a skills directory.

    Scans for directories containing SKILL.md (Agent Skills convention).
    """
    if not skills_dir.exists():
        return CatalogMetrics(
            unique_ids=0,
            duplicate_ids=0,
            total_skills=0,
            duplicate_ids_list=[],
        )

    ids: list[str] = []
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_dir():
            skill_file = entry / "SKILL.md"
            if skill_file.exists():
                ids.append(entry.name)

    unique = sorted(set(ids))
    dupes = sorted({i for i in unique if ids.count(i) > 1})

    return CatalogMetrics(
        unique_ids=len(unique),
        duplicate_ids=len(dupes),
        total_skills=len(ids),
        duplicate_ids_list=dupes,
    )


def collect_command_metrics(commands_dir: Path) -> CatalogMetrics:
    """Count command entries (thin manual adapters)."""
    return collect_catalog_metrics(commands_dir)


def collect_hook_metrics(hooks_dir: Path) -> HookMetrics:
    """Scan hook scripts for injection patterns and automatic writes.

    Detects: additionalContext emission, tracked writes, file mutations.
    """
    if not hooks_dir.exists():
        return HookMetrics(
            injection_count=0,
            additional_context_tokens=0,
            automatic_writes=0,
            hook_names=[],
        )

    injection_count = 0
    additional_context_tokens = 0
    automatic_writes = 0
    hook_names: list[str] = []

    # Patterns indicating model-visible context injection
    _INJECTION_PATTERNS = [
        re.compile(r"additionalContext", re.IGNORECASE),
        re.compile(r"additional_context", re.IGNORECASE),
        re.compile(r"inject.*context", re.IGNORECASE),
    ]

    # Patterns indicating automatic file writes
    _WRITE_PATTERNS = [
        re.compile(r"\.write_text\(", re.IGNORECASE),
        re.compile(r"\.write_bytes\(", re.IGNORECASE),
        re.compile(r"open\(.*['\"]w['\"]", re.IGNORECASE),
        re.compile(r"shutil\.copy", re.IGNORECASE),
    ]

    for hook_file in sorted(hooks_dir.iterdir()):
        if not hook_file.is_file():
            continue
        if hook_file.suffix not in (".py", ".sh", ".ps1", ".ts", ".js"):
            continue

        hook_names.append(hook_file.name)
        try:
            content = hook_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        for pattern in _INJECTION_PATTERNS:
            injection_count += len(pattern.findall(content))

        for pattern in _WRITE_PATTERNS:
            automatic_writes += len(pattern.findall(content))

    return HookMetrics(
        injection_count=injection_count,
        additional_context_tokens=additional_context_tokens,
        automatic_writes=automatic_writes,
        hook_names=hook_names,
    )


def collect_mcp_residue(config_paths: list[Path]) -> McpResidue:
    """Scan MCP configuration files for reachable registrations.

    Reads structure only; never reads secret values.
    """
    registrations = 0
    plugins = 0
    permissions = 0
    operational_instructions = 0
    names: list[str] = []

    for config_path in config_paths:
        if not config_path.exists():
            continue
        try:
            content = config_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        # Count registration-like patterns
        registrations += content.lower().count("mcp")
        registrations += content.lower().count("server")

        # Count plugin patterns
        plugins += content.lower().count("plugin")
        plugins += content.lower().count("extension")

        # Count permission patterns
        permissions += content.lower().count("permission")
        permissions += content.lower().count("scope")

        names.append(config_path.name)

    return McpResidue(
        reachable_registrations=registrations,
        plugins=plugins,
        permissions=permissions,
        operational_instructions=operational_instructions,
        names=names,
    )
