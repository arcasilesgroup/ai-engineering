# spec-122 Phase C — commit conventional-format policy.
#
# Allow only commit subjects matching the Conventional Commits regex:
#
#   <type>(<optional-scope>): <description>
#
# where <type> is one of feat|fix|chore|docs|test|refactor|perf|build|ci|style|revert.
# Input shape: { "subject": "<commit-subject-line>" }.
#
# Evaluated by OPA via `data.commit_conventional.deny`.

package commit_conventional

import rego.v1

# Single source of truth for the conventional-commits subject pattern. Keep
# this in sync with the equivalent regex baked into the Python fallback in
# `src/ai_engineering/policy/checks/commit_msg.py` (the `_CONVENTIONAL_RE`
# constant); the OPA policy is the canonical definition.
conventional_pattern := `^(feat|fix|chore|docs|test|refactor|perf|build|ci|style|revert)(\([^)]+\))?!?: .+`

default allow := false

allow if regex.match(conventional_pattern, input.subject)

deny contains "commit subject must follow conventional format" if {
	not regex.match(conventional_pattern, input.subject)
}
