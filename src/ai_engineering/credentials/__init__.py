"""Credential management for platform integrations.

Provides OS-native secret storage via the ``keyring`` library,
abstracting over Windows Credential Manager, macOS Keychain,
and Linux libsecret/GNOME Keyring.

Tokens are **never** stored in plain-text files. Platform metadata
is now tracked in ``InstallState.platforms`` (see ``state.models``).
"""

from __future__ import annotations
