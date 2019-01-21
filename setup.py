#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import os
import re
import sys

from setuptools import setup, find_packages, Command


here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with codecs.open(os.path.join(here, *parts), "r") as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


if sys.argv[-1] == "publish":
    os.system("python setup.py sdist bdist_wheel upload")
    sys.exit()


class UploadCommand(Command):
    """Support setup.py publish."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # self.status('Building Source distribution…')
        # os.system('{0} setup.py sdist'.format(sys.executable))
        self.status("Uploading the package to PyPi via Twine...")
        os.system("twine upload dist/*")
        self.status("Pushing git tags…")
        os.system(
            "git tag v{0}".format(find_version("src", "requirementslib", "__init__.py"))
        )
        os.system("git push origin --tags")
        sys.exit()


setup(
    name="requirementslib",
    version=find_version("src", "requirementslib", "__init__.py"),
    package_dir={'': 'src'},
    packages=find_packages(where="src", exclude=["docs*", "tests*", "tasks*"]),

    # I don't know how to specify an empty key in setup.cfg.
    package_data={
        '': ['LICENSE*', 'README*'],
    },
)
