from setuptools import find_packages, setup

inner = "quest"

SETUP = {
    "name": "test_package",
    "version": "1.0.0",
    "author": "Test Package",
    "author_email": "test@author.package",
    "url": "https://fake.package/team/url.git",
    "packages": find_packages(),
    "install_requires": [f"re{inner}s", "{}".format("six")],
    "extras_require": {"tests": ["pytest", "flake8"]},
    "license": "MIT",
    "description": "This is a fake package",
}


if __name__ == "__main__":
    setup(**SETUP)
