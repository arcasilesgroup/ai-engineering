.PHONY: test test-unit test-integration test-e2e

# Fail loud and honest. pipefail makes a pipeline return the first failing
# command's status (so `pytest ... | tee` reports pytest's exit, not tee's);
# -e aborts the recipe on the first error. Without this a piped test command
# can exit 0 while tests fail. bash is required for pipefail.
SHELL := bash
.SHELLFLAGS := -e -o pipefail -c

PYTEST ?= uv run pytest
# Parallel run via pytest-xdist. Bare `pytest <file>` stays serial for fast
# focused runs and `--pdb` debugging.
#   worksteal  — best load balance for many fast tests (unit).
#   loadscope  — groups a module's tests on one worker so module-scoped
#                fixtures (e.g. installed_project_ro, ~2s install) build once
#                per worker instead of rebuilding across workers (integration).
PAR ?= -n auto --dist worksteal
PAR_SCOPED ?= -n auto --dist loadscope

test:
	$(PYTEST) $(PAR_SCOPED)

test-unit:
	$(PYTEST) tests/unit $(PAR)

test-integration:
	$(PYTEST) tests/integration $(PAR_SCOPED)

# e2e is serial: only a handful of flows, xdist worker spawn would dominate.
test-e2e:
	$(PYTEST) tests/e2e
