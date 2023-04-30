import pytest
from pip._internal.req.constructors import (
    install_req_from_editable,
    install_req_from_line,
)
from pip._vendor.packaging.specifiers import SpecifierSet

from requirementslib.models.requirements import Requirement


@pytest.mark.needs_internet
def test_get_dependencies():
    r = Requirement.from_line("requests==2.19.1")
    deps = get_dependencies(r.as_ireq())
    assert len(deps) > 0
    deps_from_ireq = get_dependencies(r.as_ireq())
    assert len(deps_from_ireq) > 0
    assert sorted(set(deps_from_ireq)) == sorted(set(deps))


@pytest.mark.needs_internet
def test_get_deps_from_json():
    r = Requirement.from_line("requests==2.19.1")
    deps = get_dependencies_from_json(r.as_ireq())
    assert len(deps) > 0


@pytest.mark.needs_internet
def test_get_deps_from_index():
    r = Requirement.from_line("requests==2.19.1")
    deps = get_dependencies_from_index(r.as_ireq())
    assert len(deps) > 0


@pytest.mark.needs_internet
def test_get_editable_from_index():
    r = install_req_from_editable(
        "git+https://github.com/requests/requests.git#egg=requests[security]"
    )
    deps = get_dependencies_from_index(r)
    assert len(deps) > 0
