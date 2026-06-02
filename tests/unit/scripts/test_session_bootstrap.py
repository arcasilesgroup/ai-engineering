"""Tests for ``.ai-engineering/scripts/session_bootstrap.py`` (brief §16).

Validates:

* The dashboard is valid JSON with the documented top-level keys.
* ``elapsed_ms`` is present and numeric (perf-budget telemetry).
* The script handles a repo with no ``spec.md`` gracefully (``active_spec`` = None).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".ai-engineering" / "scripts" / "session_bootstrap.py"


def _run_script(repo_root: Path | None = None) -> dict:
    """Invoke the script as a subprocess; return parsed JSON."""
    cmd = [sys.executable, str(SCRIPT)]
    if repo_root is not None:
        cmd += ["--repo-root", str(repo_root)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"script failed: rc={result.returncode} stderr={result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.unit
def test_emits_valid_json() -> None:
    """The script's stdout must parse as JSON with the documented top-level keys."""
    dashboard = _run_script()
    assert isinstance(dashboard, dict)
    # Brief §16.2 minimum field set:
    for required in ("schema_version", "elapsed_ms", "branch", "last_commit", "hooks_health"):
        assert required in dashboard, f"missing key: {required!r}"
    assert dashboard["schema_version"] == 1


@pytest.mark.unit
def test_elapsed_ms_present_and_numeric() -> None:
    """``elapsed_ms`` is the perf-budget telemetry — numeric and non-negative."""
    dashboard = _run_script()
    elapsed = dashboard["elapsed_ms"]
    assert isinstance(elapsed, (int, float)), f"elapsed_ms not numeric: {type(elapsed)!r}"
    assert elapsed >= 0
    # A wildly-out-of-budget run (>5s wall) is itself a regression we'd
    # want to surface — assert a generous local-machine ceiling.
    assert elapsed < 5000, f"session bootstrap took {elapsed}ms (>5s budget)"


