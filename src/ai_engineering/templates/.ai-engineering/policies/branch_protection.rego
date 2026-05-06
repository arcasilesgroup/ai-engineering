# spec-122 Phase C — branch protection policy.
#
# Deny pushes to the `main` and `master` branches; allow pushes to any other
# branch. Evaluated by OPA via `data.branch_protection.deny`.
#
# Input shape:
#   { "branch": "<branch-name>", "action": "<git-action>" }

package branch_protection

import rego.v1

# Helper: enumerate protected branches as a single rule rather than inline.
# Custom mini-Rego subset (spec-110) didn't allow user-defined helper rules;
# OPA proper does, so we factor the list out for clarity and extensibility.
protected_branch contains "main"

protected_branch contains "master"

default allow := false

allow if {
	input.action == "push"
	not protected_branch[input.branch]
}

deny contains "push to protected branch denied" if {
	input.action == "push"
	protected_branch[input.branch]
}
