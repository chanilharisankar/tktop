.PHONY: install run test lint security audit check package-test package-run binary clean release deployment-status

install:
	pip install -e ".[dev]"

run:
	python -m tktop.cli

test:
	pytest -v

lint:
	ruff check src/ tests/ scripts/

security:
	bandit -r src/tktop/ scripts/ -q

audit:
	pip-audit

check: lint security test
	@echo "✅ All checks passed."

package-test:
	python3 scripts/test_package.py

package-run: package-test
	.venvs/package-test/bin/tktop

binary:
	pyinstaller --onefile --name tktop --paths src src/tktop/cli.py --add-data "src/tktop/tui/styles.tcss:tktop/tui"
	@echo "✅ Binary at dist/tktop ($(du -h dist/tktop | cut -f1))"

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info *.spec
	find . -type d -name __pycache__ -exec rm -rf {} +

release:
	@test -n "$(VERSION)" || (echo "VERSION is required, for example: make release VERSION=0.1.1"; exit 1)
	python3 scripts/release.py "$(VERSION)"

deployment-status:
	python3 scripts/check_deployment.py $(VERSION)
