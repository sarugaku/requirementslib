import os

from setuptools import find_packages, setup


thisdir = os.path.abspath(os.path.dirname(__file__))
version = os.environ["PACKAGE_VERSION"]


def my_function(other_list):
    entry = {"key": [{"matches": ["string 1", "string 2", "some_string"]}]}
    matches = entry["key"][0]["matches"]
    matches = [x for x in matches if "some_string" not in x]
    entry["key"][0]["matches"] = matches + other_list


setup(
    name="test_package_with_repeated_assignments",
    version=version,
    description="Test package with repeated assignments and version from environment",
    long_description="This is a package",
    install_requires=[
        "six",
    ],
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    zip_safe=False,
)
