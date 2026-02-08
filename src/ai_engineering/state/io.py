"""Read/write helpers for system-managed state files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON payload with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    """Read JSON payload from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_model(path: Path, model: type[ModelT]) -> ModelT:
    """Load and validate a model from a JSON file."""
    payload = read_json(path)
    return model.model_validate(payload)


def append_ndjson(path: Path, event: dict[str, Any]) -> None:
    """Append a single event to ndjson log file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")