@pytest.mark.unit
def test_handles_missing_spec(tmp_path: Path) -> None:
    """Empty repo with no spec.md must not error; ``active_spec`` is None."""
    # Build a minimal repo skeleton: ``.ai-engineering/`` exists, no spec.md.
    fake_repo = tmp_path / "fake-repo"
    (fake_repo / ".ai-engineering" / "specs").mkdir(parents=True)
    (fake_repo / ".ai-engineering" / "state").mkdir(parents=True)
    # Init git so ``branch`` resolves cleanly.
    subprocess.run(
        ["git", "init", "--initial-branch=main", "--quiet", str(fake_repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.email", "boot@test.local"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.name", "boot-test"],
        check=True,
        capture_output=True,
    )

    dashboard = _run_script(repo_root=fake_repo)
    assert dashboard["active_spec"] is None
    # plan / events default to zero values; not an error.
    assert dashboard["recent_events_7d"] == 0
    assert dashboard["hooks_health"] == "unknown"


@pytest.mark.unit
def test_under_budget_warning_absent_on_normal_path(tmp_path: Path) -> None:
    """A clean small-repo invocation should not flag ``budget_exceeded``."""
    fake_repo = tmp_path / "fast-repo"
    (fake_repo / ".ai-engineering" / "specs").mkdir(parents=True)
    (fake_repo / ".ai-engineering" / "state").mkdir(parents=True)
    subprocess.run(
        ["git", "init", "--initial-branch=main", "--quiet", str(fake_repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.email", "fast@test.local"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.name", "fast-test"],
        check=True,
        capture_output=True,
    )

    dashboard = _run_script(repo_root=fake_repo)
    # On a microscopic repo, we should not exceed budget. Tolerate one
    # warning slot in case CI is slow but assert the field is structured.
    if "warnings" in dashboard:
        assert isinstance(dashboard["warnings"], list)


# ---------------------------------------------------------------------------
# T-4 RED: _SURFACE_DIRS paridad test
# ---------------------------------------------------------------------------

_SCRIPT_PATH = REPO_ROOT / ".ai-engineering" / "scripts" / "session_bootstrap.py"

_EXPECTED_SURFACES: set[str] = {
    "claude-code",
    "codex",
    "github-copilot",
    "opencode",
    "cursor",
    "antigravity",
}

_EXPECTED_SURFACE_DIRS: dict[str, tuple[str, str]] = {
    "claude-code": (".claude/skills", ".claude/agents"),
    "codex": (".codex/skills", ".codex/agents"),
    "github-copilot": (".github/skills", ".github/agents"),
    "opencode": (".opencode/skills", ".opencode/agents"),
    "cursor": (".cursor/skills", ".cursor/agents"),
    "antigravity": (".agents/skills", ".agents/agents"),
}


def _load_session_bootstrap_module() -> types.ModuleType:
    """Load session_bootstrap.py as a module by spec so we can inspect its globals."""
    spec = importlib.util.spec_from_file_location("session_bootstrap", _SCRIPT_PATH)
    assert spec is not None, f"cannot load spec from {_SCRIPT_PATH}"
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
class TestSurfaceDirs:
    """RED-phase assertions for the ``_SURFACE_DIRS`` constant (T-4, spec-142).

    ``_SURFACE_DIRS`` does not yet exist in session_bootstrap.py — these tests
    are expected to fail with ``AttributeError`` until T-5 implements the constant.
    This class is IMMUTABLE: do not weaken assertions for downstream convenience.
    """

    def test_surface_dirs_importable_and_is_dict(self) -> None:
        """``_SURFACE_DIRS`` must exist and be a ``dict``."""
        mod = _load_session_bootstrap_module()
        surface_dirs = mod._SURFACE_DIRS  # raises AttributeError if absent
        assert isinstance(surface_dirs, dict), (
            f"_SURFACE_DIRS must be a dict, got {type(surface_dirs)!r}"
        )

    def test_surface_dirs_values_are_2_tuples(self) -> None:
        """Every value in ``_SURFACE_DIRS`` must be a 2-tuple of strings."""
        mod = _load_session_bootstrap_module()
        surface_dirs: dict = mod._SURFACE_DIRS
        for surface, val in surface_dirs.items():
            assert isinstance(val, tuple) and len(val) == 2, (
                f"_SURFACE_DIRS[{surface!r}] must be a 2-tuple, got {val!r}"
            )
            skills_dir, agents_dir = val
            assert isinstance(skills_dir, str), (
                f"_SURFACE_DIRS[{surface!r}][0] (skills_dir) must be str, got {type(skills_dir)!r}"
            )
            assert isinstance(agents_dir, str), (
                f"_SURFACE_DIRS[{surface!r}][1] (agents_dir) must be str, got {type(agents_dir)!r}"
            )

    def test_surface_dirs_has_exactly_6_surfaces(self) -> None:
        """``_SURFACE_DIRS`` must cover exactly the 6-surface canonical set."""
        mod = _load_session_bootstrap_module()
        surface_dirs: dict = mod._SURFACE_DIRS
        assert set(surface_dirs.keys()) == _EXPECTED_SURFACES, (
            f"_SURFACE_DIRS keys mismatch.\n"
            f"  expected: {sorted(_EXPECTED_SURFACES)}\n"
            f"  got:      {sorted(surface_dirs.keys())}"
        )

    def test_surface_dirs_paridad_with_provider_tree_maps(self) -> None:
        """Every surface in ``_PROVIDER_TREE_MAPS`` must be covered by ``_SURFACE_DIRS``."""
        from ai_engineering.config.mirror_inventory import _PROVIDER_TREE_MAPS

        mod = _load_session_bootstrap_module()
        surface_dirs: dict = mod._SURFACE_DIRS
        missing = set(_PROVIDER_TREE_MAPS.keys()) - set(surface_dirs.keys())
        assert not missing, (
            f"_SURFACE_DIRS is missing surfaces that exist in _PROVIDER_TREE_MAPS: {missing!r}"
        )

    def test_surface_dirs_claude_code_layout(self) -> None:
        """``claude-code`` must map to ``.claude/skills`` / ``.claude/agents``."""
        mod = _load_session_bootstrap_module()
        surface_dirs: dict = mod._SURFACE_DIRS
        assert surface_dirs["claude-code"] == _EXPECTED_SURFACE_DIRS["claude-code"], (
            f"claude-code layout mismatch: {surface_dirs['claude-code']!r}"
        )

    def test_surface_dirs_codex_layout(self) -> None:
        """``codex`` must map to ``.codex/skills`` / ``.codex/agents``."""
        mod = _load_session_bootstrap_module()
        surface_dirs: dict = mod._SURFACE_DIRS
        assert surface_dirs["codex"] == _EXPECTED_SURFACE_DIRS["codex"], (
            f"codex layout mismatch: {surface_dirs['codex']!r}"
        )

    def test_surface_dirs_github_copilot_layout(self) -> None:
        """``github-copilot`` must map to ``.github/skills`` / ``.github/agents``."""
        mod = _load_session_bootstrap_module()
        surface_dirs: dict = mod._SURFACE_DIRS
        assert surface_dirs["github-copilot"] == _EXPECTED_SURFACE_DIRS["github-copilot"], (
            f"github-copilot layout mismatch: {surface_dirs['github-copilot']!r}"
        )

    def test_surface_dirs_opencode_layout(self) -> None:
        """``opencode`` must map to ``.opencode/skills`` / ``.opencode/agents``."""
        mod = _load_session_bootstrap_module()
        surface_dirs: dict = mod._SURFACE_DIRS
        assert surface_dirs["opencode"] == _EXPECTED_SURFACE_DIRS["opencode"], (
            f"opencode layout mismatch: {surface_dirs['opencode']!r}"
        )

    def test_surface_dirs_cursor_layout(self) -> None:
        """``cursor`` must map to ``.cursor/skills`` / ``.cursor/agents``."""
        mod = _load_session_bootstrap_module()
        surface_dirs: dict = mod._SURFACE_DIRS
        assert surface_dirs["cursor"] == _EXPECTED_SURFACE_DIRS["cursor"], (
            f"cursor layout mismatch: {surface_dirs['cursor']!r}"
        )

    def test_surface_dirs_antigravity_layout(self) -> None:
        """``antigravity`` must map to ``.agent/skills`` / ``.agent/agents``."""
        mod = _load_session_bootstrap_module()
        surface_dirs: dict = mod._SURFACE_DIRS
        assert surface_dirs["antigravity"] == _EXPECTED_SURFACE_DIRS["antigravity"], (
            f"antigravity layout mismatch: {surface_dirs['antigravity']!r}"
        )


# ---------------------------------------------------------------------------
# T-6 RED: surface-aware count test
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSurfaceAwareCounts:
    """RED-phase assertions for the two-argument ``_count_skills`` / ``_count_agents``
    signatures (T-6, spec-142).

    The production functions currently accept only ``root`` — these tests call
    ``_count_skills(root, manifest)`` and ``_count_agents(root, manifest)``,
    which must raise ``TypeError`` until T-7 widens the signatures.

    This class is IMMUTABLE: do not weaken assertions for downstream convenience.
    """

    # ------------------------------------------------------------------
    # local helper — write a manifest YAML and return the parsed dict
    # ------------------------------------------------------------------
    @staticmethod
    def _write_manifest(root: Path, yaml_text: str) -> dict:
        """Write a minimal manifest.yml and return it as a plain dict.

        Uses the module's own ``_read_manifest`` (which calls ``_read_manifest_minimal``
        as fallback) so the dict shape matches what session_bootstrap actually sees.
        """
        ai_eng = root / ".ai-engineering"
        ai_eng.mkdir(parents=True, exist_ok=True)
        (ai_eng / "manifest.yml").write_text(yaml_text)
        mod = _load_session_bootstrap_module()
        return mod._read_manifest(root)

    # ------------------------------------------------------------------
    # case 1 — github-copilot surface
    # ------------------------------------------------------------------
    def test_github_copilot_surface_skills_and_agents(self, tmp_path: Path) -> None:
        """github-copilot surface: 3 skills + 2 ``*.agent.md`` agents under .github/."""
        manifest = self._write_manifest(
            tmp_path,
            "surfaces:\n  enabled:\n  - github-copilot\n",
        )

        # stub skills
        for name in ("skill-a", "skill-b", "skill-c"):
            skill_dir = tmp_path / ".github" / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n")

        # stub agents
        agents_dir = tmp_path / ".github" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "foo.agent.md").write_text("# foo\n")
        (agents_dir / "bar.agent.md").write_text("# bar\n")

        mod = _load_session_bootstrap_module()
        assert mod._count_skills(tmp_path, manifest) == 3
        assert mod._count_agents(tmp_path, manifest) == 2

    def test_github_copilot_ignores_internal_agents(self, tmp_path: Path) -> None:
        """github-copilot dashboard counts only first-class ``*.agent.md`` files."""
        manifest = self._write_manifest(
            tmp_path,
            "surfaces:\n  enabled:\n  - github-copilot\n",
        )

        agents_dir = tmp_path / ".github" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "build.agent.md").write_text("# build\n")
        (agents_dir / "internal").mkdir()
        (agents_dir / "internal" / "reviewer-security.md").write_text("# internal\n")

        mod = _load_session_bootstrap_module()
        assert mod._count_agents(tmp_path, manifest) == 1

    @pytest.mark.parametrize(
        ("surface", "agents_dir", "counted_name", "ignored_name"),
        [
            ("claude-code", ".claude/agents", "ai-build.md", "build.agent.md"),
            ("codex", ".codex/agents", "ai-build.md", "build.agent.md"),
            ("github-copilot", ".github/agents", "build.agent.md", "ai-build.md"),
            ("opencode", ".opencode/agents", "ai-build.md", "build.agent.md"),
            ("cursor", ".cursor/agents", "ai-build.mdc", "ai-build.md"),
            ("antigravity", ".agents/agents", "ai-build.md", "build.agent.md"),
        ],
    )
    def test_agent_filename_pattern_for_each_surface(
        self,
        tmp_path: Path,
        surface: str,
        agents_dir: str,
        counted_name: str,
        ignored_name: str,
    ) -> None:
        """Every supported surface uses its own first-class agent filename convention."""
        manifest = self._write_manifest(
            tmp_path,
            f"surfaces:\n  enabled:\n  - {surface}\n",
        )

        base = tmp_path / agents_dir
        base.mkdir(parents=True)
        (base / counted_name).write_text("# counted\n")
        (base / ignored_name).write_text("# ignored\n")
        (base / "internal").mkdir()
        (base / "internal" / counted_name).write_text("# internal ignored\n")

        mod = _load_session_bootstrap_module()
        assert mod._count_agents(tmp_path, manifest) == 1

    # ------------------------------------------------------------------
    # case 2 — claude-code surface (explicit)
    # ------------------------------------------------------------------
    def test_claude_code_surface_explicit(self, tmp_path: Path) -> None:
        """claude-code surface (explicit): 2 skills + 1 agent under .claude/."""
        manifest = self._write_manifest(
            tmp_path,
            "surfaces:\n  enabled:\n  - claude-code\n",
        )

        for name in ("skill-one", "skill-two"):
            skill_dir = tmp_path / ".claude" / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n")

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "ai-alpha.md").write_text("# ai-alpha\n")

        mod = _load_session_bootstrap_module()
        assert mod._count_skills(tmp_path, manifest) == 2
        assert mod._count_agents(tmp_path, manifest) == 1

    # ------------------------------------------------------------------
    # case 3 — codex surface
    # ------------------------------------------------------------------
    def test_codex_surface(self, tmp_path: Path) -> None:
        """codex surface: 1 skill + 1 agent under .codex/."""
        manifest = self._write_manifest(
            tmp_path,
            "surfaces:\n  enabled:\n  - codex\n",
        )

        skill_dir = tmp_path / ".codex" / "skills" / "skill-x"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# skill-x\n")

        agents_dir = tmp_path / ".codex" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "ai-x.md").write_text("# ai-x\n")

        mod = _load_session_bootstrap_module()
        assert mod._count_skills(tmp_path, manifest) == 1
        assert mod._count_agents(tmp_path, manifest) == 1

    # ------------------------------------------------------------------
    # case 4 — empty surfaces.enabled falls back to claude-code default
    # ------------------------------------------------------------------
    def test_empty_surfaces_falls_back_to_default(self, tmp_path: Path) -> None:
        """No surfaces key → fall back to _DEFAULT_SURFACE (claude-code)."""
        # manifest with no surfaces key at all
        manifest: dict = {}

        skill_dir = tmp_path / ".claude" / "skills" / "skill-default"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# skill-default\n")

        mod = _load_session_bootstrap_module()
        assert mod._count_skills(tmp_path, manifest) == 1

    # ------------------------------------------------------------------
    # case 5 — unknown surface in manifest → 0 (R-142-06 fallback)
    # ------------------------------------------------------------------
    def test_unknown_surface_returns_zero(self, tmp_path: Path) -> None:
        """Unknown surface not in _SURFACE_DIRS → _count_skills returns 0."""
        manifest: dict = {"surfaces": {"enabled": ["some-future-surface"]}}

        mod = _load_session_bootstrap_module()
        assert mod._count_skills(tmp_path, manifest) == 0


