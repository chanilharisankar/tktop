# Plan: Ship `tktop` as a pip-installable CLI

## Goal

Make `tktop` installable with:

```bash
pip install tktop
```

and upgradeable with:

```bash
pip install -U tktop
```

The installed artifact should be a normal Python package that exposes a console
command named `tktop`.

## Important constraint

`pip` does not distribute a standalone native binary. It installs Python
packages and can generate command wrappers from entry points. If we want
`tktop` to be installed with `pip`, the right product is a packaged CLI, not a
single self-contained executable.

If we later want an actual binary for users who do not want Python installed,
that should be a separate release path.

## What already exists

- `pyproject.toml` already uses modern packaging metadata.
- `tktop` already exposes a console command via `[project.scripts]`.
- The app already has a single CLI entry point in `src/tktop/cli.py`.
- The repo already has a dev/test workflow and release-friendly layout.

## Packaging model

Keep the project as a standard Python distribution:

- `name = "tktop"` in `pyproject.toml`
- `tktop = "tktop.cli:app"` in `[project.scripts]`
- source layout under `src/tktop/`
- package metadata and dependencies in `pyproject.toml`
- MIT license already included

This gives us:

- `pip install tktop` to install
- `pip install -U tktop` to upgrade
- `pip uninstall tktop` to remove
- automatic shell wrappers for the `tktop` command through the entry-point
  mechanism

## Detailed implementation plan

### 1. Confirm package metadata is PyPI-ready

Check and tighten `pyproject.toml` so the published wheel has enough metadata:

- add a short `readme` field if needed
- add `authors`
- add `classifiers` for Python version and OS support
- keep `requires-python = ">=3.13"` if that is the real floor
- keep the MIT license reference
- keep runtime dependencies minimal and correct

Decide whether the PyPI package name stays `tktop` or is published under a
different PyPI name. If the name is already taken, choose a new distribution
name and keep the executable command as `tktop`.

### 2. Make the command install cleanly from wheels

Verify the CLI entry point is the only thing users need:

- `tktop.cli:app` should remain the console entry point
- the command should work from an installed wheel, not just from source
- startup should not require the repo root to be on `PYTHONPATH`

Run an install test from a clean virtual environment:

```bash
python -m venv /tmp/tktop-test
source /tmp/tktop-test/bin/activate
pip install tktop
tktop --help
```

### 3. Add packaging validation to CI

Add checks that mimic the user install path:

- build a wheel and an sdist
- install the wheel into a fresh virtualenv
- run `tktop --help`
- run a smoke test against the CLI import path

Useful commands:

```bash
python -m build
python -m pip install dist/*.whl
tktop --help
```

### 4. Publish to PyPI

Set up a release process that uploads both wheel and source distribution.

Recommended release flow:

1. bump version in `pyproject.toml`
2. tag the release in git
3. build artifacts
4. upload to TestPyPI first
5. verify install from TestPyPI
6. upload to PyPI

The Python Packaging User Guide recommends building both wheel and sdist and
using TestPyPI before the real upload.

### 5. Automate releases

Use GitHub Actions or equivalent CI to publish on tagged releases.

Prefer:

- build artifacts in CI
- publish only from a protected release workflow
- use trusted publishing if possible, or PyPI API tokens if not
- keep the release workflow separate from normal CI

This reduces manual release drift and makes upgrades predictable for users.

### 6. Document the user-facing install path

Update the README and release notes with:

- `pip install tktop`
- `pip install -U tktop`
- `tktop --help`
- supported Python version
- note that users should install into a virtual environment unless they know
  they want a global user install

### 7. Preserve dev install workflow

Keep the current source-tree workflow working for contributors:

- `pip install -e ".[dev]"`
- local test commands
- lint and security checks

The pip-distributed CLI should be additive, not a replacement for contributor
setup.

### 8. Decide whether to ship a separate standalone binary

If “binary” really means a single executable with no Python dependency, define a
second packaging path:

- PyInstaller build for desktop distribution
- release artifacts per platform
- separate download/install instructions

That is independent from the pip package and should not block the CLI package.

## Repo changes likely needed

- `pyproject.toml`
  - metadata cleanup
  - packaging metadata for PyPI
  - release notes references if desired
- `README.md`
  - user install and upgrade commands
- `.github/workflows/release.yml` or equivalent
  - build and publish releases
- `docs/`
  - release checklist and packaging notes

## Acceptance criteria

This is done when all of the following are true:

- `pip install tktop` installs the CLI successfully
- `tktop` appears on PATH inside the environment where it was installed
- `tktop --help` works from the installed package
- `pip install -U tktop` upgrades to a newer published version
- release artifacts can be built from CI and uploaded to PyPI
- contributor workflow from source still works

