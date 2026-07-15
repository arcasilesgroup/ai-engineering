"""spec-184: field-level ownership resolution for ``manifest.yml``.

The framework already declares per-key roles in
``control_plane.manifest_field_roles`` (``framework_defaults``). This module
turns that map into resolvers so ``ai-eng update`` can advance the keys it
owns while never touching user config:

- :func:`is_framework_owned_manifest_key` — is a key framework-CLASSIFIED
  (``descriptive_metadata`` or ``generated_projection``) vs team-owned
  (``canonical_input``)? Unknown keys default to team-owned — the framework
  never claims a key it does not recognise (fail-safe).
- :data:`FRAMEWORK_WRITABLE_KEYS` / :func:`is_framework_writable_manifest_key`
  — the STRICT subset of framework-owned keys ``ai-eng update`` may actually
  write. v1 = ``framework_version`` ONLY (D-184-02). Note the
  ``descriptive_metadata`` bucket also contains ``name`` and ``version``,
  which are the USER's project identity / release — classified
  framework-owned yet never auto-written.
"""

from __future__ import annotations

from ai_engineering.config.framework_defaults import DEFAULT_CONTROL_PLANE

_ROLES = DEFAULT_CONTROL_PLANE["manifest_field_roles"]
_FRAMEWORK_OWNED: frozenset[str] = frozenset(
    [*_ROLES["descriptive_metadata"], *_ROLES["generated_projection"]]
)

# spec-184 D-184-02 / D-184-06: the STRICT allowlist of keys `ai-eng update`
# may write. v1 = framework_version ONLY. `name`/`version` live in
# descriptive_metadata but are the user's project identity/release — they are
# classified framework-owned yet are never auto-written.
FRAMEWORK_WRITABLE_KEYS: frozenset[str] = frozenset({"framework_version"})


def is_framework_owned_manifest_key(key: str) -> bool:
    """Return True if the framework classifies this manifest key as its own.

    Team-owned (``canonical_input``) and unknown keys return False so the
    framework never claims a key it does not recognise.
    """
    return key in _FRAMEWORK_OWNED


def is_framework_writable_manifest_key(key: str) -> bool:
    """Return True if ``ai-eng update`` may write this key (v1 allowlist).

    Strictly narrower than ownership: only framework bookkeeping the
    framework actively maintains (v1: ``framework_version``). Never includes
    ``name``/``version`` (user identity) even though they are framework-owned.
    """
    return key in FRAMEWORK_WRITABLE_KEYS
