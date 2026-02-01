.PHONY: format lint type policy check

CI_SHARED_ROOT ?= $(HOME)/projects/ci_shared
export PYTHONPATH := $(CI_SHARED_ROOT)$(if $(PYTHONPATH),:$(PYTHONPATH))
export PYTHONDONTWRITEBYTECODE := 1

SHARED_PYTEST_EXTRA = -W "ignore::ResourceWarning" -W "ignore::pytest.PytestUnraisableExceptionWarning"

# Include shared CI checks
include ci_shared.mk

format:
	isort --profile black $(FORMAT_TARGETS)
	black $(FORMAT_TARGETS)

lint:
	$(PYTHON) -m compileall src tests
	pylint -j 1 src tests

type:
	pyright src

policy:
	$(PYTHON) -m ci_tools.scripts.policy_guard

check: shared-checks
