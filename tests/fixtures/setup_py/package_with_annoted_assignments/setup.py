import os
from typing import Dict, List

from setuptools import find_packages, setup

extras_require: Dict[str, List[str]] = {
    "docs": ["sphinx", "sphinx-argparse"],
}
setup(
    name="a",
    version="a",
    description="a",
    packages=find_packages(),
    extras_require=extras_require,
    install_requires=[],
)
