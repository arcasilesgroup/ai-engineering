"""spec_lint — CLI shim that validates spec.md against the schema contract.

Console entry: ``python -m spec_lint`` and ``spec_lint`` (registered
in ``pyproject.toml`` ``[project.scripts]``). Parallel surface to
``tools/skill_lint`` per spec-131 D-131-17; same exit-code conventions,
same pre-commit wiring pattern.
"""

from __future__ import annotations
