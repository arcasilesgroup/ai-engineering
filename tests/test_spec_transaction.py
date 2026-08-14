"""Native filesystem boundaries for governed spec publication."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ai_engineering import spec_transaction as transaction


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".ai").mkdir(parents=True)
    (root / ".ai" / "intent.md").write_bytes(b'{"authority":"local"}\n')
    (root / "specs").mkdir()
    return root


def test_native_spec_transaction_is_locked_staged_noreplace_and_alias_safe(tmp_path):
    root = _root(tmp_path)
    body = b'---\nid: "001"\nstatus: draft\n---\n'

    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        competing_writer = transaction.writer(root, ".ai/intent.md", "specs")
        with pytest.raises(transaction.Busy), competing_writer:
            pass
        observed = writer.read(".ai/intent.md", maximum=100)
        assert observed.body == b'{"authority":"local"}\n'
        pending = writer.stage("pending-first", "spec.md", body)
        published = writer.publish(pending, "001-first")
        assert published.name == "001-first"

    assert (root / "specs" / "001-first" / "spec.md").read_bytes() == body
    assert sorted(path.name for path in (root / "specs").iterdir()) == ["001-first"]
    assert not list(root.rglob(".ai-eng-spec-*"))

    detached = root / "detached-specs"
    external = tmp_path / "external-specs"
    external.mkdir()
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        if os.name == "nt":
            with pytest.raises(OSError):
                (root / "specs").rename(detached)
        else:
            (root / "specs").rename(detached)
            (root / "specs").symlink_to(external, target_is_directory=True)
            with pytest.raises(transaction.Unsafe):
                writer.stage("pending-alias", "spec.md", body)
    assert list(external.iterdir()) == []


def test_native_publish_collision_preserves_foreign_final_and_owned_pending(tmp_path):
    root = _root(tmp_path)
    foreign = root / "specs" / "001-collision"
    foreign.mkdir()
    (foreign / "foreign.txt").write_bytes(b"foreign\n")

    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage("pending-collision", "spec.md", b"owned pending\n")
        with pytest.raises(transaction.Collision):
            writer.publish(pending, "001-collision")

    assert (foreign / "foreign.txt").read_bytes() == b"foreign\n"
    assert (root / "specs" / "pending-collision" / "spec.md").read_bytes() == b"owned pending\n"


@pytest.mark.skipif(os.name != "posix", reason="FIFO is a POSIX boundary")
def test_native_read_is_bounded_nonblocking_and_tracks_parent_generation(tmp_path):
    root = _root(tmp_path)
    target = root / "specs" / "001-fifo"
    target.mkdir()
    fifo = target / "spec.md"
    os.mkfifo(fifo)

    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        with pytest.raises(transaction.Unsafe):
            writer.read("specs/001-fifo/spec.md", maximum=100)
        with pytest.raises(transaction.Unsafe):
            writer.read(".ai/intent.md", maximum=3)
        observed = writer.read(".ai/intent.md", maximum=100)
        assert {parent.path for parent in observed.parents} == {".", ".ai"}
        assert writer.unchanged(observed)
        root.joinpath(".ai", "intent.md").write_bytes(b'{"authority":"changed"}\n')
        assert not writer.unchanged(observed)


def test_unsupported_native_publish_preserves_pending_without_final_mutation(tmp_path, monkeypatch):
    root = _root(tmp_path)

    def unavailable(*args):
        raise transaction.Unsupported("exclusive rename unavailable")

    monkeypatch.setattr(transaction, "_publish_noreplace", unavailable)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage("pending-unsupported", "spec.md", b"pending\n")
        with pytest.raises(transaction.Unsupported):
            writer.publish(pending, "001-unsupported")

    assert not (root / "specs" / "001-unsupported").exists()
    assert (root / "specs" / "pending-unsupported" / "spec.md").read_bytes() == b"pending\n"


def test_backend_exposes_no_pathname_cleanup_surface():
    assert not any(
        hasattr(transaction, name)
        for name in ("cleanup", "unlink", "rmdir", "rmtree", "remove_pending")
    )


@pytest.mark.parametrize("injected", ["flush", "verify"])
def test_successful_native_rename_has_no_fallible_postcommit_operation(
    tmp_path, monkeypatch, injected
):
    root = _root(tmp_path)
    body = b"prebuilt result\n"

    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage(f"pending-{injected}", "spec.md", body)

        def fail_after_rename(*args):
            raise transaction.Unsafe("injected postcommit failure")

        if injected == "flush":
            monkeypatch.setattr(transaction, "_fsync", fail_after_rename)
        else:
            monkeypatch.setattr(writer, "verify", fail_after_rename, raising=False)
        published = writer.publish(pending, f"001-{injected}")

    assert published.name == f"001-{injected}"
    assert (root / "specs" / published.name / "spec.md").read_bytes() == body


def test_common_publish_seam_covers_posix_and_windows_branches(monkeypatch):
    calls = []

    def posix(*args):
        calls.append(("posix", args))

    def windows(*args):
        calls.append(("windows", args))

    monkeypatch.setattr(transaction, "_rename_noreplace_posix", posix)
    monkeypatch.setattr(transaction, "_win_publish", windows, raising=False)

    transaction._publish_noreplace("posix", 10, "pending", 11, "final")
    transaction._publish_noreplace("windows", 20, None, 21, "final")

    assert calls == [
        ("posix", (10, "pending", 11, "final")),
        ("windows", (20, 21, "final")),
    ]


def test_windows_publish_contract_closes_child_before_rename_and_consumes(monkeypatch):
    calls = []
    state = transaction._PendingHandles(directory=20, child=30)

    monkeypatch.setattr(
        transaction,
        "_publish_noreplace",
        lambda *args: calls.append(("rename", args)),
    )
    transaction._publish_windows_pending(
        state,
        21,
        "final",
        lambda handle: calls.append(("close", handle)) or True,
    )

    assert calls == [
        ("close", 30),
        ("rename", ("windows", 20, None, 21, "final")),
    ]
    assert state.child == 0
    assert state.consumed
    with pytest.raises(transaction.Unsafe):
        transaction._publish_windows_pending(state, 21, "again", lambda handle: True)


def test_windows_close_failure_preserves_recoverable_pending_without_rename(monkeypatch):
    calls = []
    state = transaction._PendingHandles(directory=20, child=30)
    monkeypatch.setattr(
        transaction,
        "_publish_noreplace",
        lambda *args: calls.append(("rename", args)),
    )

    with pytest.raises(transaction.Unsafe):
        transaction._publish_windows_pending(
            state,
            21,
            "final",
            lambda handle: calls.append(("close", handle)) or False,
        )

    assert calls == [("close", 30)]
    assert state.child == 30
    assert not state.consumed


def test_windows_collision_consumes_pending_and_cannot_retry(monkeypatch):
    calls = []
    state = transaction._PendingHandles(directory=20, child=30)

    def collide(*args):
        calls.append(args)
        raise transaction.Collision("foreign final")

    monkeypatch.setattr(transaction, "_publish_noreplace", collide)
    with pytest.raises(transaction.Collision):
        transaction._publish_windows_pending(state, 21, "final", lambda handle: True)

    assert state.child == 0
    assert state.consumed
    with pytest.raises(transaction.Unsafe):
        transaction._publish_windows_pending(state, 21, "retry", lambda handle: True)
    assert calls == [("windows", 20, None, 21, "final")]


def test_windows_identity_contract_is_128_bit_file_id_and_64_bit_volume():
    source = Path(transaction.__file__).read_text(encoding="utf-8")
    assert "class _FILE_ID_INFO" in source
    assert "ctypes.c_ulonglong" in source
    assert "_BY_HANDLE_FILE_INFORMATION" not in source
    raw = bytes(range(1, 17))
    assert transaction._stable_windows_identity((1 << 64) - 1, raw) == (
        (1 << 64) - 1,
        int.from_bytes(raw, "little"),
    )
    with pytest.raises(transaction.Unsupported):
        transaction._stable_windows_identity(1, b"legacy64")


def test_transaction_home_is_one_exact_canonical_component(tmp_path):
    root = _root(tmp_path)
    (root / "specs" / "nested").mkdir()

    with (
        pytest.raises(transaction.Unsafe),
        transaction.writer(root, ".ai/intent.md", "specs/nested"),
    ):
        pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor accounting")
def test_failed_intermediate_walk_does_not_leak_descriptors(tmp_path):
    root = _root(tmp_path)
    before = len(os.listdir("/dev/fd"))

    for _attempt in range(50):
        with (
            pytest.raises(transaction.Unsafe),
            transaction.writer(root, ".ai/missing/intent.md", "specs"),
        ):
            pass

    assert len(os.listdir("/dev/fd")) <= before + 1


@pytest.mark.skipif(os.name != "posix", reason="POSIX spelling probe")
def test_posix_walk_rejects_case_alias_spelling_when_filesystem_resolves_it(tmp_path):
    root = tmp_path / "CaseRoot"
    (root / ".ai").mkdir(parents=True)
    (root / ".ai" / "intent.md").write_bytes(b"authority\n")
    (root / "specs").mkdir()
    alias = tmp_path / "caseroot"
    if not alias.is_dir():
        pytest.skip("filesystem is case-sensitive")

    with pytest.raises(transaction.Unsafe), transaction.writer(alias, ".ai/intent.md", "specs"):
        pass


@pytest.mark.skipif(os.name != "nt", reason="Windows native contract")
def test_windows_publish_closes_child_consumes_pending_and_rejects_junction(tmp_path):
    root = _root(tmp_path)
    body = b"windows native\n"
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage("pending-windows", "spec.md", body)
        published = writer.publish(pending, "001-windows")
        with pytest.raises(transaction.Unsafe):
            writer.publish(pending, "002-reused")
    assert (root / "specs" / published.name / "spec.md").read_bytes() == body

    junction = tmp_path / "junction-root"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(root)],
        capture_output=True,
        check=False,
        text=True,
    )
    if created.returncode:
        pytest.fail(f"junction creation failed: {created.stderr or created.stdout}")
    with pytest.raises(transaction.Unsafe), transaction.writer(junction, ".ai/intent.md", "specs"):
        pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX native contract")
def test_posix_root_and_pending_aliases_are_never_write_targets(tmp_path):
    root = _root(tmp_path)
    external = tmp_path / "external"
    external.mkdir()
    root_alias = tmp_path / "root-alias"
    root_alias.symlink_to(root, target_is_directory=True)

    with (
        pytest.raises(transaction.Unsafe),
        transaction.writer(root_alias, ".ai/intent.md", "specs"),
    ):
        pass

    (root / "specs" / "pending-alias").symlink_to(external, target_is_directory=True)
    active_writer = transaction.writer(root, ".ai/intent.md", "specs")
    with active_writer as writer, pytest.raises(transaction.Collision):
        writer.stage("pending-alias", "spec.md", b"must not escape\n")
    assert list(external.iterdir()) == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX native contract")
@pytest.mark.parametrize(
    "platform,symbol,expected", [("linux", "renameat2", 1), ("darwin", "renameatx_np", 4)]
)
def test_posix_publish_selects_the_platform_exclusive_flag(monkeypatch, platform, symbol, expected):
    calls = []

    class Function:
        def __call__(self, *args):
            calls.append(args)
            return 0

    function = Function()
    library = type("Library", (), {symbol: function})()
    monkeypatch.setattr(transaction.sys, "platform", platform)
    monkeypatch.setattr(transaction.ctypes, "CDLL", lambda *args, **kwargs: library)

    transaction._rename_noreplace_posix(10, "pending", 11, "final")

    assert calls == [(10, b"pending", 11, b"final", expected)]