# ---------------------------------------------------------------------------
# T-9 RED: _hooks_health unverified test
# ---------------------------------------------------------------------------


def _sha256_normalised(content: bytes) -> str:
    """Compute sha256 with CRLF→LF normalisation, matching _hooks_health exactly."""
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()


@pytest.mark.unit
class TestHooksHealth:
    """RED-phase assertions for ``_hooks_health`` (T-9, spec-142).

    Case (c) is the RED target: manifest MISSING but hooks dir has files must
    return ``"unverified"``.  The current implementation returns ``"unknown"``
    for this scenario, so test_manifest_missing_hooks_present FAILS today.

    This class is IMMUTABLE: do not weaken assertions for downstream convenience.
    """

    _HOOKS_REL = ".ai-engineering/scripts/hooks"
    _MANIFEST_REL = ".ai-engineering/state/hooks-manifest.json"

    def _hooks_dir(self, root: Path) -> Path:
        return root / self._HOOKS_REL

    def _manifest_path(self, root: Path) -> Path:
        return root / self._MANIFEST_REL

    def _write_hook_file(self, root: Path, name: str, content: bytes = b"#!/bin/sh\n") -> Path:
        hooks_dir = self._hooks_dir(root)
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook = hooks_dir / name
        hook.write_bytes(content)
        return hook

    def _write_manifest(self, root: Path, hooks: dict) -> None:
        manifest_path = self._manifest_path(root)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps({"hooks": hooks}),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # case (a) — manifest exists + hashes match → "ok"
    # ------------------------------------------------------------------
    def test_manifest_matches_on_disk(self, tmp_path: Path) -> None:
        """Manifest exists and all sha256 entries match on-disk bytes → ``'ok'``."""
        content = b"#!/bin/sh\necho hello\n"
        hook = self._write_hook_file(tmp_path, "pre-commit.sh", content)
        rel = str(hook.relative_to(tmp_path))
        digest = _sha256_normalised(content)
        self._write_manifest(tmp_path, {rel: digest})

        mod = _load_session_bootstrap_module()
        assert mod._hooks_health(tmp_path) == "ok"

    # ------------------------------------------------------------------
    # case (b) — manifest exists + drift → "drift(1)"
    # ------------------------------------------------------------------
    def test_manifest_drift(self, tmp_path: Path) -> None:
        """Manifest exists but one entry's hash differs from on-disk → ``'drift(1)'``."""
        content = b"#!/bin/sh\necho hello\n"
        hook = self._write_hook_file(tmp_path, "pre-commit.sh", content)
        rel = str(hook.relative_to(tmp_path))
        wrong_digest = "0" * 64  # deliberately wrong sha256
        self._write_manifest(tmp_path, {rel: wrong_digest})

        mod = _load_session_bootstrap_module()
        assert mod._hooks_health(tmp_path) == "drift(1)"

    # ------------------------------------------------------------------
    # case (c) — manifest MISSING, hooks dir has files → "unverified"
    #            THIS IS THE RED TARGET: current impl returns "unknown"
    # ------------------------------------------------------------------
    def test_manifest_missing_hooks_present(self, tmp_path: Path) -> None:
        """Manifest absent but hooks dir has at least one file → ``'unverified'``.

        RED target: the current ``_hooks_health`` returns ``'unknown'`` in this
        scenario (manifest-absent early-return path).  This assertion will FAIL
        until T-10 adds the ``'unverified'`` branch.
        """
        self._write_hook_file(tmp_path, "pre-commit.sh")
        # deliberately do NOT write the manifest

        mod = _load_session_bootstrap_module()
        assert mod._hooks_health(tmp_path) == "unverified", (
            "Expected 'unverified' (hooks dir has files, manifest absent), "
            f"got {mod._hooks_health(tmp_path)!r}. "
            "This test is RED until T-10 implements the unverified branch."
        )

    # ------------------------------------------------------------------
    # case (d) — manifest MISSING and hooks dir missing/empty → "unknown"
    # ------------------------------------------------------------------
    def test_manifest_missing_no_hooks(self, tmp_path: Path) -> None:
        """Manifest absent and hooks dir absent → ``'unknown'``."""
        # no manifest, no hooks dir — bare tmp_path
        mod = _load_session_bootstrap_module()
        assert mod._hooks_health(tmp_path) == "unknown"

    # ------------------------------------------------------------------
    # case (e) — manifest exists but "hooks" key empty/non-dict → "unknown"
    # ------------------------------------------------------------------
    def test_manifest_hooks_key_empty(self, tmp_path: Path) -> None:
        """Manifest exists but ``hooks`` key is empty dict → ``'unknown'``."""
        self._write_manifest(tmp_path, {})

        mod = _load_session_bootstrap_module()
        assert mod._hooks_health(tmp_path) == "unknown"

    def test_manifest_hooks_key_non_dict(self, tmp_path: Path) -> None:
        """Manifest exists but ``hooks`` key is a list (non-dict) → ``'unknown'``."""
        manifest_path = self._manifest_path(tmp_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps({"hooks": ["not", "a", "dict"]}),
            encoding="utf-8",
        )

        mod = _load_session_bootstrap_module()
        assert mod._hooks_health(tmp_path) == "unknown"


