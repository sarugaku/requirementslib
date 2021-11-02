import os

import setuptools


thisdir = os.path.abspath(os.path.dirname(__file__))
version = "1.0.0"

testing_extras = ["coverage", "flaky"]

setuptools.setup(
    name="test_package",
    version=version,
    description="The Backend HTTP Server",
    long_description="This is a package",
    install_requires=["six"],
    tests_require=testing_extras,
    extras_require={"testing": testing_extras},
    package_dir={"": "src"},
    packages=["test_package"],
    include_package_data=True,
    zip_safe=False,
)
