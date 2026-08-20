"""Write-once content for somebody else's repository.

`init` offers seven skeletons and not one more. Solution Intent has a separate seed API
because its assertions must come from the caller, never from a framework default. Every
file is written once and then belongs to the user. No later command touches AGENTS.md or
CONSTITUTION.md again — not `update`, not a migration.
"""

from __future__ import annotations

import json
import os
import secrets
import stat
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

from ai_engineering import intent

CLAUDE_MD = "@./AGENTS.md\n"

AGENTS_MD = """# How work happens here

TODO: one paragraph — what this repository is, for somebody who has just arrived.

Project identity, vocabulary and prohibitions live in CONSTITUTION.md. Read it first.

## The rules

1. No code before an approved plan (more than 3 files).
2. One commit, one change.
3. Never `--no-verify`. Never silence a linter, in any language.
4. No compatibility shims. Hard rename, hard delete; say it in the changelog.
5. Delete before you abstract.
6. Green gate before "done" — show the output.
7. Stuck twice, stop and say so.
8. No secrets, no personal data, no machine paths in committed files.
9. Explain it so somebody who does not code can follow.
10. KISS, YAGNI, DRY, SOLID, TDD, Clean Code, Clean Architecture — the criteria a review
    judges a diff by and a spec justifies a decision with, in one line each.
11. Monitoring, metrics and observability first. Nothing gets a URL until CI/CD, logs,
    traces, errors, health, an external check, a second path and security all pass, and
    each one passes with a command rather than an assertion.
12. A decision that always comes out the same is code, not a prompt. The third time the
    same judgement resolves the same way it becomes a script — and the prompt that made
    it goes away in the same commit. If it cannot be made to fail closed, it stays a
    prompt and you write down why.

## How to work

- `/ai-spec` writes the problem, the options and the chosen one to `specs/NNN-slug/`.
- `/ai-plan` turns that into numbered tasks, each with a check and a rollback.
- `/ai-ship` commits, opens the pull request and closes the work item.
- `/ai-debug`, `/ai-explore`, `/ai-research`, `/ai-review`, `/ai-note` are the rest.
- `just check` is what CI runs. Run it before you say something is done.

## What this repository runs on

TODO: the language, the package manager, the test runner, the deploy target.
TODO: how to run it locally, in the three commands it actually takes.

## What breaks if you get it wrong

TODO: the one system, dataset or customer that pays for a mistake here.
"""

CONSTITUTION_MD = """# Constitution

The identity of this project. Written by a person, for the agents and the people who
work here. `ai-eng doctor` fails while any TODO: marker remains.

## Mission

TODO: what this project is and why it exists, in one paragraph.

## Who it is for

TODO: who uses it, and who breaks if this breaks.

## Vocabulary

TODO: the five or six domain terms an outsider will get wrong. Define them here so
nobody has to guess.

## Never

TODO: the prohibitions. Not style preferences — the things that must not happen.

## Compliance gates

TODO: which regulation or audit applies. "None" is a valid answer and has to be written.

## Escalation

When a gate blocks: read the reason, fix it, or ask. Never skip it.
TODO: who to ask, and how.

## Phase

TODO: prototype, production or maintenance. It changes what is acceptable here.
"""

# lint, test and build for each stack `init` can name from a marker file in the repository
# root. A stack with no row here keeps its TODO: a command that is wrong is worse than a
# blank somebody fills in, and both of them fail `just check` until a person has read it.
# Failing loudly is the point — none of these is written with a flag that passes when the
# script is missing, because that is the green nobody earned.
RECIPES = {
    "python": ("ruff check .", "pytest -q", "uv build"),
    "node": ("npm run lint", "npm test", "npm run build"),
    "go": ("go vet ./...", "go test ./...", "go build ./..."),
    "rust": ("cargo clippy -- -D warnings", "cargo test", "cargo build --release"),
    "java": ("mvn -q checkstyle:check", "mvn -q test", "mvn -q package"),
    "ruby": ("bundle exec rubocop", "bundle exec rspec", "bundle exec rake build"),
    "dotnet": ("dotnet format --verify-no-changes", "dotnet test", "dotnet build -c Release"),
}

