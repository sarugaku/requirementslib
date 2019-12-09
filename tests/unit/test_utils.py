# -*- coding=utf-8 -*-
import pip_shims.shims
import pytest
from vistir.compat import Path

from requirementslib import utils as base_utils
from requirementslib.models import utils
from requirementslib.models.requirements import Requirement
from requirementslib.models.setup_info import SetupInfo


def mock_run_requires(cls):
    return {}


def mock_unpack(
    link,
    source_dir,
    download_dir,
    only_download=False,
    session=None,
    hashes=None,
    progress_bar="off",
):
    return


def test_filter_none():
    assert utils.filter_none("abc", "") is False
    assert utils.filter_none("abc", None) is False
    assert utils.filter_none("abc", []) is False
    assert utils.filter_none("abc", "asdf") is True


def test_init_requirement():
    req = utils.init_requirement("requests[security]")
    assert req.name == "requests"
    assert req.extras == ("security",)
    req = utils.init_requirement("requests[security,insecurity]")
    assert sorted(req.extras) == ["insecurity", "security"]
    req = utils.init_requirement("requests[security,insecurity]>=2.19.1")
    assert req.specifier
    assert req.revision is None
    assert req.vcs is None
    assert req.path is None


def test_extras_to_string():
    assert utils.extras_to_string("[security,insecurity]") == "[security,insecurity]"
    assert utils.extras_to_string(["security", "insecurity"]) == "[insecurity,security]"
    assert utils.extras_to_string(["security"]) == "[security]"


def test_build_vcs_uri():
    uri = utils.build_vcs_uri(
        "git",
        "https://github.com/sarugaku/plette.git",
        name="passa",
        ref="master",
        subdirectory="subdir",
        extras="validation",
    )
    assert (
        uri
        == "git+https://github.com/sarugaku/plette.git@master#egg=passa[validation]&subdirectory=subdir"
    )


def test_strip_ssh_from_git_url():
    url = "git+ssh://git@github.com/sarugaku/passa.git"
    url_no_ssh = "git+git@github.com:sarugaku/passa.git"
    assert base_utils.strip_ssh_from_git_uri(url) == url_no_ssh
    assert base_utils.add_ssh_scheme_to_git_uri(url_no_ssh) == url


def test_split_markers_from_line():
    line = "test_requirement; marker=='something'"
    assert utils.split_markers_from_line(line) == (
        "test_requirement",
        "marker=='something'",
    )
    line = "test_requirement"
    assert utils.split_markers_from_line(line) == ("test_requirement", None)


def test_split_vcs_method_from_uri():
    url = "git+https://github.com/sarugaku/plette.git"
    assert utils.split_vcs_method_from_uri(url) == (
        "git",
        "https://github.com/sarugaku/plette.git",
    )
    url = "https://github.com/sarugaku/plette.git"
    assert utils.split_vcs_method_from_uri(url) == (
        None,
        "https://github.com/sarugaku/plette.git",
    )


# tests from pip-tools


def test_format_requirement():
    ireq = Requirement.from_line("test==1.2").as_ireq()
    assert utils.format_requirement(ireq) == "test==1.2"


def test_format_requirement_editable(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(SetupInfo, "get_info", mock_run_requires)
        m.setattr(Requirement, "run_requires", mock_run_requires)
        m.setattr(pip_shims.shims, "unpack_url", mock_unpack)
        ireq = Requirement.from_line("-e git+git://fake.org/x/y.git#egg=y").as_ireq()
        assert utils.format_requirement(ireq) == "-e git+git://fake.org/x/y.git#egg=y"


def test_format_specifier():
    ireq = Requirement.from_line("foo").as_ireq()
    assert utils.format_specifier(ireq) == "<any>"

    ireq = Requirement.from_line("foo==1.2").as_ireq()
    assert utils.format_specifier(ireq) == "==1.2"

    ireq = Requirement.from_line("foo>1.2,~=1.1,<1.5").as_ireq()
    assert utils.format_specifier(ireq) == "~=1.1,>1.2,<1.5"
    ireq = Requirement.from_line("foo~=1.1,<1.5,>1.2").as_ireq()
    assert utils.format_specifier(ireq) == "~=1.1,>1.2,<1.5"


def test_as_tuple():
    ireq = Requirement.from_line("foo==1.1").as_ireq()
    name, version, extras = utils.as_tuple(ireq)
    assert name == "foo"
    assert version == "1.1"
    assert extras == ()

    ireq = Requirement.from_line("foo[extra1,extra2]==1.1").as_ireq()
    name, version, extras = utils.as_tuple(ireq)
    assert name == "foo"
    assert version == "1.1"
    assert extras == ("extra1", "extra2")

    # Non-pinned versions aren't accepted
    should_be_rejected = [
        "foo==1.*",
        "foo~=1.1,<1.5,>1.2",
        "foo",
    ]
    for spec in should_be_rejected:
        ireq = Requirement.from_line(spec).as_ireq()
        with pytest.raises(TypeError):
            utils.as_tuple(ireq)


def test_flat_map():
    assert [1, 2, 4, 1, 3, 9] == list(utils.flat_map(lambda x: [1, x, x * x], [2, 3]))


@pytest.mark.parametrize(
    "entry, expected",
    [
        (
            {"file": Path("fakefile").absolute().as_uri()},
            Path("fakefile").absolute().as_posix(),
        ),
        (
            {"path": Path("fakefile").absolute().as_posix()},
            Path("fakefile").absolute().as_posix(),
        ),
        ({"path": "."}, "."),
        ({"path": "../otherfakefile"}, "../otherfakefile"),
    ],
)
def test_convert_to_path(entry, expected):
    assert base_utils.convert_entry_to_path(entry) == expected


def test_convert_to_path_failures():
    with pytest.raises(TypeError):
        base_utils.convert_entry_to_path("some_string")
    with pytest.raises(ValueError):
        base_utils.convert_entry_to_path(
            {"git": "https://github.com/sarugaku/vistir.git", "editable": True}
        )


@pytest.mark.parametrize(
    "input, expected",
    [
        ({"file": Path("fakefile").absolute().as_uri()}, False),
        ({"path": Path("fakefile").absolute()}, False),
        ({"path": ".", "editable": True}, True),
        ({"path": "../otherfakefile"}, False),
        ({"git": "https://github.com/sarugaku/vistir.git", "editable": True}, True),
        ({"git": "https://github.com/sarugaku/shellingham.git"}, False),
        ("-e .", True),
        (".", False),
        ("-e git+https://github.com/pypa/pip.git", True),
        ("git+https://github.com/pypa/pip.git", False),
    ],
)
def test_editable_check(input, expected):
    assert base_utils.is_editable(input) is expected