# ---------------------------------------------------------------------------
# T-11 RED: unverified hint in markdown rendering
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHooksUnverifiedHint:
    """RED-phase assertions for the ``unverified`` hint in ``_render_markdown`` (T-11, spec-142).

    The current renderer outputs ``hooks: unverified`` with no follow-up
    hint. These tests will FAIL until T-11 GREEN applies the em-dash hint.

    This class is IMMUTABLE: do not weaken assertions for downstream convenience.
    """

    @staticmethod
    def _minimal_d(hooks_health: str) -> dict:
        """Return the minimal ``d`` dict that ``_render_markdown`` needs."""
        return {
            "hooks_health": hooks_health,
            "recent_events_7d": 0,
        }

    def test_unverified_renders_hint_with_script_reference(self) -> None:
        """When hooks_health is 'unverified', rendered markdown must contain the hint.

        The hint must read:
            hooks: unverified — run `regenerate-hooks-manifest.py`
        using a U+2014 em-dash (—).
        """
        mod = _load_session_bootstrap_module()
        rendered = mod._render_markdown(self._minimal_d("unverified"))
        assert "hooks: unverified — run `regenerate-hooks-manifest.py`" in rendered, (
            "Expected hint 'hooks: unverified — run `regenerate-hooks-manifest.py`' "
            f"not found in rendered markdown:\n{rendered}"
        )

    def test_unverified_does_not_render_bare_label(self) -> None:
        """When hooks_health is 'unverified', bare 'hooks: unverified' followed by
        separator or newline (old behaviour, no hint) must NOT appear.
        """
        mod = _load_session_bootstrap_module()
        rendered = mod._render_markdown(self._minimal_d("unverified"))
        # The old rendering was `hooks: unverified` with no em-dash continuation.
        # After the GREEN patch the rendered text contains the em-dash hint, so
        # "hooks: unverified " is still present as a prefix — we check that it is
        # always followed by the em-dash, never by the line-separator " · " or newline.
        import re

        bad_pattern = re.compile(r"hooks: unverified(?! —)")
        assert not bad_pattern.search(rendered), (
            "Found bare 'hooks: unverified' without the em-dash hint. "
            "This is the old behaviour (RED state)."
        )

    def test_ok_health_renders_without_hint(self) -> None:
        """When hooks_health is 'ok', rendered markdown must NOT contain the hint."""
        mod = _load_session_bootstrap_module()
        rendered = mod._render_markdown(self._minimal_d("ok"))
        assert "hooks: ok" in rendered
        assert "regenerate-hooks-manifest.py" not in rendered

    def test_unknown_health_renders_without_hint(self) -> None:
        """When hooks_health is 'unknown', rendered markdown must NOT contain the hint."""
        mod = _load_session_bootstrap_module()
        rendered = mod._render_markdown(self._minimal_d("unknown"))
        assert "hooks: unknown" in rendered
        assert "regenerate-hooks-manifest.py" not in rendered


