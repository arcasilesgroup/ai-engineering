"""spec-152 Wave 1 — GitHub Actions workflow-policy gate correctness.

These tests harden ``scripts/check_workflow_policy.py`` against the fail-open
holes the spec-152 audit found:

* The generic trigger checks in ``main()`` used ``data.get("on")`` which misses
  PyYAML's boolean ``True`` key produced by a bare ``on:`` block — so a
  ``pull_request_target`` workflow with a bare ``on:`` slipped through (T-1/T-2).
* PR workflows could omit ``concurrency`` with no reviewed allowlist (T-3/T-4).
* Composite ``.github/actions/*/action.yml`` files were never scanned for SHA
  pinning (T-5/T-6).
* First-party org prefixes (``actions/`` etc.) were exempted from SHA pinning,
  so a retag attack on a first-party action was undetectable (T-7/T-8b).
* No off-hot-path reachability check existed for pinned SHAs (T-9).

The script lives at repo-root ``scripts/`` (not an importable package), so it is
loaded by file path via ``importlib`` — mirroring how the other workflow tests
treat repo-root tooling.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_workflow_policy.py"


def _load_policy_module() -> ModuleType:
    """Import ``scripts/check_workflow_policy.py`` by file path.

    The script is repo-root tooling, not a package member, so it is loaded
    fresh per session via ``importlib`` rather than ``import``.
    """
    spec = importlib.util.spec_from_file_location("check_workflow_policy", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def policy() -> ModuleType:
    return _load_policy_module()


@pytest.fixture
def workflows_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Create an empty ``.github/workflows`` + ``.github/actions`` tree and chdir into it.

    ``main()`` globs ``.github/workflows/*.yml`` and ``.github/actions/*/action.yml``
    relative to the process cwd, so each test gets an isolated tree to write
    fixtures into.
    """
    workflows = tmp_path / ".github" / "workflows"
    actions = tmp_path / ".github" / "actions"
    workflows.mkdir(parents=True)
    actions.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    yield workflows


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


# A minimal valid generic workflow body. Tests append/override pieces.
_VALID_BODY = """\
name: Example
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo hello
"""


def _load_yaml(policy: ModuleType, body: str) -> dict[str, Any]:
    return policy.yaml.safe_load(body)


# ---------------------------------------------------------------------------
# T-1 / T-2 — boolean ``on:`` key with ``pull_request_target`` must be rejected
# ---------------------------------------------------------------------------


def test_bare_on_pull_request_target_is_rejected(policy: ModuleType, workflows_dir: Path) -> None:
    """A bare ``on:`` block (PyYAML key ``True``) carrying ``pull_request_target``
    must be rejected by the generic policy.

    RED rationale: ``main()`` previously read ``data.get("on")`` which returns
    ``None`` for a bare ``on:`` block, so the ``pull_request_target`` ban was
    silently skipped. Driving through ``main()`` proves the live code path.
    """
    body = """\
name: Dangerous
on:
  pull_request_target:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo hello
"""
    _write(workflows_dir / "dangerous.yml", body)

    exit_code = policy.main([])

    assert exit_code == 1, (
        "main() must reject a bare-`on:` workflow declaring pull_request_target; "
        "a passing exit code means the data.get('on') fail-open hole is still present"
    )


def test_bare_on_pull_request_target_rejected_via_helper(
    policy: ModuleType,
) -> None:
    """The same rejection must be reachable through the pure per-workflow helper.

    ``check_generic_workflow_policy(workflow, data)`` is the SOLID refactor that
    makes per-fixture policy testing possible without filesystem juggling.
    """
    body = """\
name: Dangerous
on:
  pull_request_target:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo hello
"""
    data = _load_yaml(policy, body)
    failures = policy.check_generic_workflow_policy(Path("dangerous.yml"), data)

    assert any("pull_request_target" in f for f in failures), (
        f"helper must flag pull_request_target; got {failures}"
    )


