"""Redaction engine for context safety reports (spec-194 D-194-02).

Ensures no secret value, home path, credential key material or raw
environment value appears in the report. Redaction is applied before
persistence.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Patterns that must be redacted
_SECRET_PATTERNS = [
    # API keys and tokens with assignment
    re.compile(
        r'(?i)(api[_-]?key|token|secret|password|credential)\s*[=:]\s*["\']?([^\s"\'<>]{8,})["\']?'
    ),
    # Bearer tokens
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    # AWS-style keys
    re.compile(r"(?i)(AKIA|ASIA)[A-Z0-9]{16}"),
    # GitHub tokens
    re.compile(r"gh[ps]_[A-Za-z0-9_]{36,}"),
    # Generic hex secrets (32+ chars) with assignment
    re.compile(r'(?i)(secret|key|token|password)\s*[=:]\s*["\']?([0-9a-f]{32,})["\']?'),
    # Standalone sk- prefixed tokens (OpenAI-style)
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]

_HOME_PATH_PATTERNS = [
    # macOS / Linux home paths
    re.compile(r"/Users/[a-zA-Z0-9._-]+"),
    re.compile(r"/home/[a-zA-Z0-9._-]+"),
    re.compile(r"~\/[a-zA-Z0-9._/-]+"),
]

_CREDENTIAL_FILE_PATTERNS = [
    re.compile(r"(?i)\.env\b"),
    re.compile(r"(?i)credentials?\.(json|yml|yaml|toml)"),
    re.compile(r"(?i)secrets?\.(json|yml|yaml|toml)"),
    re.compile(r"(?i)keychain"),
    re.compile(r"(?i)\.ssh/"),
]


def redact_string(value: str) -> str:
    """Redact secrets and home paths from a string."""
    result = value
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(lambda m: m.group(0)[:4] + "***REDACTED***", result)
    for pattern in _HOME_PATH_PATTERNS:
        result = pattern.sub("$HOME/.***", result)
    return result


def redact_value(value: Any) -> Any:
    """Recursively redact a value."""
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def redact_report(report_dict: dict[str, Any]) -> dict[str, Any]:
    """Redact an entire report dictionary."""
    return redact_value(report_dict)


def redact_json(json_str: str) -> str:
    """Redact a JSON string and return re-serialized JSON."""
    data = json.loads(json_str)
    redacted = redact_report(data)
    return json.dumps(redacted, indent=2, sort_keys=True)


def contains_secrets(text: str) -> bool:
    """Check if text contains potential secret patterns."""
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return True
    return False


def contains_home_paths(text: str) -> bool:
    """Check if text contains user home paths."""
    for pattern in _HOME_PATH_PATTERNS:
        if pattern.search(text):
            return True
    return False
