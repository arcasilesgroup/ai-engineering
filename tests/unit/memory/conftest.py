"""Shared fixtures for spec-118 memory layer tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Inject the canonical scripts dir so `import memory` works from tests.
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / ".ai-engineering" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


@pytest.fixture
def memory_project(tmp_path: Path) -> Path:
    """A bare project with the .ai-engineering scaffold for memory.db."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "instincts").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "state" / "runtime").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def deterministic_embedder(monkeypatch: pytest.MonkeyPatch):
    """Stub fastembed: hash text -> 384-dim normalized vector with fixed seed.

    Same input -> same vector. Cosine identity = 1.0. Used by Phase 3 tests.
    """
    import hashlib

    import numpy as np

    def _embed(texts: list[str], *, model_name: str | None = None) -> list[list[float]]:
        del model_name  # accepted for signature parity; ignored in stub
        out: list[list[float]] = []
        for t in texts:
            seed = int(hashlib.sha256(t.encode()).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            v = rng.rand(384).astype(np.float32)
            norm = float(np.linalg.norm(v)) or 1.0
            out.append((v / norm).tolist())
        return out

    try:
        from memory import semantic  # type: ignore[import-not-found]

        monkeypatch.setattr(semantic, "embed_batch", _embed)
        monkeypatch.setattr(semantic, "_get_embedder", lambda *a, **kw: None)
    except ImportError:
        # Phase 3 module not present yet -- harmless during Phase 1/2 tests.
        pass
    return _embed
