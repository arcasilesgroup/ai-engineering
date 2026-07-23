"""Tests for pack schema and validator (spec-198 T-1/T-2)."""

from __future__ import annotations

from ai_engineering.packs.schema import (
    CommandSpec,
    CredentialSpec,
    IntegrationPack,
    Provenance,
)
from ai_engineering.packs.validator import validate_pack


def _make_valid_pack() -> IntegrationPack:
    """Create a valid test pack."""
    return IntegrationPack(
        name="test-cli",
        description="Test CLI integration",
        provenance=Provenance(
            vendor_source="https://github.com/test/cli",
            version="1.0.0",
            license="MIT",
            asset_digest="abc123",
            launcher_digest="def456",
        ),
        commands=[
            CommandSpec(
                name="test-cmd",
                description="Test command",
                command_type="read-only",
            ),
        ],
        credentials=[
            CredentialSpec(
                source="keychain",
                service_name="test-cli",
            ),
        ],
    )


class TestProvenance:
    """Provenance tests."""

    def test_valid_provenance(self):
        p = Provenance(
            vendor_source="https://example.com",
            version="1.0.0",
            license="MIT",
            asset_digest="abc",
            launcher_digest="def",
        )
        assert p.vendor_source == "https://example.com"

    def test_roundtrip(self):
        pack = _make_valid_pack()
        json_str = pack.to_json()
        restored = IntegrationPack.from_json(json_str)
        assert restored.name == pack.name
        assert restored.provenance.version == pack.provenance.version


class TestValidator:
    """Validator tests."""

    def test_valid_pack(self):
        pack = _make_valid_pack()
        result = validate_pack(pack)
        assert result.valid
        assert result.errors == []

    def test_missing_provenance(self):
        pack = _make_valid_pack()
        pack = IntegrationPack(
            name=pack.name,
            description=pack.description,
            provenance=Provenance(
                vendor_source="",
                version="",
                license="",
                asset_digest="",
                launcher_digest="",
            ),
            commands=pack.commands,
            credentials=pack.credentials,
        )
        result = validate_pack(pack)
        assert not result.valid
        assert len(result.errors) > 0

    def test_mcp_fallback_forbidden(self):
        pack = _make_valid_pack()
        pack = IntegrationPack(
            name=pack.name,
            description=pack.description,
            provenance=pack.provenance,
            commands=pack.commands,
            credentials=pack.credentials,
            mcp_fallback="allowed",  # should fail
        )
        result = validate_pack(pack)
        assert not result.valid
        assert any("MCP fallback" in e for e in result.errors)

    def test_invalid_command_type(self):
        pack = _make_valid_pack()
        pack = IntegrationPack(
            name=pack.name,
            description=pack.description,
            provenance=pack.provenance,
            commands=[
                CommandSpec(name="bad", description="bad", command_type="invalid"),
            ],
            credentials=pack.credentials,
        )
        result = validate_pack(pack)
        assert not result.valid

    def test_confirmation_requires_phrase(self):
        pack = _make_valid_pack()
        pack = IntegrationPack(
            name=pack.name,
            description=pack.description,
            provenance=pack.provenance,
            commands=[
                CommandSpec(
                    name="dangerous",
                    description="dangerous",
                    command_type="destructive",
                    requires_confirmation=True,
                    confirmation_phrase=None,  # should fail
                ),
            ],
            credentials=pack.credentials,
        )
        result = validate_pack(pack)
        assert not result.valid

    def test_invalid_credential_source(self):
        pack = _make_valid_pack()
        pack = IntegrationPack(
            name=pack.name,
            description=pack.description,
            provenance=pack.provenance,
            commands=pack.commands,
            credentials=[
                CredentialSpec(source="file", service_name="test"),  # invalid
            ],
        )
        result = validate_pack(pack)
        assert not result.valid
