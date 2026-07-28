"""spec-159 D-159-02 — the BUILT wheel ships hook launchers + OPA policies.

This guard inspects the actual built artifact, NOT ``REPO_ROOT``. The
pre-existing ``tests/integration/test_hook_interpreter_resolution.py`` reads
the source tree, so the packaging gap (52 ``.sh/.ps1/.ts/.rego`` launcher /
policy files absent from ``[tool.hatch.build.targets.wheel].include``) was
structurally invisible: the dogfood editable install reads ``src/`` directly,
while every external ``pip install`` / ``uv tool install`` received a wheel
with dead hooks ("No such file or directory").

The test BUILDS a wheel into a tmp dir and unzips it. It FAILS before T-5
(the ``.sh/.ps1/.ts/.rego`` include globs are absent) and PASSES after.

Anchors: spec-159 D-159-01 (wheel include allowlist), D-159-02 (inspect the
built artifact). TDD §10.5. §10.6 SDD.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_ROOT = REPO_ROOT / "src" / "ai_engineering" / "templates"

# Files the wheel MUST ship under ``ai_engineering/templates/`` for external
# installs to have working hooks. ``run-hook.sh`` / ``resolve-python.sh`` are
# the spec-154 >=3.11 interpreter resolvers; the ``.rego`` policies back the
# governance gates; the ``.ts`` bridge wires the opencode surface.
REQUIRED_TEMPLATE_FILES = (
    ".ai-engineering/scripts/hooks/_lib/run-hook.sh",
    ".ai-engineering/scripts/hooks/_lib/resolve-python.sh",
    ".ai-engineering/scripts/hooks/opencode-hook-bridge.ts",
    # spec-201 sub-005: without the auto-discovered plugin entry the bridge is
    # packaged but never loaded, so a consumer install gets an OpenCode surface
    # that reads as guarded and enforces nothing.
    "project/.opencode/plugin/ai-engineering.ts",
    ".ai-engineering/policies/commit_conventional.rego",
    ".ai-engineering/policies/branch_protection.rego",
    ".ai-engineering/policies/risk_acceptance_ttl.rego",
)


def _build_wheel(outdir: Path) -> Path:
    """Build a wheel into ``outdir`` and return its path.

    Tries ``python -m build`` first, then ``uv build``, then ``hatch build``.
    Skips the test (rather than failing) only when no build backend is
    available in the environment — never to mask the packaging gap itself.
    """
    # Each candidate pairs a build command with the dir its wheel lands in.
    # ``build``/``uv`` honor an explicit out-dir (an isolated tmp), so the
    # test only ever inspects a freshly built artifact — never a stale wheel
    # in the repo ``dist/`` tree (which would mask a real packaging gap).
    candidates: list[tuple[list[str], Path]] = [
        ([sys.executable, "-m", "build", "--wheel", "--outdir", str(outdir)], outdir),
        (["uv", "build", "--wheel", "--out-dir", str(outdir)], outdir),
        # ``hatch build`` ignores out-dir and always writes ./dist; only used
        # as a last resort when neither build backend above is available.
        (["hatch", "build", "-t", "wheel"], REPO_ROOT / "dist"),
    ]
    last_err: str | None = None
    for cmd, wheel_dir in candidates:
        try:
            proc = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except (FileNotFoundError, OSError) as exc:
            last_err = f"{cmd[0]}: {exc}"
            continue
        if proc.returncode != 0:
            last_err = f"{' '.join(cmd)} exited {proc.returncode}:\n{proc.stderr[-2000:]}"
            continue
        wheels = sorted(
            wheel_dir.glob("ai_engineering-*.whl") if wheel_dir.is_dir() else [],
            key=lambda p: p.stat().st_mtime,
        )
        if wheels:
            return wheels[-1]
        last_err = f"{' '.join(cmd)} produced no .whl"
    pytest.skip(f"no usable wheel build backend available: {last_err}")


@pytest.mark.integration
def test_wheel_ships_hook_launchers_and_policies(tmp_path: Path) -> None:
    """The built wheel contains every launcher/policy under packaged templates."""
    wheel_path = _build_wheel(tmp_path)

    with zipfile.ZipFile(wheel_path) as zf:
        names = set(zf.namelist())

    missing: list[str] = []
    for rel in REQUIRED_TEMPLATE_FILES:
        arc = f"ai_engineering/templates/{rel}"
        if arc not in names:
            missing.append(arc)

    assert not missing, (
        "wheel is missing launcher/policy templates (external installs get dead hooks). "
        "Add the .sh/.ps1/.ts/.rego globs to "
        "[tool.hatch.build.targets.wheel].include in pyproject.toml. Missing:\n  "
        + "\n  ".join(missing)
    )


@pytest.mark.integration
def test_wheel_ships_copilot_launcher_variants(tmp_path: Path) -> None:
    """The wheel ships at least one ``copilot-*.sh`` and one ``copilot-*.ps1``."""
    wheel_path = _build_wheel(tmp_path)

    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()

    prefix = "ai_engineering/templates/.ai-engineering/scripts/hooks/copilot-"
    has_sh = any(n.startswith(prefix) and n.endswith(".sh") for n in names)
    has_ps1 = any(n.startswith(prefix) and n.endswith(".ps1") for n in names)

    assert has_sh, "wheel must ship at least one copilot-*.sh launcher"
    assert has_ps1, "wheel must ship at least one copilot-*.ps1 launcher"


@pytest.mark.integration
def test_required_template_files_exist_in_source(tmp_path: Path) -> None:
    """Sanity: the expected sources exist in-tree (guards the expected set itself)."""
    missing = [rel for rel in REQUIRED_TEMPLATE_FILES if not (TEMPLATES_ROOT / rel).is_file()]
    assert not missing, f"expected template sources missing from src tree: {missing}"
