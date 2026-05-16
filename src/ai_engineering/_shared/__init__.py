"""Cross-cutting shared services for ai_engineering (spec-134 D-134-09).

Modules here are intentionally framework-agnostic — they do not import
from `ai_engineering.state.*` or `ai_engineering.config.*` to avoid
circular dependencies. Consumers wire shared helpers from this package
into their own surfaces.
"""