TODOS = {"lint": "your linter", "test": "your test runner", "build": "compile, package, sign"}

JUSTFILE = """# What `check` means here. CI never learns a language: it runs `just check`.
{found}
wired:
    ai-eng doctor

build:
{build}

lint:
{lint}

test:
{test}

# Identical in every repository, because scanners read files rather than languages.
# These two are the ones that genuinely are: static analysis needs a rule set per
# language and we do not ship a credible cross-language one, so add your own here.
security:
    gitleaks dir . --redact --no-banner --exit-code 1
    trivy fs --scanners vuln,license,misconfig --exit-code 1 --severity CRITICAL,HIGH,MEDIUM .

# The count comes from the tool that did the work, never from the file list — that
# prints the same number whether your linter ran or was replaced by `true`.
counts:
    @echo "RAN lint=TODO  # your linter's own count of files checked, never the file list"
    @echo "RAN tests=TODO  # your runner's own count of tests collected"

check: wired build lint test security counts
"""


def justfile(stacks: list[str]) -> str:
    """The recipes, with the commands for whatever was actually found in the repository.

    It shipped `@echo "TODO: your linter"` to every project in every language, which is a
    file nobody edits and a `just check` that passes while checking nothing. More than one
    stack means more than one line inside a recipe, in the order they were detected; no
    stack we can name means the TODO markers stay exactly as they were."""
    # The names that actually contributed, and the header is written from them rather than
    # from what was asked for: a file headed "Filled in for: cobol, python" carrying only
    # python's commands is the kind of claim this whole product exists to refuse.
    filled = [stack for stack in stacks if stack in RECIPES]
    lines: dict[str, list[str]] = {verb: [] for verb in TODOS}
    for stack in filled:
        # strict=True: a row here with two commands in it would silently lose one, and that
        # is a shipped justfile with no `build` recipe in a language nobody notices until CI
        # says so.
        for verb, command in zip(TODOS, RECIPES[stack], strict=True):
            lines[verb].append(f"    {command}")
    found = f"# Filled in for: {', '.join(filled)}.\n" if filled else ""
    return JUSTFILE.format(
        found=found,
        **{
            verb: "\n".join(rows) or f'    @echo "TODO: {TODOS[verb]}"'
            for verb, rows in lines.items()
        },
    )


CONFIG_TOML = """# The pin. It says which version of the framework governs this repository, and its
# diff in a pull request is the audit trail of what changed in governance.
[framework]
version = "{version}"

[record]
# The durable chain lives outside every clone, under ~/.ai-engineering/state/.

[guards]
loop_window = 6
loop_repeats = 3
loop_failures = 5
design_budget = 3

[observability]
# Where a person looks. Leave endpoint empty and only the local record is written.
provider = ""
endpoint = ""
signals = []
encoding = "json"
auth_header = ""
auth_env = ""
# `redact` is gone: the exporter always redacts, and there was never a second thing to
# choose. It used to accept "none", which sent every unlisted field verbatim.
"""

AI_GITIGNORE = """*
!.gitignore
!config.toml
!intent.md
!readiness.json
"""

INTENT_EXISTS = ("INTENT_ALREADY_EXISTS", "canonical Intent already exists")
INTENT_PATH_UNSAFE = ("INTENT_PATH_UNSAFE", "canonical Intent path is unsafe")
INTENT_WRITE_FAILED = ("INTENT_WRITE_FAILED", "canonical Intent could not be created")

_Identity = tuple[int, int, int]
_REPARSE_POINT = 0x400


def _seed_incomplete(problem: tuple[str, str]) -> intent.Validation:
    return intent.Validation("INCOMPLETE", *problem)


def _path_identity(path: Path, directory: bool) -> _Identity:
    info = path.lstat()
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    reparse = getattr(info, "st_file_attributes", 0) & _REPARSE_POINT
    if not expected or path.is_symlink() or reparse:
        raise PermissionError
    return info.st_dev, info.st_ino, info.st_mode


def _same_identity(path: Path, expected: _Identity, directory: bool = False) -> bool:
    try:
        return _path_identity(path, directory) == expected
    except OSError:
        return False


def _remove_owned(path: Path, expected: _Identity) -> bool:
    if not _same_identity(path, expected):
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False


