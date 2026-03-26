---
id: sub-002
parent: spec-079
title: "Eliminate contexts/orgs"
status: planning
files: [".ai-engineering/contexts/orgs/", "src/ai_engineering/templates/.ai-engineering/contexts/orgs/", "src/ai_engineering/state/defaults.py", "tests/unit/test_state.py", ".ai-engineering/README.md", ".ai-engineering/state/decision-store.json"]
depends_on: []
---

# Sub-Spec 002: Eliminate contexts/orgs

## Scope

Remove the dead stub `contexts/orgs/` from templates, dogfood installation, ownership rules in defaults.py, and related tests. Document the removal in decision-store.json. Update README.md directory tree.

## Exploration

### What exists

**Dogfood directory**: `.ai-engineering/contexts/orgs/` contains a single file `README.md` (132 bytes, 1 line):
> Organization-wide conventions. Structure: `{org-name}/org.md` and `{org-name}/repos/{repo-name}.md`. Auto-detected from git remote.

**Template directory**: `src/ai_engineering/templates/.ai-engineering/contexts/orgs/` is an identical copy -- same single-file README with the same aspirational content. No implementation of the "auto-detected from git remote" feature exists anywhere in the codebase.

**Ownership rule**: `src/ai_engineering/state/defaults.py` line 70 defines:
```python
(".ai-engineering/contexts/orgs/**", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
```

**Live ownership-map.json**: `.ai-engineering/state/ownership-map.json` lines 38-42 contain the materialized entry:
```json
{"frameworkUpdate": "deny", "owner": "team-managed", "pattern": ".ai-engineering/contexts/orgs/**"}
```
This file is regenerated from `defaults.py` by the installer (`installer/phases/state.py`) and the doctor (`doctor/phases/state.py`). Removing the entry from `defaults.py` means the live file retains a stale pattern -- it will not cause a doctor failure (coverage check only validates `defaults -> live`, not the reverse), but it is dead weight. Must be removed for consistency.

**Test**: `tests/unit/test_state.py` lines 151-154, method `test_contexts_orgs_denied`:
```python
def test_contexts_orgs_denied(self) -> None:
    om = default_ownership_map()
    assert om.is_update_allowed(".ai-engineering/contexts/orgs/README.md") is False
    assert om.has_deny_rule(".ai-engineering/contexts/orgs/README.md") is True
```

**README directory tree**: `.ai-engineering/README.md` line 97 lists `orgs/` under `contexts/`. The template README at `src/ai_engineering/templates/.ai-engineering/README.md` line 97 has the same reference.

**decision-store.json**: Currently has 25 decisions (DEC-001 through DEC-025). The new decision will be DEC-026.

### What does NOT reference contexts/orgs

- Zero skills, agents, or CLI commands reference `contexts/orgs`.
- No installer phase creates or populates `contexts/orgs` content beyond template copy.
- The `orgs` grep hit in `watch.md` handlers (`gh api orgs/{org}/members`) is a GitHub API call unrelated to this directory -- it checks org membership for PR autonomy decisions.
- No updater logic references this path beyond the generic ownership map.

### Conclusion

`contexts/orgs/` is a dead stub -- an aspirational placeholder with zero implementation. All references are self-referential (the directory exists, so there is an ownership rule, so there is a test for the ownership rule). Removing all six touchpoints eliminates the dead code cleanly with no functional impact.
