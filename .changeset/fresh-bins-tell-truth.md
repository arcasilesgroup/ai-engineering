---
"ai-engineering": patch
---

`ai-eng --version` and every guard now come from the package the install declares: an installed package runs the source under bun and never a compiled binary left beside it, and a dev checkout runs `dist/` only when the build stamp written by `bun run build` names the current `package.json` version, so an upgrade can no longer answer with an older release.
