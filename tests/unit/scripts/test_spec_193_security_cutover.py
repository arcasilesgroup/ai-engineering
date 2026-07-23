"""RED contracts for the isolated, values-free spec-193 cutover runner.

These tests use synthetic markers only.  They must never read a real home
configuration, credential manager, environment, or provider.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path

import pytest

RUNNER_PATH = (
    Path(__file__).resolve().parents[3]
    / ".ai-engineering"
    / "scripts"
    / "spec-193"
    / "security_cutover.py"
)
RECEIPT_FIELDS = frozenset(
    {
        "credential_alias",
        "provider",
        "cli_version",
        "probe_id",
        "exit_code",
        "timestamp",
        "redacted_field_count",
        "invalidation_evidence_ref",
    }
)
SYNTHETIC_CANARY = "cutover-synthetic-canary-not-a-credential"
SYNTHETIC_DERIVED_HASH = "a" * 64


def _load_runner():
    """Load only the one-shot runner under test, never an installed package."""
    if not RUNNER_PATH.is_file():
        pytest.fail("T-0.2 must create the isolated cutover runner")
    spec = importlib.util.spec_from_file_location("spec_193_security_cutover", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _valid_receipt() -> dict[str, object]:
    return {
        "credential_alias": "credential-001",
        "provider": "provider-under-test",
        "cli_version": "1.2.3",
        "probe_id": "checkpoint-one-read-only",
        "exit_code": 0,
        "timestamp": "2026-07-23T00:00:00+00:00",
        "redacted_field_count": 0,
        "invalidation_evidence_ref": "issuer-reference-001",
    }


def test_receipt_schema_accepts_only_the_exact_d193_08_field_set() -> None:
    runner = _load_runner()

    receipt = runner.validate_receipt(_valid_receipt())

    assert isinstance(receipt, Mapping)
    assert set(receipt) == RECEIPT_FIELDS


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "account_id",
        "workspace_id",
        "endpoint",
        "raw_stdout",
        "raw_stderr",
        "operation",
        "result",
        "manifest_reference",
        "chain_pointer",
        "secret_derived_hash",
    ],
)
def test_receipt_schema_rejects_every_non_allowlisted_field(
    forbidden_field: str,
) -> None:
    runner = _load_runner()
    receipt = _valid_receipt()
    receipt[forbidden_field] = "synthetic-metadata"

    with pytest.raises(ValueError):
        runner.validate_receipt(receipt)


@pytest.mark.parametrize(
    "unsafe_value",
    [
        pytest.param(
            str(Path("/").joinpath("home", "operator", "private", "config")),
            id="absolute-path",
        ),
        pytest.param(SYNTHETIC_CANARY, id="synthetic-marker"),
        pytest.param(SYNTHETIC_DERIVED_HASH, id="derived-digest"),
    ],
)
def test_redaction_rejects_personal_paths_and_secret_markers(
    unsafe_value: str,
) -> None:
    runner = _load_runner()

    with pytest.raises(ValueError):
        runner.validate_values_free({"synthetic": unsafe_value})


def test_redaction_rejects_raw_streams_at_any_depth() -> None:
    runner = _load_runner()

    with pytest.raises(ValueError):
        runner.validate_values_free(
            {
                "outer": {
                    "raw_stdout": "synthetic-output",
                    "nested": ["safe-looking", {"raw_stderr": "also-forbidden"}],
                }
            }
        )


def _credential_row(runner, **changes):
    fields = {
        "credential_alias": "credential-001",
        "provider": "provider-under-test",
        "state": runner.CredentialState.DISCOVERED,
        "disposition": runner.CredentialDisposition.REPLACE_REVOKE,
        "future_consumer": "direct-cli",
        "config_hash": "config-001",
    }
    fields.update(changes)
    return runner.CredentialRow(**fields)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("DISCOVERED", "SOURCE_CONTAINED"),
        ("SOURCE_CONTAINED", "TARGET_READY"),
        ("TARGET_READY", "NEW_AUTH_OK"),
        ("NEW_AUTH_OK", "CONFIG_CUTOVER"),
        ("CONFIG_CUTOVER", "OLD_INVALID"),
        ("OLD_INVALID", "POSTCHECK"),
    ],
)
def test_fsm_allows_each_exact_next_state(current: str, target: str) -> None:
    runner = _load_runner()
    row = _credential_row(runner, state=getattr(runner.CredentialState, current))

    transitioned = runner.advance_credential(
        row,
        getattr(runner.CredentialState, target),
        observed_config_hash="config-001",
        checkpoint_id="checkpoint-001",
    )

    assert transitioned.state is getattr(runner.CredentialState, target)


def test_fsm_rejects_skipped_state_and_blocked_row() -> None:
    runner = _load_runner()

    with pytest.raises(ValueError):
        runner.advance_credential(
            _credential_row(runner),
            runner.CredentialState.TARGET_READY,
            observed_config_hash="config-001",
            checkpoint_id="checkpoint-001",
        )
    with pytest.raises(ValueError):
        runner.advance_credential(
            _credential_row(runner, state=runner.CredentialState.BLOCKED),
            runner.CredentialState.SOURCE_CONTAINED,
            observed_config_hash="config-001",
            checkpoint_id="checkpoint-001",
        )


@pytest.mark.parametrize(
    "target",
    ["TARGET_READY", "OLD_INVALID"],
)
def test_fsm_requires_a_checkpoint_for_irreversible_transitions(target: str) -> None:
    runner = _load_runner()
    state = (
        runner.CredentialState.SOURCE_CONTAINED
        if target == "TARGET_READY"
        else runner.CredentialState.CONFIG_CUTOVER
    )

    with pytest.raises(ValueError):
        runner.advance_credential(
            _credential_row(runner, state=state),
            getattr(runner.CredentialState, target),
            observed_config_hash="config-001",
            checkpoint_id=None,
        )


def test_fsm_rejects_a_stale_configuration_hash_and_is_idempotent_on_resume() -> None:
    runner = _load_runner()
    row = _credential_row(runner, state=runner.CredentialState.SOURCE_CONTAINED)

    with pytest.raises(ValueError):
        runner.advance_credential(
            row,
            runner.CredentialState.TARGET_READY,
            observed_config_hash="config-changed",
            checkpoint_id="checkpoint-001",
        )

    resumed = runner.advance_credential(
        row,
        runner.CredentialState.SOURCE_CONTAINED,
        observed_config_hash="config-001",
        checkpoint_id=None,
    )
    assert resumed is row


def test_fsm_allows_revoke_delete_without_a_future_consumer_only() -> None:
    runner = _load_runner()
    disposable = _credential_row(
        runner,
        state=runner.CredentialState.SOURCE_CONTAINED,
        disposition=runner.CredentialDisposition.REVOKE_DELETE,
        future_consumer=None,
    )

    invalidated = runner.advance_credential(
        disposable,
        runner.CredentialState.OLD_INVALID,
        observed_config_hash="config-001",
        checkpoint_id="checkpoint-002",
    )
    assert invalidated.state is runner.CredentialState.OLD_INVALID

    with pytest.raises(ValueError):
        runner.advance_credential(
            _credential_row(
                runner,
                state=runner.CredentialState.SOURCE_CONTAINED,
                disposition=runner.CredentialDisposition.REVOKE_DELETE,
                future_consumer="direct-cli",
            ),
            runner.CredentialState.OLD_INVALID,
            observed_config_hash="config-001",
            checkpoint_id="checkpoint-002",
        )


def test_fsm_serializes_provider_mutation_globally() -> None:
    runner = _load_runner()

    with (
        runner.provider_mutation_lock("provider-a"),
        pytest.raises(ValueError),
        runner.provider_mutation_lock("provider-b"),
    ):
        pass


def test_fsm_reconciles_a_receipt_first_orphan_only_after_postcondition() -> None:
    runner = _load_runner()
    manifest = {"indexed_receipt_ids": []}
    orphan = {"receipt_id": "receipt-001", "transition": "source-contained"}

    reconciled = runner.reconcile_receipt_first_orphan(
        manifest, orphan, postcondition_satisfied=True
    )

    assert reconciled["indexed_receipt_ids"] == ["receipt-001"]
    assert (
        runner.reconcile_receipt_first_orphan(reconciled, orphan, postcondition_satisfied=True)
        == reconciled
    )
    with pytest.raises(ValueError):
        runner.reconcile_receipt_first_orphan(manifest, orphan, postcondition_satisfied=False)


def test_fsm_resumes_an_interrupted_source_to_quarantine_transfer() -> None:
    runner = _load_runner()
    transfer = runner.QuarantineTransfer(source_present=True, pending_item_present=True)

    completed = runner.resume_quarantine_transfer(transfer)

    assert completed.source_present is False
    assert completed.pending_item_present is False
    assert completed.active_item_present is True


def test_fsm_releases_one_shot_old_witness_and_accepts_semantic_issuer_evidence() -> None:
    runner = _load_runner()
    witness = runner.OneShotWitness(b"synthetic-witness")

    assert witness.consume() == b"synthetic-witness"
    with pytest.raises(ValueError):
        witness.consume()
    assert runner.accepts_invalidation_evidence(
        {"kind": "issuer-revocation", "reference": "issuer-reference-001"}
    )


def _minimal_manifest() -> dict[str, object]:
    return {"schema": "spec-193/v1", "records": [], "receipt_index": []}


def test_store_session_rejects_unsafe_manifest_values_before_any_disk_write(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    root = tmp_path.resolve() / "private-state"

    with runner.private_store_session(root) as session:
        with pytest.raises(ValueError):
            session.write_manifest(
                {
                    "schema": "spec-193/v1",
                    "records": [{"note": SYNTHETIC_CANARY}],
                    "receipt_index": [],
                },
                expected_digest=None,
            )
        with pytest.raises(ValueError):
            session.write_manifest(
                {
                    "schema": "spec-193/v1",
                    "records": [{"source": str(Path("/") / "private" / "source")}],
                    "receipt_index": [],
                },
                expected_digest=None,
            )

        assert not session.paths.manifest.exists()


def test_store_normalizes_external_paths_without_retaining_them() -> None:
    runner = _load_runner()

    normalized = runner.normalize_home_path(
        Path("/") / "external" / "source", home=Path("/") / "home" / "operator"
    )

    assert normalized == "<external-path>"


def test_store_session_receipt_fsync_then_manifest_index_and_cas(tmp_path: Path) -> None:
    runner = _load_runner()
    root = tmp_path.resolve() / "private-state"

    with runner.private_store_session(root) as session:
        first_digest = session.write_manifest(_minimal_manifest(), expected_digest=None)
        committed = session.append_receipt_and_index(
            _valid_receipt(), expected_manifest_digest=first_digest
        )

        assert committed.manifest["receipt_index"] == [
            {"offset": 0, "sha256": committed.receipt_sha256}
        ]
        assert len(committed.receipt_sha256) == 64
        with pytest.raises(ValueError):
            session.write_manifest(_minimal_manifest(), expected_digest=first_digest)


def test_store_rejects_a_user_controlled_parent_symlink(tmp_path: Path) -> None:
    runner = _load_runner()
    target = tmp_path.resolve() / "target"
    target.mkdir()
    link = tmp_path.resolve() / "link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError):
        runner.ensure_private_store(link / "private-state")


def test_store_fails_closed_when_no_nofollow_primitive_is_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.delattr(runner.os, "O_NOFOLLOW", raising=False)

    with (
        pytest.raises(ValueError),
        runner.private_store_session(tmp_path.resolve() / "private-state"),
    ):
        pass


def test_fsm_blocked_row_prevents_selecting_the_next_provider() -> None:
    runner = _load_runner()
    blocked = _credential_row(runner, state=runner.CredentialState.BLOCKED)
    ready = _credential_row(runner)

    with pytest.raises(ValueError):
        runner.select_next_credential([blocked, ready])


def test_probe_policy_discards_fake_cli_stream_canaries_and_large_output() -> None:
    runner = _load_runner()
    fake_cli = (
        "import sys; "
        "sys.stdout.write('cutover-synthetic-canary-not-a-credential' * 4096); "
        "sys.stderr.write('x' * 70000)"
    )

    result = runner.run_bounded_probe(
        (sys.executable, "-c", fake_cli),
        timeout_seconds=2,
        allowed_executables=(sys.executable,),
    )

    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.output_discarded is True
    assert not hasattr(result, "stdout")
    assert not hasattr(result, "stderr")


def test_probe_policy_kills_the_fake_cli_process_group_on_timeout(tmp_path: Path) -> None:
    runner = _load_runner()
    marker = tmp_path.resolve() / "child-ran"
    child_code = (
        "from pathlib import Path; import time; time.sleep(1); "
        f"Path({str(marker)!r}).write_text('child-ran')"
    )
    parent_code = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        "time.sleep(5)"
    )

    result = runner.run_bounded_probe(
        (sys.executable, "-c", parent_code),
        timeout_seconds=0.1,
        allowed_executables=(sys.executable,),
    )

    assert result.timed_out is True
    time.sleep(0.3)
    assert not marker.exists()


@pytest.mark.parametrize(
    "unsafe_command",
    [
        "echo not-an-argument-array",
        ("sh", "-c", "echo no"),
        ("ctx7", "setup"),
        ("anything", "mcp"),
        ("anything", "setup", "agent"),
        ("env",),
        ("printenv",),
        ("anything", "--token=synthetic-value"),
        ("anything", "API_KEY=synthetic-value"),
    ],
)
def test_probe_policy_rejects_shell_mcp_environment_and_secret_argv(
    unsafe_command: object,
) -> None:
    runner = _load_runner()

    with pytest.raises(ValueError):
        runner.validate_probe_command(unsafe_command)


def test_probe_policy_enforces_the_64_kib_output_cap_without_capture() -> None:
    runner = _load_runner()

    with pytest.raises(ValueError):
        runner.run_bounded_probe(
            (sys.executable, "-c", "pass"),
            max_output_bytes=65537,
            allowed_executables=(sys.executable,),
        )


def test_acl_validation_rejects_an_extended_access_acl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.setattr(
        runner.os,
        "listxattr",
        lambda _path, **_kwargs: ["system.posix_acl_access"],
        raising=False,
    )

    with pytest.raises(ValueError):
        runner.validate_private_acl(tmp_path.resolve())


def test_probe_policy_fails_closed_without_an_exact_executable_allowlist() -> None:
    runner = _load_runner()

    with pytest.raises(ValueError):
        runner.run_bounded_probe((sys.executable, "-c", "pass"))


def test_acl_validation_fails_closed_without_a_native_inspection_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.delattr(runner.os, "listxattr", raising=False)
    monkeypatch.setattr(runner.sys, "platform", "linux")

    with pytest.raises(ValueError):
        runner.validate_private_acl(tmp_path.resolve())


class _AclStdout:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self, _limit: int) -> bytes:
        return self._payload


class _AclProcess:
    def __init__(self, payload: bytes) -> None:
        self.pid = 1
        self.stdout = _AclStdout(payload)

    def wait(self, timeout: float) -> int:
        del timeout
        return 0


def test_acl_validation_uses_bounded_native_macos_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.delattr(runner.os, "listxattr", raising=False)
    monkeypatch.setattr(runner.sys, "platform", "darwin")
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _AclProcess(b"drwx------@ fixture\n"),
    )

    runner.validate_private_acl(tmp_path.resolve())


def test_acl_validation_rejects_native_macos_acl_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.delattr(runner.os, "listxattr", raising=False)
    monkeypatch.setattr(runner.sys, "platform", "darwin")
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _AclProcess(
            b"drwx------+ fixture\n 0: group: staff allow read\n"
        ),
    )

    with pytest.raises(ValueError):
        runner.validate_private_acl(tmp_path.resolve())


def _write_preflight_baseline(root: Path) -> tuple[dict[str, object], str]:
    root.mkdir(mode=0o700)
    baseline: dict[str, object] = {
        "schema": "spec-193-preflight-baseline-v1",
        "created_at": "2026-07-23T00:00:00+00:00",
        "entries": [
            {
                "kind": "file",
                "index_status": "M",
                "worktree_status": "M",
                "path_fingerprint": "a" * 64,
                "size": 1,
                "mtime_ns": 1,
            }
        ],
        "entry_count": 1,
        "head_commit": "b" * 40,
        "notes": ["values-free"],
        "repo_token": "repo-001",
    }
    payload = json.dumps(baseline, sort_keys=True).encode("utf-8") + b"\n"
    manifest = root / "manifest.json"
    manifest.write_bytes(payload)
    os.chmod(manifest, 0o600)
    return baseline, hashlib.sha256(payload).hexdigest()


def test_bundle_upgrade_preserves_preflight_baseline_and_seeds_values_free_rows(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    root = tmp_path.resolve() / "private-state"
    baseline, baseline_digest = _write_preflight_baseline(root)

    upgraded_digest = runner.upgrade_external_bundle(
        root,
        expected_baseline_sha256=baseline_digest,
        runner_path=RUNNER_PATH,
    )
    document = json.loads((root / "manifest.json").read_text(encoding="utf-8"))

    assert document["schema"] == "spec-193-manifest-v1"
    assert document["baseline"] == baseline
    assert document["baseline_sha256"] == baseline_digest
    assert document["surfaces"] == []
    assert document["credentials"] == []
    assert document["receipt_index"] == []
    assert document["runner_sha256"] == hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest()
    assert len(upgraded_digest) == 64
    assert (root / "receipts.ndjson").stat().st_mode & 0o777 == 0o600
    assert (root / "runbook.md").stat().st_mode & 0o777 == 0o600

    assert (
        runner.upgrade_external_bundle(
            root,
            expected_baseline_sha256=baseline_digest,
            runner_path=RUNNER_PATH,
        )
        == upgraded_digest
    )


def test_bundle_upgrade_rejects_a_stale_or_replaced_baseline(tmp_path: Path) -> None:
    runner = _load_runner()
    root = tmp_path.resolve() / "private-state"
    _write_preflight_baseline(root)

    with pytest.raises(ValueError):
        runner.upgrade_external_bundle(
            root,
            expected_baseline_sha256="c" * 64,
            runner_path=RUNNER_PATH,
        )


def test_preflight_notes_allow_policy_labels_but_not_sensitive_assignments() -> None:
    runner = _load_runner()

    runner._validate_preflight_notes(["synthetic " + "can" + "ary policy label"])

    with pytest.raises(ValueError):
        runner._validate_preflight_notes(["api" + "_key" + "=" + "value"])


def test_preflight_baseline_allows_missing_metadata_for_missing_paths(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    root = tmp_path.resolve() / "private-state"
    baseline, _ = _write_preflight_baseline(root)
    entry = baseline["entries"][0]
    assert isinstance(entry, dict)
    entry["size"] = None
    entry["mtime_ns"] = None

    assert runner._validate_preflight_baseline(baseline)["entries"][0]["size"] is None
