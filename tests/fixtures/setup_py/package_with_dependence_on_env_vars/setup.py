import os

from setuptools import find_packages, setup


extras_require = {
    "docs": ["sphinx", "sphinx-argparse"],
}

setup(
    name="a",
    version="1.0.0",
    description="a",
    packages=find_packages(),
    extras_require=extras_require,
    install_requires=extras_require["docs"] if "READTHEDOCS" in os.environ else [],
)
