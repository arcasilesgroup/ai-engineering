# spec-122 Phase C — tests for risk_acceptance_ttl policy.

package risk_acceptance_ttl_test

import data.risk_acceptance_ttl
import rego.v1

# ---------------------------------------------------------------------------
# allow cases — TTL still in the future
# ---------------------------------------------------------------------------

test_allow_far_future if {
	risk_acceptance_ttl.allow with input as {
		"now": "2026-05-05T00:00:00Z",
		"ttl_expires_at": "2026-06-01T00:00:00Z",
	}
}

test_allow_one_minute_left if {
	risk_acceptance_ttl.allow with input as {
		"now": "2026-05-05T11:59:00Z",
		"ttl_expires_at": "2026-05-05T12:00:00Z",
	}
}

# ---------------------------------------------------------------------------
# deny cases — TTL in the past or now
# ---------------------------------------------------------------------------

test_deny_expired if {
	risk_acceptance_ttl.deny["risk acceptance TTL expired"] with input as {
		"now": "2026-05-05T00:00:00Z",
		"ttl_expires_at": "2026-04-01T00:00:00Z",
	}
}

test_deny_exactly_now if {
	risk_acceptance_ttl.deny["risk acceptance TTL expired"] with input as {
		"now": "2026-05-05T00:00:00Z",
		"ttl_expires_at": "2026-05-05T00:00:00Z",
	}
}

# ---------------------------------------------------------------------------
# boundary cases — different timezone offsets compare correctly
# ---------------------------------------------------------------------------

test_allow_across_timezones if {
	# now = 2026-05-05T12:00:00Z, ttl = 2026-05-05T13:00:00+00:00 -> 13Z
	risk_acceptance_ttl.allow with input as {
		"now": "2026-05-05T12:00:00Z",
		"ttl_expires_at": "2026-05-05T08:00:00-05:00",
	}
}

# Exercise the `default allow := false` fall-through line for full coverage.
test_default_allow_false_when_expired if {
	risk_acceptance_ttl.allow == false with input as {
		"now": "2026-06-01T00:00:00Z",
		"ttl_expires_at": "2026-05-01T00:00:00Z",
	}
}
