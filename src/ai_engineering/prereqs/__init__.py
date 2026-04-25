"""Per-stack SDK prerequisite probes (spec-101 D-101-14).

Probe-only invariant: this package MUST NOT invoke any package-management or
provisioning verbs. Only canonical version-query argv shapes are permitted,
enforced statically by `tests/unit/test_no_forbidden_substrings.py` and
dynamically by the `_PROBE_ARGV_ALLOWLIST` audit in
`tests/unit/test_sdk_prereq_probes.py`.
"""
