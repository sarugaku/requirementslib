# -*- coding=utf-8 -*-
import argparse
import io
import json
import os
import sys

import packaging.specifiers
import pip_shims.shims
from pip_shims.compat import get_session

from .environment import MYPY_RUNNING
from .models.lockfile import Lockfile
from .models.metadata import Dependency, get_package_from_requirement
from .models.pipfile import Pipfile
from .models.requirements import Requirement
from .models.utils import get_pinned_version, is_pinned_requirement

if MYPY_RUNNING:
    from typing import Dict, List, Tuple, Union


def get_prog():
    prog = "reqlib"
    try:
        prog_name = os.path.basename(sys.argv[0])
        if prog_name in ("__main__.py", "-c"):
            prog = "{0} -m requirementslib".format(sys.executable)
        else:
            prog = prog_name
    except (AttributeError, TypeError, IndexError):
        pass
    return prog


def parse_ireqs(requirement_file):
    install_cmd = pip_shims.shims.InstallCommand()
    session = get_session(install_cmd=install_cmd)
    ireqs = list(pip_shims.shims.parse_requirements(requirement_file, session))
    reqs = [Requirement.from_ireq(ireq) for ireq in ireqs]
    return reqs


def get_deps_from_local_req(req, allowed=None):
    deps = []
    lock = {}
    if allowed is None:
        allowed = {}
    for dep in req.req.dependencies[0].values():
        pkg, allowed_versions = get_package_from_requirement(dep)
        spec_str = ""
        if dep.specs:
            spec_str = str(dep.specifier)
        if dep.name in allowed:
            allowed[dep.name] = allowed[dep.name] & dep.specifier
        else:
            allowed[dep.name] = dep.specifier
        deps.append("{0}{1!s}".format(dep.name, spec_str))
        lock.update({pkg.info.name: pkg.releases.get_latest_lockfile()})
    return deps, lock, allowed


def get_deps_from_req(req, allowed=None):
    deps = []
    ireq = req.as_ireq()
    if allowed is None:
        allowed = {}
    pkg, allowed_versions = get_package_from_requirement(ireq)
    pkg = pkg.get_dependencies()
    deps.append(req.as_line(include_hashes=False))
    _, constraints_dict = pkg.pin_dependencies(include_extras=ireq.extras)
    for name, spec_list in constraints_dict.items():
        if name not in allowed:
            specset = next(iter(spec_list))
            if not isinstance(specset, packaging.specifiers.SpecifierSet):
                initial_specset = packaging.specifiers.SpecifierSet()
                initial_specset._specs = frozenset(specset)
                specset = initial_specset
            allowed[name] = specset
        else:
            specset = next(iter(spec_list), packaging.specifiers.SpecifierSet())
            print(
                "Merging specsets for package {0}: {1} & {2}".format(
                    name, allowed[name], specset
                )
            )
            if not allowed[name]:
                allowed[name] = specset
            else:
                if not isinstance(allowed[name], packaging.specifiers.SpecifierSet):
                    initial_specset = packaging.specifiers.SpecifierSet()
                    initial_specset._specs = frozenset(allowed[name])
                    allowed[name] = initial_specset & specset
                else:
                    allowed[name] &= specset
    deps.extend(["{0}{1}".format(k, v if v else "") for k, v in allowed.items()])
    # lock = pkg.get_latest_lockfile()
    lock = pkg.releases.get_latest_lockfile()
    return deps, lock, allowed


def get_parser():
    parser = argparse.ArgumentParser(get_prog())
    parser.add_argument("--lockfile", action="store", default="./Pipfile.lock")
    parser.add_argument("--pipfile", action="store", default="./Pipfile")
    parser.add_argument("--requirements", action="store", default="./requirements.txt")
    parser.add_argument(
        "--dev",
        action="store_true",
        default=False,
        help="When using Pipfile or Lockfile, include dev requirements?",
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--from-lockfile", help="Read requirements from lockfile at specified path"
    )
    input_group.add_argument(
        "--from-pipfile", help="Read requirements from pipfile at specified path"
    )
    input_group.add_argument(
        "--from-requirements",
        help="Read requirements from requirements.txt at specified path",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--to-pipfile",
        action="store_true",
        help="Output in pipfile format for pipenv consumption",
    )
    output_group.add_argument(
        "--to-lockfile", action="store_true", help="Output as lockfile format"
    )
    output_group.add_argument(
        "-r",
        "--to-pip",
        "--to-requirements",
        action="store_true",
        help="Output to requirement format for pip consumption",
    )
    parser.add_argument("packages", nargs="*", help="Packages to read as input")
    parser.add_argument("--resolve", action="store_true")
    return parser


