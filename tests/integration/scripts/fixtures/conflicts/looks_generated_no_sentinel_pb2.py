"""Filename mimics a protobuf-generated module but carries no sentinel.

The classifier MUST refuse to auto-resolve on filename pattern alone.
This module body is hand-written for the adversarial fixture.
"""

from __future__ import annotations


def looks_generated() -> str:
    """Return a sentinel-free string the classifier cannot use as a signal."""
    return "no sentinel here"
