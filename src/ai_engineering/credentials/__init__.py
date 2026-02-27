"""Credential management for platform integrations.

Provides OS-native secret storage via the ``keyring`` library,
abstracting over Windows Credential Manager, macOS Keychain,
and Linux libsecret/GNOME Keyring.

Tokens are **never** stored in plain-text files.  Only non-secret
metadata (URLs, project keys, ``configured`` flags) is persisted
in ``.ai-engineering/state/tools.json``.
"""

from __future__ import annotations