def resolve_unpinned(constraints):
    resolved = {}
    new_constraints = {}
    for name, constraint in constraints.items():
        print("resolving {0}{1!s}".format(name, constraint))
        dep = Dependency.from_str("{0}{1}".format(name, str(constraint)))
        pinned_dep = dep.pin()
        pinned_dep = pinned_dep.get_dependencies()
        resolved.update({pinned_dep.name: pinned_dep.releases.get_latest_lockfile()})
        deps, constraints_dict = pinned_dep.pin_dependencies(include_extras=dep.extras)
        for name, spec_list in constraints_dict.items():
            if name not in new_constraints:
                new_constraints[name] = next(iter(spec_list))
            else:
                new_constraints[name] = new_constraints[name] & next(iter(spec_list))
    return resolved, new_constraints


def resolve(requirements):
    # type: (List[Requirement]) -> Tuple[List[str], Dict[str, Union[List[str], str]]]
    resolved = {}
    dep_lines = []
    allowed = {}
    for requirement in requirements:
        print("*** TOP LEVEL PACKAGE: {0} ******".format(requirement.name))
        print("Resolving package: {0}".format(requirement.name))
        if requirement.is_file_or_url:
            resolved.update(requirement.as_pipfile())
            dep_lines.append(requirement.as_line(include_hashes=False))
            more_lines, more_locks, allowed = get_deps_from_local_req(
                requirement, allowed
            )
            resolved.update(more_locks)
            dep_lines.extend(more_lines)
        else:
            more_lines, more_locks, allowed = get_deps_from_req(requirement, allowed)
            resolved.update(more_locks)
            dep_lines.extend(more_lines)
        if "certifi" in allowed:
            print("**** certifi: {0}".format(allowed["certifi"]))
    constraint_resolution, new_constraints = resolve_unpinned(allowed)
    resolution_passes = 0
    resolution_stable = True
    while new_constraints and resolution_passes < 12:
        print("******* PASS #{0}".format(resolution_passes))
        updated_constraint_resolution, updated_constraints = resolve_unpinned(
            new_constraints
        )
        resolution_passes += 1
        for k, v in updated_constraint_resolution.items():
            if (
                k not in constraint_resolution
                or updated_constraint_resolution[k] != constraint_resolution[k]
            ):
                resolution_stable = False
                break
        if resolution_stable:
            constraint_resolution.update(updated_constraint_resolution)
        new_constraints = updated_constraints
    resolved.update(constraint_resolution)
    new_deps = [Requirement.from_pipfile(name, val) for name, val in resolved.items()]
    resolved_lines = []
    for dep in new_deps:
        resolved_lines.append(dep.as_line(include_hashes=False))
    print("current dependency lines:")
    for line in resolved_lines:
        print("    {0}".format(line))
    resolved_lines = list(set(resolved_lines))
    return resolved_lines, resolved


def test_main():
    pipfile = Pipfile.load("./Pipfile")
    requirements = list(pipfile.dev_packages)
    dep_lines, resolved = resolve(requirements)
    with io.open("./requirements,txt", "w") as fh:
        fh.write("\n".join(dep_lines))
    print("Wrote requirements file: {0}".format("requirements.txt"))


def main():
    parser = get_parser()
    parsed = parser.parse_args()
    requirements = []
    if parsed.from_lockfile:
        lockfile = Lockfile.load(parsed.lockfile)
        requirements = lockfile.as_requirements(dev=parsed.dev)
    elif parsed.from_pipfile:
        pipfile = Pipfile.load(parsed.pipfile)
        print("Loaded pipfile: {0}".format(parsed.pipfile))
        additional_reqs = pipfile.dev_packages if parsed.dev else pipfile.packages
        requirements = list(additional_reqs)
    elif parsed.from_requirements:
        requirements = parse_ireqs(parsed.requirements)
    if parsed.packages:
        print(parsed.packages)
        requirements.extend(
            [Requirement.from_line(package) for package in parsed.packages]
        )
    if parsed.resolve:
        if parsed.to_pipfile:
            raise RuntimeError("Can't resolve to pipfile, invalid process")
        dep_lines, resolved = resolve(requirements)
        if parsed.to_lockfile:
            with io.open(parsed.lockfile, "w") as fh:
                json.dump(resolved, fh)
            print("Wrote Lockfile: {0}".format(parsed.lockfile))
        elif parsed.to_pip:
            with io.open(parsed.requirements, "w") as fh:
                fh.write("\n".join(dep_lines))
            print("Wrote requirements file: {0}".format(parsed.requirements))
    else:
        if parsed.to_pipfile:
            pipfile = Pipfile.load(parsed.pipfile)
            if parsed.dev:
                pipfile.dev_packages.extend(requirements)
            else:
                pipfile.packages.extend(requirements)
            pipfile.write()
            print("Wrote pipfile: {0}".format(parsed.pipfile))
        elif parsed.to_pip:
            with io.open(parsed.requirements, "w") as fh:
                fh.write(
                    "\n".join([req.as_line(include_hashes=False) for req in requirements])
                )
            print("Wrote requirements file: {0}".format(parsed.requirements))


if __name__ == "__main__":
    main()