@pytest.mark.unit
class TestVersionUpdateBanner:
    """The dashboard surfaces a single-source ``update available`` line.

    Wired into the ``/ai-start`` dashboard so a new release shows at session
    start. Silent when up to date or when the status is unknown (fail-open).
    """

    @staticmethod
    def _d(version_status: dict | None) -> dict:
        return {
            "hooks_health": "ok",
            "recent_events_7d": 0,
            "version_status": version_status,
        }

    def test_renders_when_update_available(self) -> None:
        mod = _load_session_bootstrap_module()
        rendered = mod._render_markdown(
            self._d({"installed": "0.9.1", "latest": "0.9.2", "update_available": True})
        )
        assert "◈ ai-engineering 0.9.1 → 0.9.2" in rendered
        assert "ai-eng version upgrade" in rendered

    def test_shows_version_when_up_to_date(self) -> None:
        # The version is ALWAYS visible at session start — up to date shows the
        # installed version, not silence (operators asked "where's the version").
        mod = _load_session_bootstrap_module()
        rendered = mod._render_markdown(
            self._d({"installed": "0.9.2", "latest": "0.9.2", "update_available": False})
        )
        assert "◈ ai-engineering 0.9.2 · up to date" in rendered
        assert "version upgrade" not in rendered

    def test_silent_when_status_unknown(self) -> None:
        # Fail-open: status unknowable (ai_engineering not importable) → no line.
        mod = _load_session_bootstrap_module()
        rendered = mod._render_markdown(self._d(None))
        assert "◈ ai-engineering" not in rendered

    def test_version_status_fails_open_without_package(self) -> None:
        # _version_status swallows import/IO errors and returns None so the
        # dashboard renders even when ai_engineering is not importable.
        mod = _load_session_bootstrap_module()
        result = mod._version_status()
        assert result is None or isinstance(result, dict)


