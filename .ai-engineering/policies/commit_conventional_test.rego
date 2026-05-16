# spec-122 Phase C — tests for commit_conventional policy.

package commit_conventional_test

import data.commit_conventional
import rego.v1

# ---------------------------------------------------------------------------
# allow cases
# ---------------------------------------------------------------------------

test_allow_feat_no_scope if {
	commit_conventional.allow with input as {"subject": "feat: add new feature"}
}

test_allow_feat_with_scope if {
	commit_conventional.allow with input as {"subject": "feat(spec-122): add OPA wiring"}
}

test_allow_breaking_change if {
	commit_conventional.allow with input as {"subject": "feat(api)!: breaking change"}
}

test_allow_fix_chore_docs_etc if {
	commit_conventional.allow with input as {"subject": "fix(deps): bump version"}
	commit_conventional.allow with input as {"subject": "chore: housekeeping"}
	commit_conventional.allow with input as {"subject": "docs(readme): clarify usage"}
	commit_conventional.allow with input as {"subject": "test: add coverage"}
	commit_conventional.allow with input as {"subject": "refactor: simplify"}
	commit_conventional.allow with input as {"subject": "perf: optimise hot path"}
	commit_conventional.allow with input as {"subject": "build: bump build deps"}
	commit_conventional.allow with input as {"subject": "ci: tweak workflow"}
	commit_conventional.allow with input as {"subject": "style: formatting"}
	commit_conventional.allow with input as {"subject": "revert: undo prior change"}
}

# ---------------------------------------------------------------------------
# deny cases
# ---------------------------------------------------------------------------

test_deny_freeform if {
	commit_conventional.deny["commit subject must follow conventional format"] with input as {"subject": "fixed the thing"}
}

test_deny_unknown_type if {
	commit_conventional.deny["commit subject must follow conventional format"] with input as {"subject": "wibble: not a real type"}
}

test_deny_missing_description if {
	commit_conventional.deny["commit subject must follow conventional format"] with input as {"subject": "feat:"}
}

# ---------------------------------------------------------------------------
# boundary cases
# ---------------------------------------------------------------------------

test_deny_empty_subject if {
	commit_conventional.deny["commit subject must follow conventional format"] with input as {"subject": ""}
}

# Exercise the `default allow := false` line so opa coverage hits 100%.
test_default_allow_false_when_no_match if {
	commit_conventional.allow == false with input as {"subject": "not a conventional subject"}
}
