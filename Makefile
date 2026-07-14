# Verification targets for the home-folder repo.
#
#   make check    run everything (tests, advisory drift report, secrets)
#   make test     pytest suites: .checks + agent hook tests
#   make drift    advisory alias/env-var drift report across bash/zsh/fish
#   make secrets  betterleaks scan of git history (skips if not installed)

PYTEST = uv run --no-project --with pytest pytest

.PHONY: check test drift secrets

check: test drift secrets

test:
	$(PYTEST) .checks .agents/hooks/tests

drift:
	python3 .checks/shell_drift_report.py

secrets:
	@if command -v betterleaks >/dev/null; then \
		betterleaks git --no-banner; \
	else \
		echo "betterleaks not installed; skipping secrets scan"; \
	fi
