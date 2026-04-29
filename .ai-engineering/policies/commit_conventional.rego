# spec-110 Phase 3 -- commit conventional-format policy.
#
# Allow only commit subjects matching the Conventional Commits regex:
#
#   <type>(<optional-scope>): <description>
#
# where <type> is one of feat|fix|chore|docs|test|refactor|perf|build|ci|style|revert.
# Input shape: { "subject": "<commit-subject-line>" }.

package commit_conventional

default allow := false

allow if regex.match("^(feat|fix|chore|docs|test|refactor|perf|build|ci|style|revert)(\\([^)]+\\))?: .+", input.subject)

deny["commit subject must follow conventional format"] if not regex.match("^(feat|fix|chore|docs|test|refactor|perf|build|ci|style|revert)(\\([^)]+\\))?: .+", input.subject)
