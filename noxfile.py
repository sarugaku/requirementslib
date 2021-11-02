import re
from pathlib import Path

import nox

BASE_PATH = Path(__file__).resolve().parent
PACKAGE_ROOT = BASE_PATH / "src/requirementslib"


def find_version():
    version_file = PACKAGE_ROOT.joinpath("__init__.py").read_text()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


@nox.session
def tests(session: nox.Session):
    session.install("-e", ".[tests]")
    session.run("pytest", "-ra", "tests")


@nox.session
def coverage(session: nox.Session):
    session.install(".[tests]", "coveralls")
    session.run("coverage", "run", "-p", "-m", "pytest", "-ra", "tests")
    session.run("coverage combine")
    session.run("coveralls")


@nox.session
def build_docs(session: nox.Session):
    session.install(".[docs]")
    _current_version = find_version()
    minor = _current_version.split(".")[:2]
    docs_folder = (BASE_PATH / "docs").as_posix()
    if not docs_folder.endswith("/"):
        docs_folder += "/"
    args = ["--ext-autodoc", "--ext-viewcode", "-o", docs_folder]
    args.extend(["-A", "'Dan Ryan <dan@danryan.co>'"])
    args.extend(["-R", _current_version])
    args.extend(["-V", ".".join(minor)])
    args.extend(["-e", "-M", "-F", str(PACKAGE_ROOT)])
    print("Building docs...")
    session.run("sphinx-apidoc", *args)
