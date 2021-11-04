from setuptools import find_packages, setup

install_requires = ["requests"]


SETUP = {
    "name": "test_package",
    "version": "1.0.0",
    "author": "Test Package",
    "author_email": "test@author.package",
    "url": "https://fake.package/team/url.git",
    "packages": find_packages(),
    "install_requires": install_requires,
    "license": "MIT",
    "description": "This is a fake package",
}


if __name__ == "__main__":
    setup(**SETUP)
