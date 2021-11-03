import subprocess
from pathlib import Path

import nox
import parver

BASE_PATH = Path(__file__).resolve().parent
PACKAGE_ROOT = BASE_PATH / "src/requirementslib"
INIT_PY = PACKAGE_ROOT / "__init__.py"


@nox.session
def tests(session: nox.Session):
    session.install("-e", ".[tests]")
    session.run("pytest", "-ra", "tests")


@nox.session
def coverage(session: nox.Session):
    session.install(".[tests]", "coveralls")
    session.run("pytest", "--cov=requirementslib", "-ra", "tests")
    session.run("coveralls")


@nox.session
def docs(session: nox.Session):
    session.install(".[docs]")
    session.run("sphinx-build", "-b", "html", "docs", "docs/build/html")


@nox.session
def package(session: nox.Session):
    session.install("build", "twine")
    session.run("pyproject-build")
    session.run("twine", "check", "dist/*")


def _current_version() -> parver.Version:
    cmd = ["git", "describe", "--tags", "--abbrev=0"]
    ver = subprocess.check_output(cmd).decode("utf-8").strip()
    return parver.Version.parse(ver)


def _prebump(version: parver.Version) -> parver.Version:
    next_version = version.bump_release(index=2).bump_dev()
    print(f"[bump] {version} -> {next_version}")
    return next_version


def _write_version(v):
    lines = []
    with INIT_PY.open() as f:
        for line in f:
            if line.startswith("__version__ = "):
                line = f"__version__ = {repr(str(v))}\n".replace("'", '"')
            lines.append(line)
    with INIT_PY.open("w", newline="\n") as f:
        f.write("".join(lines))


@nox.session
def bump_version(session: nox.Session):
    new_version = _prebump(_current_version())
    _write_version(new_version)
    return new_version
