# Python environment modes (spec-101 D-101-12)

`ai-eng install` and `ai-eng doctor --fix --phase tools` honour the
`python_env.mode` value in `.ai-engineering/manifest.yml`. Three modes are
supported. The default flipped from `venv` to `uv-tool` in spec-101 because
worktree creation under `venv` triggered a multi-minute per-cwd `.venv`
re-install -- a friction-of-the-week complaint that the new default
eliminates.

## The three modes

### `uv-tool` (default, recommended)

```yaml
python_env:
  mode: uv-tool
```

Tools install **once** into `~/.local/share/uv/tools/`. Worktree creation
does not trigger any `.venv` work; the second worktree commit benchmark
(G-12) targets <30 s in this mode. Use this unless you have a hard
requirement that pins you to one of the alternatives.

**Trade-off**: tools live in your user home, not in the project. Removing a
project does not remove its tools. Run `uv tool list` and `uv tool uninstall`
manually to clean up.

### `venv` (legacy, opt-in)

```yaml
python_env:
  mode: venv
```

Restores the pre-spec-101 behaviour: a `.venv/` directory created next to
`pyproject.toml` in each cwd, populated by `uv sync` or `pip install`. Use
this when:

- Your team's tooling expects `source .venv/bin/activate`.
- You have policy that says "all dependencies live under the project
  directory" (audit, supply-chain, or ALPHA isolation requirements).
- You need a project-local cache for offline builds.

**Trade-off**: every new worktree triggers a `.venv` install on first run,
which can be slow and is the failure mode the new default avoids.

### `shared-parent` (worktree-aware)

```yaml
python_env:
  mode: shared-parent
```

Creates a single `.venv` at the **git repo root** and links it from each
worktree. Requires that the cwd lives inside a git repo so the parent can
be resolved. Use this when:

- You want a single `.venv` shared across worktrees but cannot adopt
  `uv-tool` (e.g., enterprise tools that pin to a venv path).
- You want predictable disk layout: one `.venv` per repo, regardless of
  how many worktrees you spin up.

**Trade-off**: the link mechanism varies per OS; Windows performance has
not yet been benchmarked end-to-end. Stick with `uv-tool` if 30-s worktree
turnaround on Windows is non-negotiable.

## Decision tree

```
                       Need worktree creation
                       to be < 30 s?
                            │
                  ┌─────────┴─────────┐
                yes                   no
                  │                   │
                  ▼                   ▼
       python_env.mode:        Need .venv at the
       uv-tool                 worktree level?
                                     │
                          ┌──────────┴──────────┐
                        yes                     no
                          │                     │
                          ▼                     ▼
              python_env.mode:           python_env.mode:
              venv                       shared-parent
```

## Migration commands

| From | To | Command |
|------|----|---------|
| pre-spec-101 default | `uv-tool` | edit manifest, run `ai-eng install --reconfigure` |
| `uv-tool` | `venv` (rollback) | edit `.ai-engineering/manifest.yml` -> `python_env.mode: venv`, then `ai-eng install --reconfigure` |
| `venv` | `shared-parent` | edit manifest, run `ai-eng doctor --fix --phase tools` |

`ai-eng doctor --fix --phase tools` reads the current `python_env.mode`
and runs only the probes relevant to that mode. In `mode=uv-tool` it
returns `not_applicable` for `_check_venv_health` because there is
nothing to check.

## Cross-references

- `.ai-engineering/manifest.yml > python_env.mode` -- the source of truth.
- `.ai-engineering/manifest.yml > required_tools` -- 15-key block (baseline
  + 14 stacks) consumed by both installer and doctor.
- D-101-12 (decision-store): why the default flipped.
- D-101-03 + D-101-13 (decision-store): `platform_unsupported` and
  `platform_unsupported_stack` governance with `unsupported_reason`.
- README.md (Migration -- spec-101 install contract): user-facing summary.
- CHANGELOG.md (most recent BREAKING entry): release-note copy.
- EXIT 80 / EXIT 81 -- the hard-fail exit codes that replace the previous
  silent pass; see CHANGELOG and README migration sections for the full
  contract.
