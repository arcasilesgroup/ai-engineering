---
"ai-engineering": patch
---

The self-protect guard no longer carries a rule for `ai-eng adapt apply`: the `adapt` verb was removed in 3.2.0, so the rule guarded a command that no longer exists. `uninstall`, `wrap` and `config --remove` stay refused from inside a governed session.
