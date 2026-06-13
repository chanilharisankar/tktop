.PHONY: install run test lint security audit check binary clean release

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

binary:
	pyinstaller --onefile --name tktop --paths src src/tktop/cli.py --add-data "src/tktop/tui/styles.tcss:tktop/tui"
	@echo "✅ Binary at dist/tktop ($(du -h dist/tktop | cut -f1))"

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info *.spec
	find . -type d -name __pycache__ -exec rm -rf {} +

release:
	@test -n "$(VERSION)" || (echo "VERSION is required, for example: make release VERSION=0.1.1"; exit 1)
	python3 scripts/release.py "$(VERSION)"
