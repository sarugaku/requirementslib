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
    session.run("pytest", "-ra", "-x", "-v", "tests")


@nox.session
def coverage(session: nox.Session):
    session.install(".[tests]", "coveralls")
    session.run("pytest", "--cov=requirementslib", "-x", "-v", "-ra", "tests")
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


def _get_changelog() -> str:
    cmd = ["towncrier", "--draft"]
    changelog = subprocess.check_output(cmd).decode("utf-8")
    print(changelog)
    return changelog


@nox.session
def bump_version(session: nox.Session):
    new_version = _prebump(_current_version())
    _write_version(new_version)
    return new_version


@nox.session
def release(session: nox.Session):
    version = session.posargs[0]
    _write_version(parver.Version.parse(version))
    changelog = _get_changelog()
    session.run("towncrier", "--yes", "--version", version)
    git_commit_cmd = ["git", "commit", "-am", f"Release {version}"]
    git_tag_cmd = ["git", "tag", "-sa", version, "-m", changelog]
    session.run(*git_commit_cmd)
    session.run(*git_tag_cmd)
    session.run("git", "push")
    session.run("git", "push", "--tags")
