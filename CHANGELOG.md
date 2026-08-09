# Changelog

Rule 4 of `AGENTS.md`: there are no compatibility shims here, so every hard rename and
every hard delete is written down in this file, in the words somebody upgrading would
search for.

## Unreleased

### Breaking changes

- `ai-eng init --project` no longer rewrites `.ai/config.toml` or `.ai/.gitignore`. It
  writes them when they are absent, says on its own line which one it left alone, and
  names `ai-eng update` as the only verb that changes the pin. It used to rewrite both on
  every run — taking a dated backup and printing a line — which reset the pinned version,
  the guard windows and the observability endpoint on every re-run, and made `ai-eng
  update`'s three consent gates reachable around. If you were re-running `init` to refresh
  the pin, run `ai-eng update`: it refuses on a dirty tree, refuses without a keyboard, and
  asks for a typed `y`.

- `ai-eng init` no longer prints `.github/workflows/check.yml` at you to paste. It writes
  the file, which means it is offered for overwrite like the other four when one is already
  there, and it lands in the receipt, so `ai-eng uninstall` removes the one we wrote and
  leaves the one you wrote. There is no flag to get the old paste-it-yourself behaviour
  back.

- `ai-eng accept` now requires `--by` and `--justification`. It used to write
  `TODO: a person, by name` and `TODO: why this is acceptable, in one sentence` into the
  record when they were omitted, and assertion 16 compared only the expiry date — so an
  accepted risk with no owner and no reason passed every gate this product has. An
  omitted `--follow-up` is now an empty field rather than a third marker. There is no
  shim and no deprecation period: the command exits 2 and names the four flags it needs.

- What makes a hook entry ours is now the dispatcher's own filename, `chain.py`, and no
  longer the hyphenated project name. The old mark could only reach an entry through the
  interpreter's path, which spells this package with an underscore under a wheel, so it
  worked under `uv tool` and `pipx` and was false everywhere at once under `pip` into a
  venv named anything else. If you installed that way, `ai-eng init` has been writing a
  duplicate guard entry on every run and `ai-eng uninstall` has been leaving your guards
  wired; run `ai-eng init --global --no-project` once after upgrading and both stop. There
  is no dual-marker fallback: entries written by 1.0.0 are recognised by the new signature
  because the dispatcher's path was always in them.

- `ai-eng spec new --ref` no longer prefills the spec. The flag still records the work
  item in the frontmatter and `/ai-ship` still closes it, but the heading is the slug and
  the problem statement is the author's to write. Nothing fetches the work item any more.
