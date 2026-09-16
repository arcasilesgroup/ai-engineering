---
"ai-engineering": patch
---

The session can write its own artifacts again: `self-protect` was denying the session everything under `.ai-engineering/`.

That protection was a plain directory literal, so it covered every child of the directory — the four milestone slots (`spec.html`, `plan.html`, `brainstorm.md`, `recap.html`), the receipts, the cache, and the artifacts the canon's own nodes promise in their `Writes:`: `ai-research` writes `research/NNN-{name}.html`, `ai-security` writes `security/run-N/findings.json` and `REPORT.md`, `ai-design` writes `design/direction.html`. Nothing else writes those files, so the guard denied the only writer there is — a `brainstorm.md` came back as "this file governs you", and a research or security node could not leave the artifact its own contract requires. It also shadowed the pin check: an approved contract is frozen by the sha256 in the lock, and that check was never reached while the directory literal answered first.

The fence is now the machinery and only the machinery: the four files the chain itself reads (`config.toml`, `overrides.toml`, `ai-eng.lock`, `arch.rules.json`), the git floor, the machine-side canon and carriers, and `spec.html` once its sha256 is in the lock. Everything else under the directory is the session's own material. The directory itself is matched as a terminal segment, never a prefix — `rm -rf .ai-engineering` names the machinery in one word and stays denied, while `.ai-engineering/research/002.html` is not the directory and is a write like any other.

The four slot names still live in one place, `src/shared-slots.ts`, because `spec` sweeps them at `spec close`; the guard no longer needs the list, since it no longer carves an exemption out of a directory literal.
