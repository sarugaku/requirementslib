import os
import re

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with open(os.path.join(here, *parts), encoding="utf-8") as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="requirementslib",
    version=find_version("src", "requirementslib", "__init__.py"),
    package_dir={"": "src"},
    packages=find_packages(where="src", exclude=["docs*", "tests*", "tasks*"]),
    # I don't know how to specify an empty key in setup.cfg.
    package_data={
        "": ["LICENSE*", "README*"],
    },
)
