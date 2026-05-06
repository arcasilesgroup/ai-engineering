# spec-122 Phase C — risk-acceptance TTL policy.
#
# Allow when `now < ttl_expires_at`, deny otherwise. Uses the OPA
# `time.parse_rfc3339_ns` builtin for precise nanosecond comparison instead
# of the lexicographic string comparison the spec-110 mini-Rego engine
# relied on (which only worked for matched timezone offsets).
#
# Evaluated by OPA via `data.risk_acceptance_ttl.deny`.
#
# Input shape:
#   { "ttl_expires_at": "<RFC-3339>", "now": "<RFC-3339>" }

package risk_acceptance_ttl

import rego.v1

now_ns := time.parse_rfc3339_ns(input.now)

ttl_ns := time.parse_rfc3339_ns(input.ttl_expires_at)

default allow := false

allow if now_ns < ttl_ns

deny contains "risk acceptance TTL expired" if now_ns >= ttl_ns
