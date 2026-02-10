"""JSON and NDJSON I/O for ai-engineering state files.

Provides:
- read/write for JSON state files (install-manifest, ownership-map, decision-store, sources.lock).
- append-only write for NDJSON audit log.
- Stable JSON formatting (sorted keys, 2-space indent) for clean diffs.
- ISO 8601 timestamp serialization.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def _json_serializer(obj: object) -> str:
    """Custom JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def read_json_model(path: Path, model_class: type[T]) -> T:
    """Read a JSON file and parse it into a Pydantic model.

    Args:
        path: Path to the JSON file.
        model_class: Pydantic model class to parse into.

    Returns:
        Parsed model instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        pydantic.ValidationError: If the JSON does not match the model schema.
    """
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return model_class.model_validate(data)


def write_json_model(path: Path, model: BaseModel) -> None:
    """Write a Pydantic model to a JSON file with stable formatting.

    Creates parent directories if they don't exist.
    Uses sorted keys and 2-space indentation for clean diffs.

    Args:
        path: Path to write the JSON file.
        model: Pydantic model instance to serialize.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = model.model_dump(by_alias=True, exclude_none=True)
    content = json.dumps(data, indent=2, sort_keys=True, default=_json_serializer)
    path.write_text(content + "\n", encoding="utf-8")


def append_ndjson(path: Path, entry: BaseModel) -> None:
    """Append a single entry to an NDJSON (newline-delimited JSON) file.

    Creates the file and parent directories if they don't exist.

    Args:
        path: Path to the NDJSON file.
        entry: Pydantic model instance to append as a single JSON line.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = entry.model_dump(by_alias=True, exclude_none=True)
    line = json.dumps(data, sort_keys=True, default=_json_serializer)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_ndjson_entries(path: Path, model_class: type[T]) -> list[T]:
    """Read all entries from an NDJSON file.

    Args:
        path: Path to the NDJSON file.
        model_class: Pydantic model class to parse each line into.

    Returns:
        List of parsed model instances. Empty list if file doesn't exist.
    """
    if not path.exists():
        return []

    entries: list[T] = []
    raw = path.read_text(encoding="utf-8")
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        entries.append(model_class.model_validate(data))
    return entries
