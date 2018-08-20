# -*- coding=utf-8 -*-
from requirementslib.models import utils


def test_filter_none():
    assert utils.filter_none("abc", "") == False
    assert utils.filter_none("abc", None) == False
    assert utils.filter_none("abc", []) == False
    assert utils.filter_none("abc", "asdf") == True


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


def test_build_vcs_link():
    link = utils.build_vcs_link("git", "https://github.com/sarugaku/plette.git", name="passa", ref="master", subdirectory="subdir", extras="validation")
    assert link.url == "git+https://github.com/sarugaku/plette.git@master#egg=passa[validation]&subdirectory=subdir"


def test_strip_ssh_from_git_url():
    url = "git+ssh://git@github.com/sarugaku/passa.git"
    url_no_ssh = "git+git@github.com/sarugaku/passa.git"
    assert utils.strip_ssh_from_git_uri(url) == url_no_ssh
    assert utils.add_ssh_scheme_to_git_uri(url_no_ssh) == url


def test_split_markers_from_line():
    line = "test_requirement; marker=='something'"
    assert utils.split_markers_from_line(line) == ("test_requirement", "marker=='something'")
    line = "test_requirement"
    assert utils.split_markers_from_line(line) == ("test_requirement", None)


def test_split_vcs_method_from_uri():
    url = "git+https://github.com/sarugaku/plette.git"
    assert utils.split_vcs_method_from_uri(url) == ("git", "https://github.com/sarugaku/plette.git")
    url = "https://github.com/sarugaku/plette.git"
    assert utils.split_vcs_method_from_uri(url) == (None, "https://github.com/sarugaku/plette.git")
