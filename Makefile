.PHONY: install run test clean

install:
	pip install -e ".[dev]"

run:
	python -m tktop.cli

test:
	pytest -v

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
