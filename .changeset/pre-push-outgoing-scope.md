---
"ai-engineering": patch
---

The pre-push hook now scans for secrets only in the commits the push sends. It used to scan every ref in the clone, so a leak parked on a local `refs/archive/*` ref or in the stash blocked a push that never sent it. A ref the remote already has is measured from its old tip; a new ref is measured from the remote's base branch (`[git] base`, or the remote default), and when that branch is not in the clone the push is refused with the fetch to run. Deletions send nothing and several refs are one scan. The hook also stops naming a `.gitleaksrc.toml` the project does not have, which made gitleaks exit before scanning and was reported as a secret.
