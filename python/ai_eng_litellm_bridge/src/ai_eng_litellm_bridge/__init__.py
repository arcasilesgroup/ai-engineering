"""ai-eng-litellm-bridge — Docker-isolated multi-LLM router.

Why Docker-isolated: the LiteLLM PyPI package was compromised in March
2026 (versions 1.82.7/8) leaking cloud credentials. We pin versions by
content hash, run unprivileged, and limit network egress to allowlisted
provider domains. ADR-0008 has the full rationale.

For `--profile=regulated`, this bridge is replaced by an in-cluster
TrueFoundry deployment.
"""

__version__ = "3.0.0a0"
