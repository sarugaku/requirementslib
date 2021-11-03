import sys

from setuptools import setup


try:
    from non_existant_pkg import cmdclass
except ImportError:
    from distutils import log as logger

    logger.warn("Wheel is not available, disabling bdist_wheel hook")
    cmdclass = {}

try:
    import incompatible_pkg

    try:
        ver = incompatible_pkg.__version__
        raise Exception(
            "This package is incompatible with incompatible_pkg=={}. ".format(ver)
            + 'Uninstall it with "pip uninstall azure".'
        )
    except AttributeError:
        pass
except ImportError:
    pass

setup(
    name="fakepkg",
    version="0.1.0",
    description="Fake package",
    long_description=open("README.rst", "r").read(),
    license="MIT",
    author="Fake Author",
    author_email="Fake@fake.com",
    url="https://github.com/fake/fakepackage",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
    zip_safe=True,
    package_dir={"": "src"},
    packages=["fakepkg"],
    install_requires=[
        "azure-common>=1.1.5",
        "cryptography",
        "python-dateutil",
        "requests",
    ]
    + (["futures"] if sys.version_info < (3, 0) else []),
    cmdclass=cmdclass,
)
