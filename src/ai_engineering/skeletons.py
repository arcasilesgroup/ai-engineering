"""What `init` offers to write into somebody else's repository.

Seven files and not one more. Each is a skeleton with a TODO: marker per section: it is
written once, and from that second it belongs to the user. No later command touches
AGENTS.md or CONSTITUTION.md again — not `update`, not a migration.
"""

from __future__ import annotations

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

JUSTFILE = """# What `check` means here. CI never learns a language: it runs `just check`.

wired:
    ai-eng doctor

build:
    @echo "TODO: compile, package, sign"

lint:
    @echo "TODO: your linter"

test:
    @echo "TODO: your test runner"

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

CONFIG_TOML = """# The pin. It says which version of the framework governs this repository, and its
# diff in a pull request is the audit trail of what changed in governance.
[framework]
version = "{version}"

[record]
# The durable chain lives outside every clone, under ~/.ai-engineering/state/.
anchor_commits = true

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
redact = "strict"
"""

AI_GITIGNORE = """*
!.gitignore
!config.toml
"""

CHECK_YML = """name: check
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v5
      - uses: extractions/setup-just@v3
      - run: uv tool install ai-engineering==${{{{ env.PIN }}}}
        env:
          PIN: {version}
      - run: ai-eng doctor --ci
      - run: ai-eng audit verify --anchors
      - run: just check
"""