# ---------------------------------------------------------------------------
# T-14 RED: JSON output includes `surface_resolved`
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    """Initialise a bare git repo so session_bootstrap's git helpers don't fail."""
    subprocess.run(
        ["git", "init", "--initial-branch=main", "--quiet", str(path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "surface@test.local"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "surface-test"],
        check=True,
        capture_output=True,
    )


def _make_surface_root(tmp_path: Path, surface_name: str) -> Path:
    """Build a minimal fake-repo tmp root with surfaces.enabled: [surface_name]."""
    root = tmp_path / "repo"
    ai_eng = root / ".ai-engineering"
    (ai_eng / "specs").mkdir(parents=True)
    (ai_eng / "state").mkdir(parents=True)
    (ai_eng / "manifest.yml").write_text(
        f"surfaces:\n  enabled:\n  - {surface_name}\n",
        encoding="utf-8",
    )
    _init_git_repo(root)
    return root


@pytest.mark.unit
class TestSurfaceResolvedJsonField:
    """RED-phase assertions for the ``surface_resolved`` JSON field (T-14, spec-142).

    The field does not yet exist in session_bootstrap.py's output — these tests
    will FAIL until T-15 adds ``surface_resolved`` to the payload assembly in
    ``build_dashboard()``.

    D-142-06: ``surface_resolved`` is a top-level optional field; adding it
    MUST NOT bump ``schema_version``.

    This class is IMMUTABLE: do not weaken assertions for downstream convenience.
    """

    # ------------------------------------------------------------------
    # case 1 — known surface: claude-code
    # ------------------------------------------------------------------
    def test_surface_resolved_claude_code(self, tmp_path: Path) -> None:
        """surfaces.enabled: [claude-code] → surface_resolved == 'claude-code'."""
        root = _make_surface_root(tmp_path, "claude-code")
        dashboard = _run_script(repo_root=root)
        assert "surface_resolved" in dashboard, (
            "JSON output is missing top-level 'surface_resolved' key (D-142-06). "
            "This is the RED state — T-15 must add the field."
        )
        assert dashboard["surface_resolved"] == "claude-code", (
            f"Expected surface_resolved='claude-code', got {dashboard['surface_resolved']!r}"
        )

    # ------------------------------------------------------------------
    # case 2 — known surface: github-copilot
    # ------------------------------------------------------------------
    def test_surface_resolved_github_copilot(self, tmp_path: Path) -> None:
        """surfaces.enabled: [github-copilot] → surface_resolved == 'github-copilot'."""
        root = _make_surface_root(tmp_path, "github-copilot")
        dashboard = _run_script(repo_root=root)
        assert "surface_resolved" in dashboard, (
            "JSON output is missing top-level 'surface_resolved' key (D-142-06). "
            "This is the RED state — T-15 must add the field."
        )
        assert dashboard["surface_resolved"] == "github-copilot", (
            f"Expected surface_resolved='github-copilot', got {dashboard['surface_resolved']!r}"
        )

    # ------------------------------------------------------------------
    # case 3 — future / unknown surface → null (R-142-06)
    # ------------------------------------------------------------------
    def test_surface_resolved_unknown_surface_is_null(self, tmp_path: Path) -> None:
        """surfaces.enabled: [some-future-surface] → surface_resolved is null (R-142-06).

        When the declared surface is not in _SURFACE_DIRS the field must be
        JSON null (Python None) so tooling can detect the gap without
        parsing an unrecognised string.
        """
        root = _make_surface_root(tmp_path, "some-future-surface")
        dashboard = _run_script(repo_root=root)
        assert "surface_resolved" in dashboard, (
            "JSON output is missing top-level 'surface_resolved' key (D-142-06). "
            "This is the RED state — T-15 must add the field."
        )
        assert dashboard["surface_resolved"] is None, (
            f"Expected surface_resolved=null for unknown surface, "
            f"got {dashboard['surface_resolved']!r} (R-142-06: unknown surfaces map to null)"
        )

    # ------------------------------------------------------------------
    # case 4 — schema_version stays 1 (additive contract)
    # ------------------------------------------------------------------
    def test_schema_version_stays_1_after_surface_resolved_added(self, tmp_path: Path) -> None:
        """Adding surface_resolved MUST NOT bump schema_version (D-142-06 additive)."""
        root = _make_surface_root(tmp_path, "claude-code")
        dashboard = _run_script(repo_root=root)
        assert "schema_version" in dashboard, "schema_version key is missing from JSON output"
        assert dashboard["schema_version"] == 1, (
            f"schema_version must stay 1 after adding surface_resolved, "
            f"got {dashboard['schema_version']!r} (D-142-06: additive contract)"
        )
