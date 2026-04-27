"""Dockerfile static checks.

We deliberately do NOT run a real Docker build here — the CI smoke matrix
covers that. These tests catch high-blast-radius regressions:

* The hard pin on `litellm==1.51.0` (ADR-0008) cannot be widened or replaced.
* The compromised range `1.82.x` cannot appear anywhere in the Dockerfile.
* USER appuser / non-root must remain in place.
* The entrypoint must remain `python -m ai_eng_litellm_bridge serve`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    path = Path(__file__).resolve().parent.parent / "Dockerfile"
    assert path.exists(), f"Dockerfile not found at {path}"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def compose_text() -> str:
    path = Path(__file__).resolve().parent.parent / "docker-compose.yml"
    assert path.exists(), f"docker-compose.yml not found at {path}"
    return path.read_text(encoding="utf-8")


class TestDockerfileSecurity:
    def test_litellm_hard_pinned_at_1_51_0(self, dockerfile_text: str) -> None:
        assert re.search(r'"litellm==1\.51\.0"', dockerfile_text), (
            "litellm pin missing — ADR-0008 requires 1.51.0 exactly."
        )

    def test_no_compromised_litellm_range(self, dockerfile_text: str) -> None:
        # 1.82.x was compromised on PyPI in March 2026.
        forbidden = re.search(r"litellm[^\n]*1\.82\.", dockerfile_text)
        assert forbidden is None, "Compromised LiteLLM 1.82.x present"

    def test_runs_unprivileged(self, dockerfile_text: str) -> None:
        assert re.search(r"useradd.*--uid 1000.*appuser", dockerfile_text), (
            "Unprivileged appuser missing"
        )
        assert "USER appuser" in dockerfile_text, "USER directive missing"

    def test_entrypoint_is_module_serve(self, dockerfile_text: str) -> None:
        # Order matters; the entrypoint elements must include the module + serve.
        assert '"ai_eng_litellm_bridge"' in dockerfile_text
        assert '"serve"' in dockerfile_text
        assert '"--port"' in dockerfile_text

    def test_python_unbuffered_set(self, dockerfile_text: str) -> None:
        # NDJSON telemetry-to-stdout requires unbuffered I/O.
        assert "PYTHONUNBUFFERED=1" in dockerfile_text

    def test_uses_slim_base(self, dockerfile_text: str) -> None:
        # No full python image — keep the attack surface small.
        assert "python:3.13-slim" in dockerfile_text


class TestComposeSecurity:
    def test_loopback_only_publish(self, compose_text: str) -> None:
        # ADR-0008: ports MUST be bound to 127.0.0.1 only.
        assert "127.0.0.1:4848:4848" in compose_text
        # Bare "4848:4848" without 127.0.0.1 prefix would expose externally.
        assert re.search(r"^\s*-\s*\"4848:4848\"", compose_text, re.MULTILINE) is None

    def test_read_only_filesystem(self, compose_text: str) -> None:
        assert re.search(r"read_only:\s*true", compose_text), "read_only must be true"

    def test_caps_dropped(self, compose_text: str) -> None:
        assert "cap_drop:" in compose_text
        assert "ALL" in compose_text

    def test_no_new_privileges(self, compose_text: str) -> None:
        assert "no-new-privileges" in compose_text

    def test_unprivileged_user(self, compose_text: str) -> None:
        assert re.search(r'user:\s*"1000:1000"', compose_text), (
            "user 1000:1000 must be set in compose"
        )
