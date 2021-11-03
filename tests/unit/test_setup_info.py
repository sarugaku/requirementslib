# -*- coding=utf-8 -*-
import ast
import contextlib
import os
import shutil
import sys

import pytest
import vistir

from requirementslib.models.requirements import Requirement
from requirementslib.models.setup_info import (
    ast_parse_file,
    ast_parse_setup_py,
    parse_setup_cfg,
)


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
    """When the package has 'src' directory, do not write egg-info in base
    dir."""
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
    """Tests a setup.py or setup.cfg parse when extras returns None for some
    files."""
    setup_dir = pathlib_tmpdir.joinpath("sanitized-package")
    setup_dir.mkdir()
    assert setup_dir.is_dir()
    setup_py = setup_dir.joinpath("setup.py")
    setup_py.write_text(
        """
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


@pytest.mark.parametrize(
    "setup_py_name, extras, dependencies",
    [
        (
            "package_with_multiple_extras",
            ["testing", "dev"],
            ["coverage", "flaky", "invoke", "parver", "six", "vistir", "wheel"],
        ),
        ("package_with_one_extra", ["testing"], ["coverage", "flaky", "six"]),
    ],
)
def test_extras(pathlib_tmpdir, setup_py_dir, setup_py_name, extras, dependencies):
    """Test named extras as a dependency."""
    setup_dir = pathlib_tmpdir.joinpath("test_package")
    shutil.copytree(setup_py_dir.joinpath(setup_py_name).as_posix(), setup_dir.as_posix())
    assert setup_dir.is_dir()
    pipfile_entry = {
        "path": "./{0}".format(setup_dir.name),
        "extras": extras,
        "editable": True,
    }
    setup_dict = None
    with vistir.contextmanagers.cd(pathlib_tmpdir.as_posix()):
        r = Requirement.from_pipfile("test-package", pipfile_entry)
        assert r.name == "test-package"
        r.req.setup_info.get_info()
        setup_dict = r.req.setup_info.as_dict()
        assert sorted(list(setup_dict.get("requires").keys())) == dependencies


def test_ast_parser_finds_variables(setup_py_dir):
    target = setup_py_dir.joinpath("package_with_extras_as_variable/setup.py").as_posix()
    parsed = ast_parse_setup_py(target)
    analyzer = ast_parse_file(target)
    expected = {
        "name": "test_package",
        "version": "1.0.0",
        "description": "The Backend HTTP Server",
        "long_description": "This is a package",
        "install_requires": ["six"],
        "tests_require": ["coverage", "flaky"],
        "extras_require": {"testing": ["coverage", "flaky"]},
        "package_dir": {"": "src"},
        "packages": ["test_package"],
        "include_package_data": True,
        "zip_safe": False,
    }
    for k, v in expected.items():
        assert k in parsed
        if isinstance(v, bool):
            assert str(parsed[k]) == str(v), parsed[k]
        else:
            assert parsed[k] == v, parsed[k]
    assert analyzer.parse_setup_function() == parsed


def test_ast_parser_finds_fully_qualified_setup(setup_py_dir):
    target = setup_py_dir.joinpath(
        "package_using_fully_qualified_setuptools/setup.py"
    ).as_posix()
    parsed = ast_parse_setup_py(target)
    analyzer = ast_parse_file(target)
    expected = {
        "name": "test_package",
        "version": "1.0.0",
        "description": "The Backend HTTP Server",
        "long_description": "This is a package",
        "install_requires": ["six"],
        "tests_require": ["coverage", "flaky"],
        "extras_require": {"testing": ["coverage", "flaky"]},
        "package_dir": {"": "src"},
        "packages": ["test_package"],
        "include_package_data": True,
        "zip_safe": False,
    }
    for k, v in expected.items():
        assert k in parsed
        if isinstance(v, bool):
            assert str(parsed[k]) == str(v), parsed[k]
        else:
            assert parsed[k] == v, parsed[k]
    assert analyzer.parse_setup_function() == parsed


def test_ast_parser_handles_binops(setup_py_dir):
    target = setup_py_dir.joinpath(
        "package_with_conditional_install_requires/setup.py"
    ).as_posix()
    parsed = ast_parse_setup_py(target)
    analyzer = ast_parse_file(target)
    expected = [
        "azure-common>=1.1.5",
        "cryptography",
        "python-dateutil",
        "requests",
    ]
    assert list(sorted(parsed["install_requires"])) == list(sorted(expected))
    assert analyzer.parse_setup_function() == parsed


def test_ast_parser_handles_binops(setup_py_dir):
    target = setup_py_dir.joinpath("package_with_setup_from_dict/setup.py").as_posix()
    parsed = ast_parse_setup_py(target)
    analyzer = ast_parse_file(target)
    assert parsed["name"] == "test package"
    assert parsed["version"] == "1.0.0"
    expected = [
        "pytest",
        "flake8",
    ]
    assert list(sorted(parsed["extras_require"]["tests"])) == list(sorted(expected))
    assert analyzer.parse_setup_function() == parsed


def test_parse_function_call_as_name(setup_py_dir, pathlib_tmpdir):
    package_dir = pathlib_tmpdir.joinpath("package_with_function_call_as_name").as_posix()
    setup_dir = setup_py_dir.joinpath("package_with_function_call_as_name").as_posix()
    shutil.copytree(setup_dir, package_dir)
    req = Requirement.from_line("-e {}".format(package_dir))
    assert req.name == "package-with-function-call-as-name"


def test_ast_parser_handles_repeated_assignments(setup_py_dir):
    target = setup_py_dir.joinpath(
        "package_with_repeated_assignments/setup.py"
    ).as_posix()
    parsed = ast_parse_setup_py(target)
    analyzer = ast_parse_file(target)
    assert parsed["name"] == "test_package_with_repeated_assignments"
    assert isinstance(parsed["version"], str) is False
    assert parsed["install_requires"] == ["six"]
    analyzer_parsed = analyzer.parse_setup_function()
    # the versions in this instance are AST objects as they come from
    # os.environ and will need to be parsed downstream from here, so
    # equality comparisons will fail
    analyzer_parsed.pop("version")
    parsed.pop("version")
    assert analyzer_parsed == parsed


def test_setup_cfg_parser(setup_cfg_dir):
    setup_path = setup_cfg_dir / "package_with_multiple_extras/setup.cfg"
    contents = setup_path.read_text()
    result = parse_setup_cfg(contents, setup_path.parent.as_posix())
    assert result["version"] == "0.5.0"
    assert result["name"] == "test_package"


def test_parse_setup_cfg_with_special_directives(setup_cfg_dir):
    setup_path = setup_cfg_dir / "package_with_special_directives/setup.cfg"
    contents = setup_path.read_text()
    result = parse_setup_cfg(contents, setup_path.parent.as_posix())
    assert result["version"] == "0.1.0"
    assert result["name"] == "bug-test"


@pytest.mark.parametrize(
    "env_vars, expected_install_requires",
    [
        ({"NOTHING": "1"}, []),
        ({"READTHEDOCS": "1"}, ["sphinx", "sphinx-argparse"]),
    ],
)
def test_ast_parser_handles_dependency_on_env_vars(
    env_vars, expected_install_requires, setup_py_dir
):
    @contextlib.contextmanager
    def modified_environ(**update):
        env = os.environ
        try:
            env.update(update)
            yield
        finally:
            [env.pop(k) for k in update]

    with modified_environ(**env_vars):
        parsed = ast_parse_setup_py(
            setup_py_dir.joinpath(
                "package_with_dependence_on_env_vars/setup.py"
            ).as_posix()
        )
        assert list(sorted(parsed["install_requires"])) == list(
            sorted(expected_install_requires)
        )


def test_ast_parser_handles_exceptions(artifact_dir):
    path = artifact_dir.joinpath("git/pyinstaller/setup.py")
    result = ast_parse_setup_py(path.as_posix())
    analyzer = ast_parse_file(path.as_posix())
    assert result is not None
    assert "altgraph" in result["install_requires"]
    for k, v in analyzer.parse_setup_function().items():
        assert k in result
        assert result[k] == v or (
            isinstance(v, dict) and isinstance(list(v.keys())[0], ast.Attribute)
        )


@pytest.mark.skipif(
    sys.version_info < (3, 6), reason="Type annotations are not available for Python<3.6"
)
def test_ast_parser_handles_annoted_assignments(setup_py_dir):
    parsed = ast_parse_setup_py(
        setup_py_dir.joinpath("package_with_annoted_assignments/setup.py").as_posix()
    )
    assert parsed["extras_require"] == {"docs": ["sphinx", "sphinx-argparse"]}
