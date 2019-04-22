# -*- coding=utf-8 -*-

import os
import sys

import pip_shims.shims
import pytest
import vistir

from requirementslib.models.requirements import Requirement


@pytest.mark.parametrize(
    "test_artifact",
    [
        {"name": "environ_config", "as_artifact": False},
        {"name": "environ_config", "as_artifact": True},
    ],
    indirect=True,
)
def test_local_req(test_artifact):
    r = Requirement.from_line(test_artifact.as_posix())
    assert r.name == "environ_config"
    setup_dict = r.req.setup_info.as_dict()
    assert sorted(list(setup_dict.get("requires").keys())) == ["attrs"]


@pytest.mark.parametrize(
    "url_line, name, requires",
    [
        [
            "https://github.com/requests/requests/archive/v2.20.1.zip",
            "requests",
            ["urllib3", "chardet", "certifi", "idna"],
        ],
        [
            "https://github.com/dropbox/pyannotate/archive/v1.0.4.zip",
            "pyannotate",
            ["six", "mypy-extensions", "typing"],
        ],
    ],
)
@pytest.mark.needs_internet
def test_remote_req(url_line, name, requires):
    r = Requirement.from_line(url_line)
    assert r.name == name
    setup_dict = r.req.setup_info.as_dict()
    assert sorted(list(setup_dict.get("requires").keys())) == sorted(requires)


def test_no_duplicate_egg_info():
    """When the package has 'src' directory, do not write egg-info in base dir."""
    base_dir = vistir.compat.Path(os.path.abspath(os.getcwd())).as_posix()
    r = Requirement.from_line("-e {}".format(base_dir))
    egg_info_name = "{}.egg-info".format(r.name.replace("-", "_"))
    distinfo_name = "{0}.dist-info".format(r.name.replace("-", "_"))

    def find_metadata(path):
        metadata_names = [
            os.path.join(path, name) for name in (egg_info_name, distinfo_name)
        ]
        if not os.path.isdir(path):
            return None
        pth = next(iter(pth for pth in metadata_names if os.path.isdir(pth)), None)
        if not pth:
            pth = next(
                iter(
                    pth
                    for pth in os.listdir(path)
                    if any(
                        pth.endswith(md_ending)
                        for md_ending in [".egg-info", ".dist-info", ".whl"]
                    )
                ),
                None,
            )
        return pth

    assert not find_metadata(base_dir)
    assert not find_metadata(os.path.join(base_dir, "reqlib-metadata"))
    assert not find_metadata(os.path.join(base_dir, "src", "reqlib-metadata"))
    assert r.req.setup_info and os.path.isdir(r.req.setup_info.egg_base)
    setup_info = r.req.setup_info
    setup_info.get_info()
    assert (
        find_metadata(setup_info.egg_base)
        or find_metadata(setup_info.extra_kwargs["build_dir"])
        or setup_info.get_egg_metadata()
    )


@pytest.mark.needs_internet
def test_without_extras(pathlib_tmpdir):
    """Tests a setup.py or setup.cfg parse when extras returns None for some files"""
    setup_dir = pathlib_tmpdir.joinpath("sanitized-package")
    setup_dir.mkdir()
    assert setup_dir.is_dir()
    setup_py = setup_dir.joinpath("setup.py")
    setup_py.write_text(
        u"""
# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name="sanitized-package",
    version="0.0.1",
    install_requires=["raven==5.32.0"],
    extras_require={
        'PDF': ["socks"]
    }
)
    """.strip()
    )
    setup_dict = None
    with vistir.contextmanagers.cd(setup_dir.as_posix()):
        pipfile_entry = {
            "path": os.path.abspath(os.curdir),
            "editable": True,
            "extras": ["socks"],
        }
        r = Requirement.from_pipfile("e1839a8", pipfile_entry)
        r.run_requires()
        setup_dict = r.req.setup_info.as_dict()
        assert sorted(list(setup_dict.get("requires").keys())) == ["raven"]


def test_extras(pathlib_tmpdir):
    """Test named extras as a dependency"""
    setup_dir = pathlib_tmpdir.joinpath("test_package")
    setup_dir.mkdir()
    assert setup_dir.is_dir()
    setup_py = setup_dir.joinpath("setup.py")
    setup_py.write_text(
        u"""
import os
from setuptools import setup, find_packages

thisdir = os.path.abspath(os.path.dirname(__file__))
version = "1.0.0"

testing_extras = [
    'coverage',
    'flaky',
]

setup(
    name='test_package',
    version=version,
    description="The Backend HTTP Server",
    long_description="This is a package",
    install_requires=[
        'six',
    ],
    tests_require=testing_extras,
    extras_require={
        'testing': testing_extras,
    },
    package_dir={"": "src"},
    packages=['test_package'],
    include_package_data=True,
    zip_safe=False,
)
    """.strip()
    )
    src_dir = setup_dir.joinpath("src")
    src_dir.mkdir()
    pkg_dir = src_dir.joinpath("test_package")
    pkg_dir.mkdir()
    pkg_dir.joinpath("__init__.py").write_text(u"")
    pipfile_entry = {
        "path": "./{0}".format(setup_dir.name),
        "extras": ["testing"],
        "editable": True,
    }
    setup_dict = None
    with vistir.contextmanagers.cd(pathlib_tmpdir.as_posix()):
        r = Requirement.from_pipfile("test-package", pipfile_entry)
        assert r.name == "test-package"
        r.req.setup_info.get_info()
        setup_dict = r.req.setup_info.as_dict()
        assert sorted(list(setup_dict.get("requires").keys())) == [
            "coverage",
            "flaky",
            "six",
        ], setup_dict
