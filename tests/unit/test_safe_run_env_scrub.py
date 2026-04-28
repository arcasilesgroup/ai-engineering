"""RED tests for spec-101 D-101-02 hardening 4.

Hardening 4 covers two load-bearing properties of ``ai_engineering.installer.user_scope_install``:

1. **Sensitive env scrubbing** — every subprocess spawned by ``_safe_run`` runs with an env
   stripped of keys matching the regex
   ``^(.+_API_KEY|.+_SECRET|.+_TOKEN|.+_PASSWORD|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|
   AWS_ACCESS_KEY_ID|GITHUB_TOKEN|DATABASE_URL|GH_TOKEN|AZURE_.+_KEY|
   GOOGLE_APPLICATION_CREDENTIALS)$``. Standard env (``PATH``, ``HOME``, ``LANG``, ``TZ``,
   ``TERM``) is preserved.
2. **Cached absolute path resolution** — ``RESOLVED_DRIVERS`` is initialised at module-load
   time as a frozen mapping (``MappingProxyType``-like) of driver name to absolute path.
   Subsequent ``_safe_run`` calls use the cached absolute path; ``shutil.which`` is NOT
   re-invoked per call (closing the TOCTOU race where ``$PATH`` mutates between resolve and
   exec).

These tests intentionally fail with ``ModuleNotFoundError`` until T-1.22 GREEN creates
``src/ai_engineering/installer/user_scope_install.py`` and the public helper
``_scrubbed_env``.
"""

from __future__ import annotations

import importlib
import os
import sys
from types import MappingProxyType

import pytest

MODULE_NAME = "ai_engineering.installer.user_scope_install"

SENSITIVE_KEYS_POISONED: tuple[tuple[str, str], ...] = (
    ("ANTHROPIC_API_KEY", "poison"),
    ("AWS_SECRET_ACCESS_KEY", "poison"),
    ("AWS_ACCESS_KEY_ID", "poison"),
    ("GITHUB_TOKEN", "poison"),
    ("GH_TOKEN", "poison"),
    ("DATABASE_URL", "poison"),
    ("MY_API_KEY", "poison"),
    ("STRIPE_SECRET", "poison"),
    ("JWT_TOKEN", "poison"),
    ("DB_PASSWORD", "poison"),
    ("AZURE_STORAGE_KEY", "poison"),
    ("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/creds.json"),
)

PRESERVED_KEYS: tuple[str, ...] = ("PATH", "HOME", "LANG", "TZ", "TERM")


def _import_module():
    """Import the SUT module — fails with ModuleNotFoundError until T-1.22 GREEN."""
    return importlib.import_module(MODULE_NAME)


