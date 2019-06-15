# -*- coding=utf-8 -*-
import pytest
from packaging.specifiers import Specifier, SpecifierSet
from pip_shims import InstallRequirement

import requirementslib
from requirementslib.models.dependencies import (
    AbstractDependency,
    get_abstract_dependencies,
    get_dependencies,
    get_dependencies_from_index,
    get_dependencies_from_json,
)
from requirementslib.models.requirements import Requirement


@pytest.mark.needs_internet
def test_find_all_matches():
    r = Requirement.from_line("six")
    matches = r.find_all_matches()
    assert len(matches) > 0


@pytest.mark.needs_internet
def test_abstract_deps():
    abstract_deps = get_abstract_dependencies(["vistir[spinner]"])
    assert len(abstract_deps) == 1
    dep = abstract_deps[0]
    assert dep.specifiers._specs == SpecifierSet()._specs
    assert dep.requirement.name == "vistir"
    assert dep.requirement.extras == ("spinner",)
    assert dep.parent is None
    assert dep.markers is None
    assert len(dep.candidates) > 0
    assert len(dep.version_set) > 0


@pytest.mark.needs_internet
def test_two_deps():
    abstract_deps = get_abstract_dependencies(["requests>=2.14.0", "requests<=2.22.1"])
    dep1, dep2 = abstract_deps
    assert len(dep1.compatible_versions(dep2)) == 25
    new_dep = dep1.compatible_abstract_dep(dep2)
    versions = (">=2.14.0", "<=2.22.1")
    specs = [str(spec) for spec in new_dep.specifiers._specs]
    assert all(version in specs for version in versions)
    chosen_candidate = new_dep.candidates[-1]
    assert str(chosen_candidate.specifier) == "==2.22.0"
    deps = new_dep.get_deps(chosen_candidate)
    assert len(deps) == 4


@pytest.mark.needs_internet
def test_get_dependencies():
    r = Requirement.from_line("requests==2.19.1")
    deps = r.get_dependencies()
    assert len(deps) > 0
    deps_from_ireq = get_dependencies(r.as_ireq())
    assert len(deps_from_ireq) > 0
    assert sorted(set(deps_from_ireq)) == sorted(set(deps))


def get_abstract_deps():
    r = Requirement.from_line("requests")
    deps = [InstallRequirement.from_line(d) for d in r.get_dependencies()]
    abstract_deps = r.get_abstract_dependencies()
    req_abstract_dep = AbstractDependency.from_requirement(r)
    assert r.abstract_dep == req_abstract_dep
    assert len(abstract_deps) > 0
    deps_from_ireqs = get_abstract_dependencies(deps, parent=r)
    assert len(deps_from_ireqs) > 0
    assert sorted(set(deps_from_ireqs)) == sorted(set(abstract_deps))


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
    r = InstallRequirement.from_editable(
        "git+https://github.com/requests/requests.git#egg=requests[security]"
    )
    deps = get_dependencies_from_index(r)
    assert len(deps) > 0
