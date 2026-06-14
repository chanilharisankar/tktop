"""Build and smoke-test the wheel without publishing it."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 -- runs fixed local build commands
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
VENV_DIR = ROOT / ".venvs" / "package-test"


def run(*args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=cwd, env=env, check=True)  # nosec B603


def main() -> int:
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    shutil.rmtree(VENV_DIR, ignore_errors=True)

    run(sys.executable, "-m", "build")

    wheels = sorted(DIST_DIR.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one wheel in {DIST_DIR}, found {len(wheels)}")

    run(sys.executable, "-m", "venv", str(VENV_DIR))

    python = VENV_DIR / "bin" / "python"
    tktop = VENV_DIR / "bin" / "tktop"
    run(str(python), "-m", "pip", "install", str(wheels[0]))

    smoke_home = VENV_DIR / "home"
    smoke_home.mkdir()
    smoke_env = {**os.environ, "HOME": str(smoke_home)}
    run(str(tktop), "--help", cwd=VENV_DIR, env=smoke_env)
    run(str(tktop), "config", "path", cwd=VENV_DIR, env=smoke_env)
    run(str(tktop), "config", "show", cwd=VENV_DIR, env=smoke_env)

    print(f"\nPackage smoke test passed: {wheels[0].name}")
    print(f"Run the packaged app with: {tktop}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
