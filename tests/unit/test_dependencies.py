# -*- coding=utf-8 -*-
import requirementslib
from requirementslib.models.requirements import Requirement
from requirementslib.models.dependencies import (
    get_abstract_dependencies,
    get_dependencies_from_json,
    get_dependencies_from_index
)

from pip_shims import InstallRequirement


def test_find_all_matches():
    r = Requirement.from_line("six")
    matches = r.find_all_matches()
    assert len(matches) > 0


def test_get_dependencies():
    r = Requirement.from_line("requests==2.19.1")
    deps = r.get_dependencies()
    assert len(deps) > 0
    deps_from_ireq = requirementslib.models.dependencies.get_dependencies(r.as_ireq())
    assert len(deps_from_ireq) > 0
    assert sorted(set(deps_from_ireq)) == sorted(set(deps))


def get_abstract_deps():
    r = Requirement.from_line("requests")
    deps = [InstallRequirement.from_line(d) for d in r.get_dependencies()]
    abstract_deps = r.get_abstract_dependencies()
    req_abstract_dep = requirementslib.models.dependencies.AbstractDependency.from_requirement(r)
    assert r.abstract_dep == req_abstract_dep
    assert len(abstract_deps) > 0
    deps_from_ireqs = get_abstract_dependencies(deps, parent=r)
    assert len(deps_from_ireqs) > 0
    assert sorted(set(deps_from_ireqs)) == sorted(set(abstract_deps))


def test_get_deps_from_json():
    r = Requirement.from_line("requests==2.19.1")
    deps = get_dependencies_from_json(r.as_ireq())
    assert len(deps) > 0


def test_get_deps_from_index():
    r = Requirement.from_line("requests==2.19.1")
    deps = get_dependencies_from_index(r.as_ireq())
    assert len(deps) > 0


def test_get_editable_from_index():
    r = InstallRequirement.from_editable("git+https://github.com/requests/requests.git#egg=requests[security]")
    deps = get_dependencies_from_index(r)
    assert len(deps) > 0
