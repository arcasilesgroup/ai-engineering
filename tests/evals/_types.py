"""Shared types for the evals harness (spec 029 / B-029-1)."""

from __future__ import annotations

from typing import TypedDict


class Defect(TypedDict):
    id: str
    tier: int
    file: str
    line: int


class Key(TypedDict):
    pack: str
    defects: list[Defect]
