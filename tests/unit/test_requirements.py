import os
import subprocess as sp
from pathlib import Path
from unittest import mock

import pytest
from hypothesis import given, settings

from requirementslib.exceptions import RequirementError
from requirementslib.models.requirements import Line, NamedRequirement, Requirement
from requirementslib.models.setup_info import SetupInfo
from requirementslib.utils import temp_environ

from .strategies import repository_line, requirements

UNIT_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.dirname(UNIT_TEST_DIR)
ARTIFACTS_DIR = os.path.join(TEST_DIR, "artifacts")
TEST_WHEEL = os.path.join(ARTIFACTS_DIR, "six", "six-1.11.0-py2.py3-none-any.whl")
TEST_WHEEL_PATH = Path(TEST_WHEEL)
TEST_WHEEL_URI = TEST_WHEEL_PATH.absolute().as_uri()
TEST_PROJECT_RELATIVE_DIR = "tests/artifacts/six/six-1.11.0-py2.py3-none-any.whl"

# Pipfile format <-> requirements.txt format.
DEP_PIP_PAIRS = [
    ({"requests": "*"}, "requests"),
    ({"requests": {"extras": ["socks"], "version": "*"}}, "requests[socks]"),
    ({"django": ">1.10"}, "django>1.10"),
    ({"Django": ">1.10"}, "Django>1.10"),
    ({"requests": {"extras": ["socks"], "version": ">1.10"}}, "requests[socks]>1.10"),
    ({"requests": {"extras": ["socks"], "version": "==1.10"}}, "requests[socks]==1.10"),
    (
        {
            "django-user-accounts": {
                "git": "git://github.com/pinax/django-user-accounts.git",
                "ref": "v2.1.0",
                "editable": True,
            }
        },
        "-e git+git://github.com/pinax/django-user-accounts.git@v2.1.0#egg=django-user-accounts",
    ),
    (
        {
            "django-user-accounts": {
                "git": "git://github.com/pinax/django-user-accounts.git",
                "ref": "v2.1.0",
            }
        },
        "git+git://github.com/pinax/django-user-accounts.git@v2.1.0#egg=django-user-accounts",
    ),
    (  # Mercurial.
        {"MyProject": {"hg": "http://hg.myproject.org/MyProject", "ref": "da39a3ee5e6b"}},
        "hg+http://hg.myproject.org/MyProject@da39a3ee5e6b#egg=MyProject",
    ),
    (  # SVN.
        {"MyProject": {"svn": "svn://svn.myproject.org/svn/MyProject", "editable": True}},
        "-e svn+svn://svn.myproject.org/svn/MyProject#egg=MyProject",
    ),
    (
        # Extras in url
        {
            "dparse": {
                "file": "https://github.com/oz123/dparse/archive/refs/heads/master.zip",
                "extras": ["pipenv"],
            }
        },
        "https://github.com/oz123/dparse/archive/refs/heads/master.zip#egg=dparse[pipenv]",
    ),
    (
        {
            "requests": {
                "git": "https://github.com/requests/requests.git",
                "ref": "master",
                "extras": ["security"],
                "editable": False,
            }
        },
        "git+https://github.com/requests/requests.git@master#egg=requests[security]",
    ),
    (
        {
            "FooProject": {
                "version": "==1.2",
                "hashes": [
                    "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
                ],
            }
        },
        "FooProject==1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    ),
    (
        {
            "FooProject": {
                "version": "==1.2",
                "extras": ["stuff"],
                "hashes": [
                    "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
                ],
            }
        },
        "FooProject[stuff]==1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    ),
    ({"six": {"file": "{0}".format(TEST_WHEEL_URI)}}, TEST_WHEEL_URI),
    (
        {"plette": {"extras": ["validation"], "version": ">=0.1.1"}},
        "plette[validation] (>=0.1.1)",
    ),
    (
        {
            "pythonfinder": {
                "ref": "master",
                "git": "https://github.com/techalchemy/pythonfinder.git",
                "subdirectory": "mysubdir",
                "extras": ["dev"],
                "editable": True,
            }
        },
        "-e git+https://github.com/techalchemy/pythonfinder.git@master#egg=pythonfinder[dev]&subdirectory=mysubdir",
    ),
]

# These are legacy Pipfile formats we need to be able to do Pipfile -> pip,
# but don't need to for pip -> Pipfile anymore.
DEP_PIP_PAIRS_LEGACY_PIPFILE = [
    (
        {
            "FooProject": {
                "version": "==1.2",
                "hash": "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
            }
        },
        "FooProject==1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    ),
    (
        {
            "FooProject": {
                "version": "==1.2",
                "extras": ["stuff"],
                "hash": "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
            }
        },
        "FooProject[stuff]==1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    ),
]


lines = [
    ("requests",),
    ("vistir[spinner]"),
    ("vistir[spinner]==0.4.1"),
    ("vistir==0.4.1"),
    (
        "https://files.pythonhosted.org/packages/2d/ac/e8a34d4b3d24bf554f40651b2aac549a3fc7223725bf10fbdfe2083b6372/shellingham-1.3.1-py2.py3-none-any.whl",  # noqa
    ),
]


@given(requirements())
def test_requirement_line(req):
    line = Line(req.line)
    assert line.get_line(with_markers=True, with_hashes=True) == req.line
    assert line.get_line(with_markers=True, with_hashes=True, as_list=True) == req.as_list
    assert line.get_line(with_markers=False, with_hashes=True) == req.line_without_markers
    assert (
        line.get_line(with_markers=False, with_hashes=True, as_list=True)
        == req.list_without_markers
    )


@settings(deadline=None)
@given(repository_line())
def test_repo_line(repo_line):
    reformatted_line = repo_line
    if repo_line.startswith("-e "):
        repo_list = repo_line.split(" ", 1)
        if "; " in repo_list[1]:
            reformatted_line = "{0} {1}".format(repo_list[0], repo_list[1])
    else:
        repo_list = [repo_line]
    assert (
        Line(repo_line).get_line(with_prefix=True, with_markers=True, as_list=False)
        == reformatted_line
    )
    assert (
        Line(repo_line).get_line(with_prefix=True, with_markers=True, as_list=True)
        == repo_list
    )


def mock_run_requires(cls):
    return {}


def mock_setup_requires(cls):
    return mock.MagicMock(version="1.2")


@pytest.mark.utils
@pytest.mark.parametrize("expected, requirement", DEP_PIP_PAIRS)
@mock.patch(
    "requirementslib.models.setup_info.unpack_url", mock.MagicMock(return_value={})
)
def test_convert_from_pip(monkeypatch, expected, requirement):
    with monkeypatch.context() as m:
        m.setattr(Requirement, "run_requires", mock_run_requires)
        m.setattr(SetupInfo, "get_info", mock_setup_requires)
        m.setattr(Line, "get_setup_info", mock_setup_requires)
        pkg_name = next(iter(expected.keys()))
        pkg_pipfile = expected[pkg_name]
        line = Line(requirement)
        if (
            hasattr(pkg_pipfile, "keys")
            and "editable" in pkg_pipfile
            and not pkg_pipfile["editable"]
        ):
            del expected[pkg_name]["editable"]
        req = Requirement.from_line(requirement)
        assert req.as_pipfile() == expected
        assert line.line_with_prefix == req.as_line(include_hashes=False)
        assert hash(Line(line.line_with_prefix)) == hash(Line(line.line_with_prefix))


@pytest.mark.to_line
@pytest.mark.parametrize(
    "requirement, expected", DEP_PIP_PAIRS + DEP_PIP_PAIRS_LEGACY_PIPFILE
)
@mock.patch(
    "requirementslib.models.setup_info.unpack_url", mock.MagicMock(return_value={})
)
def test_convert_from_pipfile(monkeypatch, requirement, expected):
    with monkeypatch.context() as m:
        m.setattr(SetupInfo, "get_info", mock_run_requires)
        m.setattr(Requirement, "run_requires", mock_run_requires)
        pkg_name = next(iter(requirement.keys()))
        pkg_pipfile = requirement[pkg_name]
        req = Requirement.from_pipfile(pkg_name, pkg_pipfile)
        if " (" in expected and expected.endswith(")"):
            # To strip out plette[validation] (>=0.1.1)
            expected = expected.replace(" (", "").rstrip(")")
        assert req.as_line() == (expected.lower() if "://" not in expected else expected)


@pytest.mark.requirements
@mock.patch(
    "requirementslib.models.setup_info.unpack_url", mock.MagicMock(return_value={})
)
def test_convert_from_pipfile_vcs(monkeypatch):
    """ssh VCS links should be converted correctly."""
    with monkeypatch.context() as m:
        pkg_name = "shellingham"
        pkg_pipfile = {"editable": True, "git": "git@github.com:sarugaku/shellingham.git"}
        req = Requirement.from_pipfile(pkg_name, pkg_pipfile)
        assert (
            req.req.link.url
            == "git+ssh://git@github.com/sarugaku/shellingham.git#egg=shellingham"
        )


@pytest.mark.utils
def test_convert_from_pip_fail_if_no_egg():
    """Parsing should fail without `#egg=`."""
    dep = "git+https://github.com/psf/requests.git"
    with pytest.raises(ValueError) as e:
        dep = Requirement.from_line(dep).as_pipfile()
        assert "pipenv requires an #egg fragment for vcs" in str(e)


@pytest.mark.requirements
def test_convert_non_installable_dir_fail(pathlib_tmpdir):
    """Convert a non-installable directory link should fail without deleting
    the directory."""
    dep = "-e file://{}".format(pathlib_tmpdir.as_posix())
    with pytest.raises(RequirementError):
        req = Requirement.from_line(dep)
    assert pathlib_tmpdir.exists()


@pytest.mark.editable
def test_one_way_editable_extras():
    dep = "-e .[socks]"
    with pytest.raises(RequirementError):
        Requirement.from_line(dep)


@pytest.mark.utils
@mock.patch(
    "requirementslib.models.setup_info.unpack_url", mock.MagicMock(return_value={})
)
def test_convert_from_pip_git_uri_normalize(monkeypatch):
    """Pip does not parse this correctly, but we can (by converting to
    ssh://)."""
    with monkeypatch.context() as m:
        m.setattr(Requirement, "run_requires", mock_run_requires)
        m.setattr(SetupInfo, "get_info", mock_run_requires)
        dep = "git+git@host:user/repo.git#egg=myname"
        dep = Requirement.from_line(dep).as_pipfile()
        assert dep == {"myname": {"git": "git@host:user/repo.git"}}


@pytest.mark.utils
@pytest.mark.requirements
@mock.patch(
    "requirementslib.models.setup_info.unpack_url", mock.MagicMock(return_value={})
)
def test_get_requirements(monkeypatch_if_needed):
    # Test eggs in URLs
    # m.setattr(SetupInfo, "get_info", mock_run_requires)
    # url_with_egg = Requirement.from_line(
    #     "https://github.com/IndustriaTech/django-user-clipboard/archive/0.6.1.zip#egg=django-user-clipboard"
    # ).requirement
    # assert (
    #     url_with_egg.url
    #     == "https://github.com/IndustriaTech/django-user-clipboard/archive/0.6.1.zip"
    # )
    # assert url_with_egg.name == "django-user-clipboard"
    # Test URLs without eggs pointing at installable zipfiles
    url = Requirement.from_line(
        "https://github.com/jazzband/tablib/archive/v0.12.1.zip"
    ).requirement
    assert url.url == "https://github.com/jazzband/tablib/archive/v0.12.1.zip"
    wheel_line = "https://github.com/pypa/pipenv/raw/master/tests/test_artifacts/six-1.11.0+mkl-py2.py3-none-any.whl"
    wheel = Requirement.from_line(wheel_line)
    assert wheel.as_pipfile() == {
        "six": {
            "file": "https://github.com/pypa/pipenv/raw/master/tests/test_artifacts/six-1.11.0+mkl-py2.py3-none-any.whl"
        }
    }
    # Requirementslib inserts egg fragments as names when possible if we know the appropriate name
    # this allows for custom naming
    assert (
        Requirement.from_pipfile(wheel.name, list(wheel.as_pipfile().values())[0])
        .as_line()
        .split("#")[0]
        == wheel_line
    )
    # Test VCS urls with refs and eggnames
    vcs_url = Requirement.from_line(
        "git+https://github.com/jazzband/tablib.git@master#egg=tablib"
    ).requirement
    assert (
        vcs_url.vcs == "git" and vcs_url.name == "tablib" and vcs_url.revision == "master"
    )
    assert vcs_url.url == "git+https://github.com/jazzband/tablib.git"
    # Test normal package requirement
    normal = Requirement.from_line("tablib").requirement
    assert normal.name == "tablib"
    # Pinned package  requirement
    spec = Requirement.from_line("tablib==0.12.1").requirement
    assert spec.name == "tablib" and spec.specs == [("==", "0.12.1")]
    # Test complex package with both extras and markers
    extras_markers = Requirement.from_line(
        "requests[security] ; os_name=='posix'"
    ).requirement
    assert list(extras_markers.extras) == ["security"]
    assert extras_markers.name == "requests"
    assert str(extras_markers.marker) == 'os_name == "posix"'
    # Test VCS uris get generated correctly, retain git+git@ if supplied that way, and are named according to egg fragment
    git_reformat = Requirement.from_line(
        "-e git+git@github.com:pypa/pipenv.git#egg=pipenv"
    ).requirement
    assert git_reformat.url == "git+ssh://git@github.com/pypa/pipenv.git"
    assert git_reformat.name == "pipenv"
    assert git_reformat.editable
    # Previously VCS uris were being treated as local files, so make sure these are not handled that way
    assert not git_reformat.local_file
    # Test regression where VCS uris were being handled as paths rather than VCS entries
    assert git_reformat.vcs == "git"
    assert git_reformat.link.url == "git+ssh://git@github.com/pypa/pipenv.git#egg=pipenv"
    # Test VCS requirements being added with extras for constraint_line
    git_extras = Requirement.from_line(
        "-e git+https://github.com/requests/requests.git@master#egg=requests[security]"
    )
    assert (
        git_extras.as_line()
        == "-e git+https://github.com/requests/requests.git@master#egg=requests[security]"
    )
    assert (
        git_extras.constraint_line
        == "-e git+https://github.com/requests/requests.git@master#egg=requests[security]"
    )
    # these will fail due to not being real paths
    # local_wheel = Requirement.from_pipfile('six', {'path': '../wheels/six/six-1.11.0-py2.py3-none-any.whl'})
    # assert local_wheel.as_line() == 'file:///home/hawk/git/wheels/six/six-1.11.0-py2.py3-none-any.whl'
    # local_wheel_from_line = Requirement.from_line('../wheels/six/six-1.11.0-py2.py3-none-any.whl')
    # assert local_wheel_from_line.as_pipfile() == {'six': {'path': '../wheels/six/six-1.11.0-py2.py3-none-any.whl'}}


@pytest.mark.utils
@pytest.mark.requirements
def test_get_requirements_when_subdirectory_fragment(monkeypatch_if_needed):
    url_with_egg = Requirement.from_line(
        "https://github.com/matteius/test-project.git#egg=test_project&subdirectory=parent_folder/pep508-package",
        parse_setup_info=False,
    ).requirement
    assert url_with_egg.url == "https://github.com/matteius/test-project.git"


@pytest.mark.needs_internet
def test_get_ref(artifact_dir):
    req_uri = (
        artifact_dir.joinpath("git/shellingham").as_uri().replace("file:/", "file:///")
    )
    git_uri = "-e git+{0}@1.2.1#egg=shellingham".format(req_uri)
    r = Requirement.from_line(git_uri)
    #     "-e git+https://github.com/sarugaku/shellingham.git@1.2.1#egg=shellingham"
    # )
    assert r.commit_hash == "9abe7464dab5cc362fe08361619d3fb15f2e16ab"


def test_get_local_ref(tmpdir):
    # TODO: add this as a git submodule and don't clone it from the internet all the time
    six_dir = tmpdir.join("six")

    c = sp.run(
        ["git", "clone", "https://github.com/benjaminp/six.git", six_dir.strpath],
    )
    assert c.returncode == 0
    r = Requirement.from_line("git+{0}#egg=six".format(Path(six_dir.strpath).as_uri()))
    assert r.commit_hash


@pytest.mark.needs_internet
def test_stdout_is_suppressed(capsys, tmpdir):
    r = Requirement.from_line("git+https://github.com/benjaminp/six.git@master#egg=six")
    r.req.get_vcs_repo(src_dir=tmpdir.strpath)
    out, err = capsys.readouterr()
    assert out.strip() == "", out
    assert err.strip() == "", err


@mock.patch(
    "requirementslib.models.setup_info.unpack_url", mock.MagicMock(return_value={})
)
def test_local_editable_ref(monkeypatch):
    with monkeypatch.context() as m:
        path = Path(ARTIFACTS_DIR) / "git/requests"
        req = Requirement.from_pipfile(
            "requests", {"editable": True, "git": path.as_uri(), "ref": "2.18.4"}
        )
        assert req.as_line() == "-e git+{0}@2.18.4#egg=requests".format(path.as_uri())


@pytest.mark.needs_internet
def test_pep_508():
    r = Requirement.from_line(
        "tablib@ https://codeload.github.com/jazzband/tablib/zip/v0.12.1",
    )
    assert r.specifiers == "==0.12.1"
    assert (
        r.req.link.url
        == "https://codeload.github.com/jazzband/tablib/zip/v0.12.1#egg=tablib"
    )
    assert r.req.req.name == "tablib"
    assert r.req.req.url == "https://codeload.github.com/jazzband/tablib/zip/v0.12.1"
    requires, setup_requires, build_requires = r.req.dependencies
    assert all(dep in requires for dep in ["openpyxl", "odfpy", "xlrd"])
    assert r.as_pipfile() == {
        "tablib": {"file": "https://codeload.github.com/jazzband/tablib/zip/v0.12.1"}
    }


@pytest.mark.requirements
@pytest.mark.needs_internet
def test_named_requirement_selected_over_non_installable_path(
    monkeypatch, pathlib_tmpdir
):
    with monkeypatch.context() as m:
        m.chdir(pathlib_tmpdir.as_posix())
        pathlib_tmpdir.joinpath("alembic").write_text("")
        r = Requirement.from_line("alembic")
        assert isinstance(r.req, NamedRequirement)
        assert r.as_line() == "alembic"
        assert r.line_instance.is_named is True


@pytest.mark.requirements
def test_file_url_with_percent_encoding():
    r = Requirement.from_pipfile(
        "torch",
        {
            "file": "https://download.pytorch.org/whl/cpu/torch-1.7.0%2Bcpu-cp38-cp38-linux_x86_64.whl#egg=torch"
        },
    )
    assert (
        r.req.uri
        == "https://download.pytorch.org/whl/cpu/torch-1.7.0%2Bcpu-cp38-cp38-linux_x86_64.whl"
    )
    assert (
        r.as_line()
        == "https://download.pytorch.org/whl/cpu/torch-1.7.0%2Bcpu-cp38-cp38-linux_x86_64.whl#egg=torch"
    )


@pytest.mark.needs_internet
def test_vcs_requirement_with_env_vars():
    with temp_environ():
        os.environ["GIT_URL"] = "github.com"
        r = Requirement.from_pipfile(
            "click", {"git": "https://${GIT_URL}/pallets/click.git", "ref": "6.7"}
        )
        assert (
            r.as_ireq().link.url_without_fragment
            == "git+https://github.com/pallets/click.git@6.7"
        )
        assert r.as_line() == "git+https://${GIT_URL}/pallets/click.git@6.7#egg=click"
        assert r.as_pipfile()["click"]["git"] == "https://${GIT_URL}/pallets/click.git"
        assert r.commit_hash == "df0e37dd890d36fc997986ae6d2b6c255f3ed1dc"


@mock.patch(
    "requirementslib.models.setup_info.unpack_url", mock.MagicMock(return_value={})
)
def test_remote_requirement_with_env_vars():
    with temp_environ():
        os.environ["USERNAME"] = "foo"
        os.environ["PASSWORD"] = "bar"
        r = Requirement.from_line(
            "https://${USERNAME}:${PASSWORD}@codeload.github.com/jazzband/tablib/zip/v0.12.1#egg=tablib"
        )
        assert (
            r.as_ireq().link.url_without_fragment
            == "https://foo:bar@codeload.github.com/jazzband/tablib/zip/v0.12.1"
        )
        assert (
            r.as_line()
            == "https://${USERNAME}:${PASSWORD}@codeload.github.com/jazzband/tablib/zip/v0.12.1#egg=tablib"
        )
        assert (
            r.as_pipfile()["tablib"]["file"]
            == "https://${USERNAME}:${PASSWORD}@codeload.github.com/jazzband/tablib/zip/v0.12.1"
        )
