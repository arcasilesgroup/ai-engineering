---
"ai-engineering": patch
---

`update` now reaches the machine half even when the repo is already current. A repo whose assets all match the binary returned from the sync plan before the declared surfaces' carriers and the git template dir were touched — so a machine that had lost its carrier, which is exactly the state `doctor` answers with "→ ai-eng update", could not be repaired by the verb it named: the remedy ran, printed "all N assets current — nothing to sync", and changed nothing. The machine-side work moved into its own step, and both paths run it.

What an existing install will notice: on a machine that lost a carrier (a wiped home, or `uninstall` at machine scope), `ai-eng update` now rewrites it and says which file it wrote, instead of reporting that nothing needed doing.
