# Package marker for the spec-129 shared scripting libraries.
#
# The directory name is ``skill_scripts_lib`` (not ``_lib``) so this
# folder maps directly to a Python distribution-package name. Spec-129
# §14.1 and the plan's Phase 0 prose use ``_lib`` as shorthand for
# "internal helpers" sitting alongside the hot-path scripts; that label
# describes intent, not the importable identifier. The tests in
# ``tests/unit/scripts/_lib/`` pin the import path
# ``skill_scripts_lib.manifest_reader``, so the package is named to
# match. The parent directory ``.ai-engineering/scripts/skills/`` is
# placed on ``pythonpath`` via ``pyproject.toml`` so the package
# resolves at test-collection time. See spec-129 D-129-08 (test-first
# ordering) for the binding decision and AGENTS.md TDD iron law for the
# rule that the T-1 test contract is immutable.
