# Verification targets for the home-folder repo.
#
#   make check    run everything (tests, advisory drift report, secrets)
#   make test     pytest suites: .checks + agent hook tests
#   make drift    advisory alias-drift report across bash/zsh/fish
#   make secrets  gitleaks scan of git history (skips if not installed)

PYTEST = uv run --no-project --with pytest pytest

.PHONY: check test drift secrets

check: test drift secrets

test:
	$(PYTEST) .checks .agents/hooks/tests

drift:
	python3 .checks/shell_drift_report.py

secrets:
	@if command -v gitleaks >/dev/null; then \
		gitleaks git --no-banner; \
	else \
		echo "gitleaks not installed; skipping secrets scan"; \
	fi
