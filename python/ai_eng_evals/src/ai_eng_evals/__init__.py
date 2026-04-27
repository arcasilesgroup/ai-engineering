"""ai-eng-evals — CLEAR framework eval runners.

CLEAR (arXiv 2511.14136, November 2025):
    Cost / Latency / Efficacy / Assurance / Reliability

Implementation roadmap (Phase 6):
    - Promptfoo runner -> emits CLEAR-shaped JSON
    - DeepEval runner  -> emits CLEAR-shaped JSON
    - Aggregator       -> merges multi-run pass@k + cost-normalized accuracy
"""

__version__ = "3.0.0a0"
