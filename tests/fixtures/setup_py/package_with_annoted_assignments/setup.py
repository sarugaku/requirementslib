import os

from typing import Dict, List

from setuptools import find_packages, setup

# Test AnnAssign that isn't used
unused: str = "foo"
# Test AnnAssign with no Value
unused2: int
# Test AnnAssign where the target isn't a simple Name
os.requirementslib_unused: int = 1

extras_require: Dict[str, List[str]] = {
    "docs": ["sphinx", "sphinx-argparse"],
}
install_requires: List[str] = []

setup(
    name="a",
    version="a",
    description="a",
    packages=find_packages(),
    extras_require=extras_require,
    install_requires=install_requires,
)
