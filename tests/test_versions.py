"""Tests for spec 033 / B-033-4: the installed-version rule.

A finding that contradicts the installed bytes is mismatch; a matching claim passes; an
unresolvable package is unverified — never a guess from memory (graph-engineering's
installed-version rule). Resolution goes through importlib.metadata, monkeypatched in the
fixtures so no real distribution is needed.
"""

from __future__ import annotations

import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import versions  # noqa: E402


def test_a_matching_claim_passes(monkeypatch):
    monkeypatch.setattr(versions.metadata, "version", lambda _pkg: "8.30.1")
    assert versions.verify_against_installed("gitleaks", "8.30.1") == "match"


def test_a_contradicting_claim_is_mismatch(monkeypatch):
    monkeypatch.setattr(versions.metadata, "version", lambda _pkg: "8.30.1")
    assert versions.verify_against_installed("gitleaks", "7.0.0") == "mismatch"


def test_an_unresolvable_package_is_unverified(monkeypatch):
    def _raise(_pkg):
        raise metadata.PackageNotFoundError("nope")

    monkeypatch.setattr(versions.metadata, "version", _raise)
    assert versions.verify_against_installed("not-a-real-pkg", "1.0") == "unverified"
