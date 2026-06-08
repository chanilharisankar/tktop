.PHONY: install run test lint security audit check clean

install:
	pip install -e ".[dev]"

run:
	python -m tktop.cli

test:
	pytest -v

lint:
	ruff check src/ tests/

security:
	bandit -r src/tktop/ -q

audit:
	pip-audit

check: lint security test
	@echo "✅ All checks passed."

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
