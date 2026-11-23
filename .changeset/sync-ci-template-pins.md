---
"ai-engineering": patch
---

The Version Packages PR now carries the CI template pin: `bun run version-packages`
runs `changeset version` and then `scripts/sync-ci-template-pins.ts`, which rewrites
`AI_ENG_VERSION` in `templates/ci.yml.tpl` and `templates/azure-pipelines.yml.tpl`
from `package.json`. A bump can no longer leave the templates pinning the previous
release, and a template that loses its pin fails the release loudly instead of
shipping without one.