class TestEnvScrubbingStripsSensitive:
    """``_safe_run`` MUST strip sensitive env keys from the child process environment."""

    @pytest.mark.parametrize(("key", "value"), SENSITIVE_KEYS_POISONED)
    def test_sensitive_key_absent_in_child_env(
        self,
        key: str,
        value: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        module = _import_module()
        monkeypatch.setenv(key, value)

        result = module._safe_run(
            [
                sys.executable,
                "-c",
                f"import os; print(os.environ.get({key!r}))",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"child exited non-zero: {result.stderr!r}"
        assert result.stdout.strip() == "None", (
            f"sensitive key {key!r} leaked into child stdout: {result.stdout!r}"
        )


class TestEnvScrubbingPreservesStandard:
    """Standard env keys (``PATH``, ``HOME``, ``LANG``, ``TZ``, ``TERM``) MUST survive."""

    @pytest.mark.parametrize("key", PRESERVED_KEYS)
    def test_standard_key_present_in_child_env(
        self,
        key: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        module = _import_module()
        monkeypatch.setenv(key, f"sentinel-{key.lower()}")

        result = module._safe_run(
            [
                sys.executable,
                "-c",
                f"import os; print(os.environ.get({key!r}, '<<MISSING>>'))",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"child exited non-zero: {result.stderr!r}"
        assert result.stdout.strip() == f"sentinel-{key.lower()}", (
            f"standard key {key!r} did not survive scrubbing: {result.stdout!r}"
        )


class TestResolvedDriversIsFrozen:
    """``RESOLVED_DRIVERS`` MUST be an immutable mapping."""

    def test_resolved_drivers_is_mapping_proxy(self) -> None:
        module = _import_module()
        assert isinstance(module.RESOLVED_DRIVERS, MappingProxyType), (
            "RESOLVED_DRIVERS must be a MappingProxyType (or frozendict-equivalent)"
        )

    def test_resolved_drivers_assignment_raises_type_error(self) -> None:
        module = _import_module()
        with pytest.raises(TypeError):
            module.RESOLVED_DRIVERS["new-driver"] = "/usr/bin/evil"  # type: ignore[index]

    def test_resolved_drivers_pop_raises_type_error(self) -> None:
        module = _import_module()
        with pytest.raises((TypeError, AttributeError)):
            module.RESOLVED_DRIVERS.pop("git")  # type: ignore[attr-defined]

    def test_resolved_drivers_values_are_absolute_paths(self) -> None:
        module = _import_module()
        for name, path in module.RESOLVED_DRIVERS.items():
            assert os.path.isabs(path), (
                f"RESOLVED_DRIVERS[{name!r}]={path!r} is not an absolute path"
            )


class TestResolvedDriversCachedAtLoad:
    """``shutil.which`` MUST NOT be invoked per call — paths are cached at module load."""

    def test_safe_run_does_not_invoke_shutil_which_per_call(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        module = _import_module()

        # Patch shutil.which AFTER module import — if _safe_run still resolves correctly,
        # the resolution must come from the pre-cached RESOLVED_DRIVERS.
        which_calls: list[str] = []

        def _spy_which(cmd: str, *args: object, **kwargs: object) -> str | None:
            which_calls.append(cmd)
            return None  # simulate $PATH being mutated to remove the driver

        monkeypatch.setattr("shutil.which", _spy_which)

        # If _safe_run uses RESOLVED_DRIVERS, it succeeds. If it re-invokes shutil.which,
        # the patched _spy_which returns None and the call would fail.
        result = module._safe_run(
            [sys.executable, "-c", "print('cached')"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, (
            f"_safe_run should use cached RESOLVED_DRIVERS, not shutil.which "
            f"(which-calls observed: {which_calls!r}, stderr: {result.stderr!r})"
        )
        assert result.stdout.strip() == "cached"
        # Strict TOCTOU closure: zero per-call shutil.which invocations.
        assert which_calls == [], (
            f"_safe_run invoked shutil.which {len(which_calls)} time(s) post-cache: {which_calls!r}"
        )


class TestScrubbedEnvHelper:
    """``_scrubbed_env`` is a public-tested helper."""

    def test_helper_exists(self) -> None:
        module = _import_module()
        assert hasattr(module, "_scrubbed_env"), (
            "module must expose _scrubbed_env(env: dict) -> dict for direct testing"
        )
        assert callable(module._scrubbed_env)

    @pytest.mark.parametrize(("key", "value"), SENSITIVE_KEYS_POISONED)
    def test_helper_strips_sensitive_keys(self, key: str, value: str) -> None:
        module = _import_module()
        poisoned = {**dict(os.environ), key: value}
        scrubbed = module._scrubbed_env(poisoned)
        assert key not in scrubbed, (
            f"_scrubbed_env did not strip sensitive key {key!r}; output keys: "
            f"{sorted(scrubbed.keys())[:20]}..."
        )

    @pytest.mark.parametrize("key", PRESERVED_KEYS)
    def test_helper_preserves_standard_keys(self, key: str) -> None:
        module = _import_module()
        sentinel = f"sentinel-{key.lower()}"
        scrubbed = module._scrubbed_env({key: sentinel})
        assert scrubbed.get(key) == sentinel, (
            f"_scrubbed_env did not preserve standard key {key!r}: got {scrubbed.get(key)!r}"
        )

    def test_helper_returns_new_dict_not_mutating_input(self) -> None:
        module = _import_module()
        original = {"ANTHROPIC_API_KEY": "poison", "PATH": "/usr/bin"}
        snapshot = dict(original)
        _ = module._scrubbed_env(original)
        assert original == snapshot, (
            "_scrubbed_env mutated its input dict; it must return a new dict"
        )


class TestEmptyEnvOK:
    """``_safe_run`` MUST accept an explicit empty env without crashing."""

    def test_empty_env_runs_without_crash(self) -> None:
        module = _import_module()
        result = module._safe_run(
            [sys.executable, "-c", "print('ok')"],
            env={},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"_safe_run({{env: {{}}}}) crashed; stderr: {result.stderr!r}"
        )
        assert result.stdout.strip() == "ok"
