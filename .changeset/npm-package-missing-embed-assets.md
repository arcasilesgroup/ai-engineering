---
"ai-engineering": patch
---

npm install -g ai-engineering@2.2.1 was broken: `src/assets.ts` imports seven fixture scripts with `with { type: "file" }` from `scripts/.embed/`, but the npm `files` whitelist did not include it, so the tarball shipped without them and `ai-eng` aborted on first run ("Cannot find module '../scripts/.embed/..."). The whitelist now ships `scripts/.embed`; verified by installing the packed tarball and running `ai-eng --version` + `doctor`.
