---
"ai-engineering": patch
---

npm: drop the eight `ai-engineering-<target>` platform packages. They never
existed on the registry — OIDC trusted publishing cannot create a package
(npm: "Package must exist"), so every release died at their publish with
ENEEDAUTH while `ai-engineering` itself published fine. The launcher now runs
`src/` under the bun that `engines` already requires (the v0.13.0
`requires-python` contract, in npm terms), and the GitHub release keeps
shipping the eight compiled binaries for the client's CI.