def test_explicit_quoted_on_pull_request_target_is_rejected(
    policy: ModuleType,
) -> None:
    """Quoting ``"on":`` keeps the string key, and the ban must still fire."""
    body = """\
name: Dangerous
"on":
  pull_request_target:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo hello
"""
    data = _load_yaml(policy, body)
    failures = policy.check_generic_workflow_policy(Path("dangerous.yml"), data)
    assert any("pull_request_target" in f for f in failures), failures


def test_clean_workflow_passes_helper(policy: ModuleType) -> None:
    """A well-formed generic workflow yields no generic-policy failures."""
    data = _load_yaml(policy, _VALID_BODY)
    failures = policy.check_generic_workflow_policy(Path("example.yml"), data)
    assert failures == [], f"clean workflow should pass; got {failures}"


# ---------------------------------------------------------------------------
# T-3 / T-4 — pull_request workflow must declare concurrency unless allowlisted
# ---------------------------------------------------------------------------


def test_pull_request_workflow_without_concurrency_is_rejected(
    policy: ModuleType,
) -> None:
    """A ``pull_request``-triggered workflow without ``concurrency`` is rejected."""
    body = """\
name: NeedsConcurrency
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo hello
"""
    data = _load_yaml(policy, body)
    failures = policy.check_generic_workflow_policy(Path("needs-concurrency.yml"), data)
    assert any("concurrency" in f for f in failures), (
        f"PR workflow without concurrency must be flagged; got {failures}"
    )


