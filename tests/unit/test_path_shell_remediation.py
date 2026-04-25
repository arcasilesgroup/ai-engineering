"""Unit tests for ``_detect_active_shell`` + ``emit_path_snippet`` -- spec-101 T-2.13 RED.

When a tool lands outside the user's interactive ``$PATH`` (e.g. a fresh
``uv tool install ruff`` lands ``$HOME/.local/bin`` which the user has
not yet added to their shell rc), the installer needs to emit a
shell-specific copy-paste snippet so the user can fix the gap without
guessing which dialect their login shell uses.

Two single-concern helpers, both living in
``installer/user_scope_install.py``:

* ``_detect_active_shell()`` -- inspects ``$SHELL`` /
  ``$PSModulePath`` / ``$PSVersionTable``-style environment hints and
  returns ``"bash" | "zsh" | "fish" | "pwsh" | "cmd"``. Falls back to
  ``"bash"`` when nothing is detected so the snippet still renders.
* ``emit_path_snippet(target_dir)`` -- builds the shell-specific
  one-liner the operator must paste into their rc to add ``target_dir``
  to PATH.

These helpers are intentionally NOT coupled to ``capture_os_release``
(T-2.12) -- the user-scope install module's two single-concern surfaces
remain orthogonal.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# _detect_active_shell -- env-driven shell sniffer
# ---------------------------------------------------------------------------


class TestDetectActiveShellBash:
    """``$SHELL`` ending in ``/bash`` -> ``"bash"``."""

    def test_shell_bash_path_detected(self) -> None:
        from ai_engineering.installer import user_scope_install

        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/bin/bash", "PSModulePath": ""},
            clear=True,
        ):
            assert user_scope_install._detect_active_shell() == "bash"

    def test_shell_bash_in_homebrew_detected(self) -> None:
        from ai_engineering.installer import user_scope_install

        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/opt/homebrew/bin/bash"},
            clear=True,
        ):
            assert user_scope_install._detect_active_shell() == "bash"


class TestDetectActiveShellZsh:
    """``$SHELL`` ending in ``/zsh`` -> ``"zsh"``."""

    def test_shell_zsh_default_macos_detected(self) -> None:
        from ai_engineering.installer import user_scope_install

        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/bin/zsh"},
            clear=True,
        ):
            assert user_scope_install._detect_active_shell() == "zsh"


class TestDetectActiveShellFish:
    """``$SHELL`` ending in ``/fish`` -> ``"fish"``."""

    def test_shell_fish_detected(self) -> None:
        from ai_engineering.installer import user_scope_install

        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/usr/local/bin/fish"},
            clear=True,
        ):
            assert user_scope_install._detect_active_shell() == "fish"


class TestDetectActiveShellPowerShell:
    """PowerShell detected via ``$PSModulePath`` env presence."""

    def test_psmodulepath_detected_as_pwsh(self) -> None:
        from ai_engineering.installer import user_scope_install

        # The PowerShell child sets PSModulePath to the modules location.
        with patch.dict(
            user_scope_install.os.environ,
            {"PSModulePath": "C:\\Program Files\\PowerShell\\Modules"},
            clear=True,
        ):
            assert user_scope_install._detect_active_shell() == "pwsh"

    def test_pwsh_takes_precedence_over_inherited_shell(self) -> None:
        """When both PSModulePath and SHELL are set, PowerShell wins.

        Some terminals on Windows inherit ``$SHELL`` from a wrapper but
        the active interactive shell is PowerShell -- the env hint
        ``PSModulePath`` is the canonical signal.
        """
        from ai_engineering.installer import user_scope_install

        with patch.dict(
            user_scope_install.os.environ,
            {
                "PSModulePath": "C:\\Modules",
                "SHELL": "/bin/bash",  # inherited from a Cygwin wrapper, ignored
            },
            clear=True,
        ):
            assert user_scope_install._detect_active_shell() == "pwsh"


class TestDetectActiveShellCmd:
    """``cmd.exe`` -- Windows console without PowerShell hint."""

    def test_comspec_cmd_detected(self) -> None:
        from ai_engineering.installer import user_scope_install

        with patch.dict(
            user_scope_install.os.environ,
            {"COMSPEC": "C:\\Windows\\System32\\cmd.exe"},
            clear=True,
        ):
            assert user_scope_install._detect_active_shell() == "cmd"


class TestDetectActiveShellFallback:
    """Falls back to ``"bash"`` when nothing is detected."""

    def test_no_env_hints_falls_back_to_bash(self) -> None:
        from ai_engineering.installer import user_scope_install

        with patch.dict(user_scope_install.os.environ, {}, clear=True):
            assert user_scope_install._detect_active_shell() == "bash"

    def test_unrecognised_shell_falls_back_to_bash(self) -> None:
        """An exotic shell (e.g. ``tcsh``) falls back to bash."""
        from ai_engineering.installer import user_scope_install

        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/usr/local/bin/tcsh"},
            clear=True,
        ):
            assert user_scope_install._detect_active_shell() == "bash"


# ---------------------------------------------------------------------------
# emit_path_snippet -- shell-specific PATH addition snippet
# ---------------------------------------------------------------------------


class TestEmitPathSnippetBashZsh:
    """bash + zsh share an ``export PATH=...`` syntax."""

    def test_bash_emits_export_path_string(self) -> None:
        from ai_engineering.installer import user_scope_install

        # Resolve Path.home() BEFORE patching os.environ with clear=True --
        # on Windows, Path.home() reads USERPROFILE/HOMEDRIVE+HOMEPATH and
        # raises RuntimeError if those env vars are absent.
        target = Path.home() / ".local" / "bin"
        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/bin/bash"},
            clear=True,
        ):
            snippet = user_scope_install.emit_path_snippet(target)

        assert snippet.startswith("export PATH=")
        assert '"$HOME/.local/bin:$PATH"' in snippet or '"$HOME/.local/bin:$PATH' in snippet

    def test_zsh_emits_export_path_string(self) -> None:
        from ai_engineering.installer import user_scope_install

        target = Path.home() / ".local" / "bin"
        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/bin/zsh"},
            clear=True,
        ):
            snippet = user_scope_install.emit_path_snippet(target)

        assert snippet.startswith("export PATH=")
        assert "$HOME/.local/bin" in snippet
        assert "$PATH" in snippet


class TestEmitPathSnippetFish:
    """fish uses ``fish_add_path``."""

    def test_fish_emits_fish_add_path(self) -> None:
        from ai_engineering.installer import user_scope_install

        target = Path.home() / ".local" / "bin"
        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/usr/local/bin/fish"},
            clear=True,
        ):
            snippet = user_scope_install.emit_path_snippet(target)

        assert snippet.startswith("fish_add_path")
        assert "$HOME/.local/bin" in snippet


class TestEmitPathSnippetPowerShell:
    """PowerShell uses ``$env:Path += ...``."""

    def test_pwsh_emits_env_path_assign(self) -> None:
        from ai_engineering.installer import user_scope_install

        target = Path.home() / ".local" / "bin"
        with patch.dict(
            user_scope_install.os.environ,
            {"PSModulePath": "C:\\Modules"},
            clear=True,
        ):
            snippet = user_scope_install.emit_path_snippet(target)

        assert "$env:Path" in snippet
        # Windows separator (semicolon) and the target dir are present.
        assert ";" in snippet
        assert "$HOME" in snippet


class TestEmitPathSnippetCmd:
    """cmd.exe uses ``set PATH=...``."""

    def test_cmd_emits_set_path(self) -> None:
        from ai_engineering.installer import user_scope_install

        target = Path.home() / ".local" / "bin"
        with patch.dict(
            user_scope_install.os.environ,
            {"COMSPEC": "C:\\Windows\\System32\\cmd.exe"},
            clear=True,
        ):
            snippet = user_scope_install.emit_path_snippet(target)

        assert snippet.lower().startswith("set path=")


class TestEmitPathSnippetFallback:
    """Undetected shell falls back to bash dialect."""

    def test_unknown_shell_falls_back_to_bash_export(self) -> None:
        from ai_engineering.installer import user_scope_install

        target = Path.home() / ".local" / "bin"
        with patch.dict(user_scope_install.os.environ, {}, clear=True):
            snippet = user_scope_install.emit_path_snippet(target)

        assert snippet.startswith("export PATH=")


class TestEmitPathSnippetTargetDirSubstitution:
    """``target_dir`` is rendered literally into the snippet."""

    def test_custom_target_dir_appears_verbatim(self) -> None:
        """A non-default target_dir (e.g. ``~/.cargo/bin``) is substituted in."""
        from ai_engineering.installer import user_scope_install

        # Resolve target BEFORE clear=True patch wipes USERPROFILE on Windows.
        target = Path.home() / ".cargo" / "bin"
        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/bin/bash"},
            clear=True,
        ):
            snippet = user_scope_install.emit_path_snippet(target)

        # The home placeholder OR the absolute path must appear.
        assert ("$HOME/.cargo/bin" in snippet) or (str(target) in snippet)

    def test_dotnet_tools_dir_appears_verbatim(self) -> None:
        """``~/.dotnet/tools`` is rendered correctly for zsh."""
        from ai_engineering.installer import user_scope_install

        target = Path.home() / ".dotnet" / "tools"
        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/bin/zsh"},
            clear=True,
        ):
            snippet = user_scope_install.emit_path_snippet(target)

        assert ("$HOME/.dotnet/tools" in snippet) or (str(target) in snippet)


# ---------------------------------------------------------------------------
# Single-concern guard
# ---------------------------------------------------------------------------


class TestPathHelperContract:
    """The PATH helper is single-concern -- no os_release coupling."""

    def test_emit_path_snippet_does_not_invoke_capture_os_release(self) -> None:
        """``emit_path_snippet`` MUST NOT call ``capture_os_release``.

        T-2.13 spec: the PATH+shell helpers are orthogonal to OS release
        capture. Patching ``capture_os_release`` and asserting it was
        never called proves the orthogonality.
        """
        from ai_engineering.installer import user_scope_install

        target = Path.home() / ".local" / "bin"
        with (
            patch.dict(
                user_scope_install.os.environ,
                {"SHELL": "/bin/bash"},
                clear=True,
            ),
            patch.object(user_scope_install, "capture_os_release") as os_release_mock,
        ):
            user_scope_install.emit_path_snippet(target)

        os_release_mock.assert_not_called()

    def test_detect_active_shell_returns_str_literal(self) -> None:
        """``_detect_active_shell`` returns one of the documented literals."""
        from ai_engineering.installer import user_scope_install

        with patch.dict(
            user_scope_install.os.environ,
            {"SHELL": "/bin/zsh"},
            clear=True,
        ):
            result = user_scope_install._detect_active_shell()

        assert result in {"bash", "zsh", "fish", "pwsh", "cmd"}
