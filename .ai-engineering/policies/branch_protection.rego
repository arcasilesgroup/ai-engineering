# spec-110 Phase 3 -- branch protection policy.
#
# Deny pushes to the `main` and `master` branches; allow pushes to any other
# branch. The policy receives an input shape of:
#
#   { "branch": "<branch-name>", "action": "<git-action>" }
#
# Evaluated by `ai_engineering.governance.policy_engine.evaluate`, which only
# supports `allow if`/`deny if` rules (no user-defined helper rules), so the
# main/master check is inlined via `or`.

package branch_protection

default allow := false

allow if input.action == "push" and input.branch != "main" and input.branch != "master"

deny["push to protected branch denied"] if input.action == "push" and (input.branch == "main" or input.branch == "master")
