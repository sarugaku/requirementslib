import codecs
import os
import re

from setuptools import find_packages, setup


def read_file(filename):
    """Read package file as text to get name and version."""
    # intentionally *not* adding an encoding option to open
    # see here:
    # https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(
        os.path.join(here, "src/package_with_function_call_as_name", filename), "r"
    ) as f:
        return f.read()


def find_version():
    """Only define version in one place."""
    version_file = read_file("__init__.py")
    version_match = re.search(r'^__version__ = ["\']([^"\']*)["\']', version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


def find_name():
    """Only define name in one place."""
    name_file = read_file("__init__.py")
    name_match = re.search(r'^__name__ = ["\']([^"\']*)["\']', name_file, re.M)
    if name_match:
        return name_match.group(1)
    raise RuntimeError("Unable to find name string.")


SETUP = {
    "name": find_name(),
    "version": "1.0.0",
    "author": "Test Package",
    "author_email": "test@author.package",
    "url": "https://fake.package/team/url.git",
    "packages": find_packages(),
    "install_requires": [],
    "extras_require": {"tests": ["pytest", "flake8"]},
    "license": "MIT",
    "description": "This is a fake package",
}


if __name__ == "__main__":
    setup(**SETUP)
