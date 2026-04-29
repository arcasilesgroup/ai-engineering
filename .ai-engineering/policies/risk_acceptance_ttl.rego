# spec-110 Phase 3 -- risk-acceptance TTL policy.
#
# Allow when `now < ttl_expires_at`, deny otherwise. RFC-3339 timestamps with
# the same `Z` timezone offset compare lexicographically in chronological
# order, which is what the policy_engine relies on (see its module docstring).
#
# Input shape:
#   { "ttl_expires_at": "<RFC-3339>", "now": "<RFC-3339>" }

package risk_acceptance_ttl

default allow := false

allow if input.now < input.ttl_expires_at

deny["risk acceptance TTL expired"] if input.now >= input.ttl_expires_at