def test_pull_request_workflow_allowlisted_for_concurrency_passes(
    policy: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An allowlisted filename skips the missing-concurrency failure."""
    filename = "allowlisted-pr.yml"
    monkeypatch.setitem(
        policy._CONCURRENCY_ALLOWLIST,
        filename,
        "test rationale # expires: 2099-01-01",
    )
    body = """\
name: Allowlisted
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo hello
"""
    data = _load_yaml(policy, body)
    failures = policy.check_generic_workflow_policy(Path(filename), data)
    assert not any("concurrency" in f for f in failures), (
        f"allowlisted workflow must not be flagged for missing concurrency; got {failures}"
    )


def test_concurrency_allowlist_empty_by_default(policy: ModuleType) -> None:
    """The allowlist ships empty — every PR workflow must really declare concurrency."""
    assert policy._CONCURRENCY_ALLOWLIST == {}, (
        "the concurrency allowlist must be empty by default (T-4a adds concurrency "
        f"to PR workflows instead); got {policy._CONCURRENCY_ALLOWLIST}"
    )


# ---------------------------------------------------------------------------
# T-5 / T-6 — composite action.yml SHA pinning
# ---------------------------------------------------------------------------


def test_composite_action_tag_pinned_use_is_rejected(
    policy: ModuleType, workflows_dir: Path
) -> None:
    """A composite ``runs.steps[].uses`` pinned to a tag (not a SHA) is rejected.

    RED rationale: composites were never globbed/scanned, so a tag-pinned
    ``uses:`` inside ``.github/actions/<x>/action.yml`` slipped through.
    """
    action_body = """\
name: Sample composite
description: tag-pinned external action
runs:
  using: composite
  steps:
    - uses: some-vendor/build-thing@v3
"""
    actions_dir = workflows_dir.parent / "actions"
    _write(actions_dir / "sample" / "action.yml", action_body)

    exit_code = policy.main([])
    assert exit_code == 1, (
        "main() must scan composite action.yml steps and reject a tag-pinned uses"
    )


def test_composite_sha_pinned_use_passes(policy: ModuleType, workflows_dir: Path) -> None:
    """A composite whose external ``uses:`` is SHA-pinned passes the scan."""
    sha = "a" * 40
    action_body = f"""\
name: Sample composite
description: sha-pinned external action
runs:
  using: composite
  steps:
    - uses: some-vendor/build-thing@{sha} # v3
"""
    actions_dir = workflows_dir.parent / "actions"
    _write(actions_dir / "sample" / "action.yml", action_body)

    exit_code = policy.main([])
    assert exit_code == 0, "a SHA-pinned composite must pass the policy check"


# ---------------------------------------------------------------------------
# T-7 / T-8b — first-party orgs are no longer SHA-pin exempt
# ---------------------------------------------------------------------------


def test_first_party_tag_pinned_action_is_rejected(policy: ModuleType) -> None:
    """``actions/checkout@v4`` (tag, not SHA) must be rejected once exemptions narrow.

    RED rationale: ``_FIRST_PARTY_PREFIXES`` previously exempted ``actions/`` so a
    mutable tag on a first-party action was undetectable.
    """
    body = """\
name: FirstPartyTag
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
"""
    data = _load_yaml(policy, body)
    failures = policy.check_generic_workflow_policy(Path("first-party.yml"), data)
    assert any("actions/checkout@v4" in f for f in failures), (
        f"a tag-pinned first-party action must be flagged; got {failures}"
    )


def test_first_party_prefixes_narrowed_to_empty(policy: ModuleType) -> None:
    """D-152-05 default: no org prefix is exempt from SHA pinning."""
    assert tuple(policy._FIRST_PARTY_PREFIXES) == (), (
        "spec-152 D-152-05 removes the first-party SHA-pin exemption entirely; "
        f"got {policy._FIRST_PARTY_PREFIXES}"
    )


def test_local_and_docker_uses_are_skipped(policy: ModuleType) -> None:
    """Local (``./``) and ``docker://`` refs are not SHA-pinnable and are skipped."""
    body = """\
name: LocalAndDocker
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: ./.github/actions/setup-env
      - uses: docker://alpine:3.20
"""
    data = _load_yaml(policy, body)
    failures = policy.check_generic_workflow_policy(Path("local.yml"), data)
    assert not any("SHA pinning" in f for f in failures), (
        f"local/docker uses must be skipped by the SHA check; got {failures}"
    )


# ---------------------------------------------------------------------------
# T-9 — opt-in SHA reachability check (off the PR hot path)
# ---------------------------------------------------------------------------


def test_extract_pinned_refs_collects_sha_pins(policy: ModuleType) -> None:
    """The pure ref-extraction core returns every SHA-pinned (repo, sha) pair."""
    sha = "b" * 40
    body = f"""\
name: Pinned
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@{sha} # v6.0.2
      - uses: ./.github/actions/setup-env
      - uses: docker://alpine:3.20
"""
    data = _load_yaml(policy, body)
    refs = policy.extract_pinned_refs(data)
    assert ("actions/checkout", sha) in refs, f"expected the SHA pin in {refs}"
    # Local and docker refs carry no upstream SHA to verify.
    assert all(repo not in ("", None) for repo, _ in refs), refs
    assert all(not repo.startswith("docker://") for repo, _ in refs), refs


def test_check_reachability_flags_unreachable_sha(
    policy: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreachable SHA fails the reachability check (git stubbed at the edge)."""
    reachable_sha = "c" * 40
    unreachable_sha = "d" * 40

    def fake_ls_remote(repo: str, ref: str) -> bool:
        return ref == reachable_sha

    monkeypatch.setattr(policy, "_ref_is_reachable", fake_ls_remote)

    refs = [("actions/checkout", reachable_sha), ("actions/setup-python", unreachable_sha)]
    failures = policy.check_reachability(refs)
    assert len(failures) == 1, f"exactly the unreachable SHA must fail; got {failures}"
    assert unreachable_sha in failures[0], failures


def test_check_reachability_all_reachable_passes(
    policy: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When every pinned SHA resolves, the reachability check returns no failures."""
    monkeypatch.setattr(policy, "_ref_is_reachable", lambda repo, ref: True)
    refs = [("actions/checkout", "e" * 40)]
    assert policy.check_reachability(refs) == []


def test_main_default_does_not_invoke_reachability(
    policy: ModuleType, workflows_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The PR hot path (default ``main()``) must stay regex-only — no git calls."""
    called = False

    def boom(*_args: object, **_kwargs: object) -> bool:
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(policy, "_ref_is_reachable", boom)
    sha = "f" * 40
    body = f"""\
name: Pinned
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@{sha} # v6.0.2
"""
    _write(workflows_dir / "pinned.yml", body)
    policy.main([])
    assert called is False, "default main() must not perform reachability git calls"