def seed_intent(repository: Path, candidate: Mapping[str, Any]) -> intent.Validation:
    """Validate and create the caller-owned Intent once.

    Trust boundary: pre-P3 permits one cooperative repository writer; concurrent calls to
    this function are allowed. This is not a security boundary against another process or
    account that can mutate the repository mid-call, and it makes no crash-durability claim.
    Windows uses the same stdlib hard-link path (expected on NTFS); an unsupported filesystem
    returns INCOMPLETE and remains for the approved Windows CI install matrix to prove.
    """
    if not isinstance(repository, Path) or not isinstance(candidate, Mapping):
        return _seed_incomplete(intent.SCHEMA_INVALID)
    try:
        root = repository.resolve(strict=True)
        if Path(os.path.abspath(repository)) != root:
            return _seed_incomplete(INTENT_PATH_UNSAFE)
        _path_identity(root, directory=True)
        ai = root / ".ai"
        if os.path.lexists(ai):
            _path_identity(ai, directory=True)
        rendered = (
            json.dumps(candidate, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8")
        snapshot = json.loads(rendered)
    except (OSError, RuntimeError):
        return _seed_incomplete(INTENT_PATH_UNSAFE)
    except (TypeError, ValueError):
        return _seed_incomplete(intent.SCHEMA_INVALID)

    validated = intent.validate(snapshot, root)
    if validated.outcome != "PASS":
        return validated

    created_ai = False
    temporary_fd = -1
    temporary_id: _Identity | None = None
    committed = False
    temporary = ai / f".intent.md.seed-{secrets.token_hex(16)}"
    final = ai / "intent.md"
    try:
        try:
            ai.mkdir(mode=0o700)
            created_ai = True
        except FileExistsError:
            pass
        _path_identity(ai, directory=True)
        if os.path.lexists(final):
            try:
                _path_identity(final, directory=False)
            except OSError:
                return _seed_incomplete(INTENT_PATH_UNSAFE)
            return _seed_incomplete(INTENT_EXISTS)

        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        temporary_fd = os.open(temporary, flags, 0o600)
        opened = os.fstat(temporary_fd)
        temporary_id = opened.st_dev, opened.st_ino, opened.st_mode
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            return _seed_incomplete(INTENT_PATH_UNSAFE)
        remaining = memoryview(rendered)
        while remaining:
            written = os.write(temporary_fd, remaining)
            if written <= 0:
                raise OSError("Intent seed write made no progress")
            remaining = remaining[written:]
        os.fsync(temporary_fd)
        if not _same_identity(temporary, temporary_id):
            return _seed_incomplete(INTENT_PATH_UNSAFE)
        try:
            os.link(temporary, final, follow_symlinks=False)
        except FileExistsError:
            return _seed_incomplete(INTENT_EXISTS)
        if not _remove_owned(temporary, temporary_id):
            return _seed_incomplete(INTENT_WRITE_FAILED)
        final_info = os.fstat(temporary_fd)
        if (
            (final_info.st_dev, final_info.st_ino, final_info.st_mode) != temporary_id
            or final_info.st_nlink != 1
            or not _same_identity(final, temporary_id)
            or final.read_bytes() != rendered
        ):
            return _seed_incomplete(INTENT_WRITE_FAILED)
        revalidated = intent.validate(final, root)
        if revalidated.outcome != "PASS":
            return revalidated
        committed = True
        return intent.PASS
    except (OSError, NotImplementedError):
        return _seed_incomplete(INTENT_WRITE_FAILED)
    finally:
        if not committed and temporary_id is not None:
            _remove_owned(final, temporary_id)
            _remove_owned(temporary, temporary_id)
        if temporary_fd >= 0:
            os.close(temporary_fd)
        if not committed and temporary_id is not None:
            _remove_owned(final, temporary_id)
            _remove_owned(temporary, temporary_id)
        if created_ai and not committed:
            with suppress(OSError):
                ai.rmdir()


CHECK_YML = """name: check
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v5
      - run: uv tool install rust-just
      - run: uv tool install ai-engineering==${{{{ env.PIN }}}}
        env:
          PIN: {version}
      - run: ai-eng doctor --ci
      - run: ai-eng audit verify
      - run: just check
"""
