# spec-122 Phase C — tests for branch_protection policy.
#
# Coverage targets per spec: at least one allow case, one deny case, and
# one boundary case (empty / missing field) per policy. opa test must
# report >= 0.90 line coverage when run on this suite.

package branch_protection_test

import data.branch_protection
import rego.v1

# ---------------------------------------------------------------------------
# allow cases
# ---------------------------------------------------------------------------

test_allow_feature_branch if {
	branch_protection.allow with input as {"branch": "feat/spec-122", "action": "push"}
}

test_allow_dev_branch if {
	branch_protection.allow with input as {"branch": "dev/refactor", "action": "push"}
}

# ---------------------------------------------------------------------------
# deny cases
# ---------------------------------------------------------------------------

test_deny_main_push if {
	branch_protection.deny["push to protected branch denied"] with input as {"branch": "main", "action": "push"}
}

test_deny_master_push if {
	branch_protection.deny["push to protected branch denied"] with input as {"branch": "master", "action": "push"}
}

test_no_allow_for_main if {
	not branch_protection.allow with input as {"branch": "main", "action": "push"}
}

# ---------------------------------------------------------------------------
# boundary cases
# ---------------------------------------------------------------------------

test_no_allow_when_action_missing if {
	not branch_protection.allow with input as {"branch": "feat/x"}
}

test_no_allow_when_branch_empty if {
	# Empty string is a non-protected branch but action must still be "push".
	not branch_protection.allow with input as {"branch": "", "action": "fetch"}
}

test_protected_branch_set if {
	branch_protection.protected_branch["main"]
	branch_protection.protected_branch["master"]
}
