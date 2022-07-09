# -*- coding=utf-8 -*-
import os
import shutil

import pytest
import vistir

from requirementslib.models.requirements import Requirement
from requirementslib.models.setup_info import ast_parse_setup_py


@pytest.mark.skipif(os.name == "nt", reason="Building this is broken on windows")
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
    assert r.name.replace("_", "-") == "environ-config"
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


@pytest.mark.parametrize(
    "url_line, name",
    [
        [
            "https://github.com/matteius/test-project/archive/refs/tags/1.0.0.zip#egg=test_project&subdirectory=parent_folder/pep508-package",
            "test_project",
        ],
    ],
)
@pytest.mark.needs_internet
def test_remote_source_in_subdirectory(url_line, name):
    r = Requirement.from_line(url_line)
    assert r.name == name
    setup_dict = r.req.setup_info.as_dict()
    print(setup_dict)
    assert setup_dict.get("name") == "pep508_package"
    assert setup_dict.get("version") == "1.0.0"
    assert sorted(list(setup_dict.get("requires").keys())) == sorted(
        ["sibling-package", "six"]
    )


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
    expected = {
        "name": "test_package",
        "version": "1.0.0",
        "install_requires": ["six"],
        "extras_require": {"testing": ["coverage", "flaky"]},
    }
    for k, v in expected.items():
        assert k in parsed
        if isinstance(v, bool):
            assert str(parsed[k]) == str(v), parsed[k]
        else:
            assert parsed[k] == v, parsed[k]


def test_ast_parser_finds_fully_qualified_setup(setup_py_dir):
    target = setup_py_dir.joinpath(
        "package_using_fully_qualified_setuptools/setup.py"
    ).as_posix()
    parsed = ast_parse_setup_py(target)
    expected = {
        "name": "test_package",
        "version": "1.0.0",
        "install_requires": ["six"],
        "extras_require": {"testing": ["coverage", "flaky"]},
    }
    for k, v in expected.items():
        assert k in parsed
        if isinstance(v, bool):
            assert str(parsed[k]) == str(v), parsed[k]
        else:
            assert parsed[k] == v, parsed[k]


def test_ast_parser_handles_binops(setup_py_dir):
    target = setup_py_dir.joinpath(
        "package_with_conditional_install_requires/setup.py"
    ).as_posix()
    parsed = ast_parse_setup_py(target)
    expected = [
        "azure-common>=1.1.5",
        "cryptography",
        "python-dateutil",
        "requests",
    ]
    assert list(sorted(parsed["install_requires"])) == list(sorted(expected))


def test_ast_parser_handles_binops_alternate(setup_py_dir):
    target = setup_py_dir.joinpath("package_with_setup_from_dict/setup.py").as_posix()
    parsed = ast_parse_setup_py(target)
    assert parsed["name"] == "test package"
    assert parsed["version"] == "1.0.0"
    expected = [
        "pytest",
        "flake8",
    ]
    assert list(sorted(parsed["extras_require"]["tests"])) == list(sorted(expected))


def test_parse_function_call_as_name(setup_py_dir, pathlib_tmpdir):
    package_dir = pathlib_tmpdir.joinpath("package_with_function_call_as_name").as_posix()
    setup_dir = setup_py_dir.joinpath("package_with_function_call_as_name").as_posix()
    shutil.copytree(setup_dir, package_dir)
    req = Requirement.from_line("-e {}".format(package_dir))
    assert req.name == "package-with-function-call-as-name"


def test_ast_parser_handles_repeated_assignments(setup_py_dir):
    target = (
        setup_py_dir.joinpath("package_with_repeated_assignments").absolute().as_posix()
    )
    r = Requirement.from_line(target)
    setup_dict = r.req.setup_info.as_dict()
    assert setup_dict["name"] == "test-package-with-repeated-assignments"
    assert sorted(setup_dict["requires"]) == ["six"]


def test_ast_parser_handles_exceptions(artifact_dir):
    path = artifact_dir.joinpath("git/pyinstaller")
    r = Requirement.from_line(path.as_posix())
    setup_dict = r.req.setup_info.as_dict()
    assert "altgraph" in setup_dict["requires"]


def test_ast_parser_handles_annoted_assignments(setup_py_dir):
    parsed = ast_parse_setup_py(
        setup_py_dir.joinpath("package_with_annoted_assignments/setup.py").as_posix()
    )
    assert parsed["extras_require"] == {"docs": ["sphinx", "sphinx-argparse"]}


def test_read_requirements_with_list_comp(setup_py_dir):
    req = Requirement.from_line(
        f"-e {(setup_py_dir / 'package_with_setup_with_list_comp').as_posix()}"
    )
    setup_info = req.req.setup_info.as_dict()
    assert sorted(setup_info["requires"]) == ["requests"]


def test_read_requirements_with_string_interpolation(setup_py_dir):
    req = Requirement.from_line(
        f"-e {(setup_py_dir / 'package_with_setup_with_string_interpolation').as_posix()}"
    )
    setup_info = req.req.setup_info.as_dict()
    assert sorted(setup_info["requires"]) == ["requests", "six"]


def test_ast_parse_from_dict_with_name(setup_py_dir):
    parsed = ast_parse_setup_py(
        (setup_py_dir / "package_with_setup_from_dict_with_name/setup.py").as_posix()
    )
    assert parsed["install_requires"] == ["requests"]
