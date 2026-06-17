---
name: tktop-release
description: Prepare and verify tktop releases. Use when Codex needs to inspect the current tktop package version, suggest or validate a target release version, run release checks, create release commits/tags, push release tags, or verify GitHub Actions/PyPI publication for the tktop repository.
---

# tktop Release

## Core Workflow

Use this skill for tktop release preparation and publication.

1. Start by running:
   ```bash
   python ~/.codex/skills/tktop-release/scripts/release_info.py --repo <repo>
   ```
   Report the current package version, latest release tag, dirty worktree state,
   and suggested next patch/minor/major versions.

2. If the user did not provide a target version, ask for it after showing the
   current version and suggestions.

3. Validate the target before changing files:
   ```bash
   python ~/.codex/skills/tktop-release/scripts/validate_target.py --repo <repo> <version>
   ```

4. Before a real release, run the repository checks:
   ```bash
   env PATH="<repo>/.venv/bin:$PATH" make check
   env PATH="<repo>/.venv/bin:$PATH" make package-test
   ```

5. For tktop, release publication is tag-driven:
   - update package metadata
   - commit the release bump
   - create `v<version>` tag
   - push `main` and the tag
   - verify the GitHub Release workflow and PyPI version with:
     ```bash
     python scripts/check_deployment.py <version> --wait --timeout 600
     ```

## Guardrails

- Do not overwrite unrelated worktree changes. Surface them before release.
- Do not include `.coverage`, `dist/`, virtualenvs, or generated build output in
  release commits.
- Prefer the repository’s existing release helper when it fits the requested
  flow, but inspect it first.
- If pushing a tag, state clearly that it can trigger GitHub Actions and PyPI
  publication.
- Verify deployment after publish with:
  ```bash
  python scripts/check_deployment.py <version>
  ```

## Bundled Scripts

- `scripts/release_info.py`: inspect current version, latest tag, worktree state,
  and suggested next versions.
- `scripts/validate_target.py`: validate a user-provided target version against
  the current repo and local tags.
- `scripts/check_deployment.py`: verify the pushed tag, GitHub Release workflow,
  and PyPI publication status for a version.
