# -*- coding=utf-8 -*-
import attr
import copy
import requests
import six
from first import first
from packaging.version import parse as parse_version
from .utils import (
    full_groupby,
    key_from_ireq,
    is_pinned_requirement,
    name_from_req,
    make_install_requirement,
    format_requirement,
    version_from_ireq,
    partialclass,
)
from .cache import CACHE_DIR, DependencyCache
from .._compat import (
    RequirementPreparer,
    Resolver,
    WheelCache,
    RequirementSet,
    PackageFinder,
    TemporaryDirectory,
    InstallRequirement,
    FormatControl,
    RequirementTracker,
    pip_version,
)
from ..utils import (
    fs_str,
    prepare_pip_source_args,
    get_pip_command,
    temp_cd,
    log,
    mkdir_p,
)

import os

DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, "pkgs"))
WHEEL_DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, "wheels"))
DEPCACHE = DependencyCache()
WHEEL_CACHE = WheelCache(CACHE_DIR, FormatControl(None, None))


@attr.s
class AbstractDependency(object):
    name = attr.ib()
    specifiers = attr.ib()
    markers = attr.ib()
    candidates = attr.ib()
    requirement = attr.ib()
    parent = attr.ib()
    dep_dict = attr.ib(default=attr.Factory(dict))

    @property
    def sort_order(self):
        if self.is_root:
            return 1
        elif self.parent.is_root:
            return 2
        elif len(self.candidates) == 1:
            return 3
        return 4

    @property
    def version_set(self):
        """Return the set of versions for the candidates in this abstract dependency.

        :return: A set of matching versions
        :rtype: set(str)
        """

    def compatible_versions(self, other):
        """Find compatible version numbers between this abstract
        dependency and another one.

        :param other: An abstract dependency to compare with.
        :type other: :class:`~requirementslib.models.dependency.AbstractDependency`
        :return: A set of compatible version strings
        :rtype: set(str)
        """

        return self.version_set & other.version_set

    def compatible_abstract_dep(self, other):
        """Merge this abstract dependency with another one.

        Return the result of the merge as a new abstract dependency.

        :param other: An abstract dependency to merge with
        :type other: :class:`~requirementslib.models.dependency.AbstractDependency`
        :return: A new, combined abstract dependency
        :rtype: :class:`~requirementslib.models.dependency.AbstractDependency`
        """

        from .requirements import Requirement

        new_specifiers = self.specifiers & other.specifiers
        new_ireq = copy.deepcopy(self.requirement.ireq)
        new_ireq.req.specifier = new_specifiers
        new_requirement = Requirement.from_line(format_requirement(new_ireq))
        compatible_versions = self.compatible_versions(other)
        candidates = [
            c for c in self.candidates
            if parse_version(first(c.specifier._specs).version) in compatible_versions
        ]
        dep_dict = {}
        candidate_strings = [format_requirement(c) for c in candidates]
        for c in candidate_strings:
            if c in self.dep_dict:
                dep_dict[c] = self.dep_dict.get(c)
        return AbstractDependency(
            name=self.name,
            specifiers=new_specifiers,
            markers=self.markers,
            candidates=candidates,
            requirement=new_requirement,
            parent=self.parent,
            dep_dict=dep_dict,
        )

    def is_root(self):
        return self.parent is None

    def iter_candidates(self):
        for candidate in self.candidates:
            candidate.parent = self.parent
            yield candidate

    def get_deps(self, candidate):
        """Get the dependencies of the supplied candidate.

        :param candidate: An installrequirement
        :type candidate: :class:`~pip._internal.req.req_install.InstallRequirement`
        :return: A list of abstract dependencies
        :rtype: list[:class:`~requirementslib.models.dependency.AbstractDependency`]
        """

        key = format_requirement(candidate)
        if key not in self.dep_dict:
            from .requirements import Requirement

            req = Requirement.from_line(key)
            self.dep_dict[key] = req.get_abstract_dependencies()
        return self.dep_dict[key]

    @property
    def parent_is_pinned(self):
        from .requirements import Requirement

        if isinstance(self.parent, Requirement):
            return is_pinned_requirement(self.parent.ireq)
        # Handle InstallRequirements natively as well
        return is_pinned_requirement(self.parent)

    @classmethod
    def from_requirement(cls, requirement, parent=None):
        """Creates a new :class:`~requirementslib.models.dependency.AbstractDependency`
        from a :class:`~requirementslib.models.requirements.Requirement` object.

        This class is used to find all candidates matching a given set of specifiers
        and a given requirement.

        :param requirement: A requirement for resolution
        :type requirement: :class:`~requirementslib.models.requirements.Requirement` object.
        """
        name = requirement.normalized_name
        specifiers = requirement.ireq.specifier
        markers = requirement.ireq.markers
        extras = requirement.ireq.extras
        is_pinned = is_pinned_requirement(requirement.ireq)
        candidates = []
        if not is_pinned:
            for r in requirement.find_all_matches():
                req = make_install_requirement(name, r.version, extras=extras, markers=markers)
                req.req.link = r.location
                req.parent = parent
                candidates.append(req)
        else:
            candidates = [requirement.ireq]
        candidates = sorted(candidates, key=lambda k: parse_version(first(k.specifier._specs).version))
        return cls(
            name=name,
            specifiers=specifiers,
            markers=markers,
            candidates=candidates,
            requirement=requirement,
            parent=parent,
        )

    @classmethod
    def from_string(cls, line, parent=None):
        from .requirements import Requirement

        # abstract_deps = []
        req = Requirement.from_line(line)
        abstract_dep = cls.from_requirement(req, parent=parent)
        # req.abstract_dep = abstract_dep
        # abstract_deps.append(abstract_dep)
        # abstract_deps.extend(req.get_abstract_dependencies())
        return abstract_dep


class ResolutionError(Exception):
    pass


@attr.s
class DependencyResolver(object):
    pinned_deps = attr.ib(default=attr.Factory(dict))
    #: A list of current abstract dependencies
    abstract_deps = attr.ib(default=attr.Factory(list))
    #: A dictionary of abstract dependencies by name
    dep_dict = attr.ib(default=attr.Factory(dict))
    #: A dictionary of sets of version numbers that are valid for a candidate currently
    candidate_dict = attr.ib(default=attr.Factory(dict))
    #: A historical record of pins
    pin_history = attr.ib(default=attr.Factory(dict))

    @property
    def dependencies(self):
        return list(self.dep_dict.values())

    @property
    def resolution(self):
        return list(self.pinned_deps.values())

    def get_candidates(self, dep):
        """Takes an abstract dependency, finds the valid candidates

        :param dep: Abstract Dependency
        :returns: Valid candidates
        """
        if dep.name not in self.dep_dict:
            self.add_abstract_dep(dep)
        return self.dep_dict[dep.name].candidates

    def add_abstract_dep(self, dep):
        """Add an abstract dependency by either creating a new entry or
        merging with an old one.

        :param dep: An abstract dependency to add
        :type dep: :class:`~requirementslib.models.dependency.AbstractDependency`
        :raises ResolutionError: Raised when the given dependency is not compatible with
                                 an existing abstract dependency.
        """

        if dep.name in self.dep_dict:
            compatible_versions = self.dep_dict[dep.name].compatible_versions(dep)
            if compatible_versions:
                self.candidate_dict[dep.name] = compatible_versions
                self.dep_dict[dep.name] = self.dep_dict[dep.name].compatible_abstract_dep(dep)
            else:
                raise ResolutionError
        else:
            self.candidate_dict[dep.name] = dep.version_set
            self.dep_dict[dep.name] = dep

    def pin_deps(self):
        """Pins the current abstract dependencies and adds them to the history dict.

        Adds any new dependencies to the abstract dependencies already present by
        merging them together to form new, compatible abstract dependencies.
        """

        for name in list(self.dep_dict.keys()):
            candidates = self.dep_dict[name].candidates[:]
            abs_dep = self.dep_dict[name]
            while candidates:
                # TODO: Give up when candidates are exhausted?
                pin = candidates.pop()
                new_version = version_from_ireq(pin)
                # Move on from existing pins if the new pin isn't compatible
                if name in self.pinned_deps:
                    old_version = version_from_ireq(self.pinned_deps[name])
                    if (
                        new_version != old_version
                        and new_version not in self.candidate_dict[name]
                    ):
                        continue
                pin.parent = abs_dep.parent
                pin_subdeps = self.dep_dict[name].get_deps(pin)
                backup = self.dep_dict.copy(), self.candidate_dict.copy()
                try:
                    for pin_dep in pin_subdeps:
                        self.add_abstract_dep(pin_dep)
                except ResolutionError:
                    self.dep_dict, self.candidate_dict = backup
                    continue
                else:
                    self.pinned_deps[name] = pin
                    break

    def resolve(self, root_nodes, max_rounds=20):
        """Resolves dependencies using a backtracking resolver and multiple endpoints.

        Note: this resolver caches aggressively.
        Runs for *max_rounds* or until any two pinning rounds yield the same outcome.

        :param root_nodes: A list of the root requirements.
        :type root_nodes: list[:class:`~requirementslib.models.requirements.Requirement`]
        :param max_rounds: The max number of resolution rounds, defaults to 20
        :param max_rounds: int, optional
        :raises RuntimeError: Raised when max rounds is exceeded without a resolution.
        """

        self.dep_dict = {}
        for dep in root_nodes:
            if isinstance(dep, six.string_types):
                dep = AbstractDependency.from_string(dep)
            elif not isinstance(dep, AbstractDependency):
                dep = AbstractDependency.from_requirement(dep)
            self.add_abstract_dep(dep)
        for _ in range(max_rounds):
            self.pin_deps()
            if len(self.pinned_deps.keys()) == len(self.dep_dict.keys()):
                return
        # TODO: Raise a better error.
        raise RuntimeError('cannot resolve after {} rounds'.format(max_rounds))


def get_resolver(sources=None):
    """Given a list of sources, return a finder, preparer, and resolver.

    :param sources: A list of pipfile-formatted sources, defaults to None
    :param sources: list[dict], optional
    :return: A 3-tuple of finder, preparer, resolver
    :rtype: (:class:`~pip._internal.index.PackageFinder`, :class:`~pip._internal.operations.prepare.RequirementPreparer`, :class:`~pip._internal.resolve.Resolver`)
    """

    pip_command = get_pip_command()
    if not sources:
        sources = [
            {"url": "https://pypi.org/simple", "name": "pypi", "verify_ssl": True}
        ]
    pip_args = []
    pip_args = prepare_pip_source_args(sources, pip_args)
    pip_options, _ = pip_command.parser.parse_args(pip_args)
    pip_options.cache_dir = CACHE_DIR
    mkdir_p(CACHE_DIR)
    session = pip_command._build_session(pip_options)
    wheel_cache = WheelCache(CACHE_DIR, pip_options.format_control)
    finder = PackageFinder(
        find_links=[],
        index_urls=[s.get("url") for s in sources],
        trusted_hosts=[],
        allow_all_prereleases=pip_options.pre,
        session=session,
    )
    download_dir = DOWNLOAD_DIR
    mkdir_p(download_dir)
    _build_dir = TemporaryDirectory(fs_str("build"))
    _source_dir = TemporaryDirectory(fs_str("source"))
    preparer = partialclass(
        RequirementPreparer,
        build_dir=_build_dir.name,
        src_dir=_source_dir.name,
        download_dir=download_dir,
        wheel_download_dir=WHEEL_DOWNLOAD_DIR,
        progress_bar="off",
        build_isolation=False,
    )
    resolver = partialclass(
        Resolver,
        finder=finder,
        session=session,
        upgrade_strategy="to-satisfy-only",
        force_reinstall=True,
        ignore_dependencies=False,
        ignore_requires_python=True,
        ignore_installed=True,
        isolated=False,
        wheel_cache=wheel_cache,
        use_user_site=False,
    )
    if parse_version(pip_version) >= parse_version('18.0.0'):
        with RequirementTracker() as req_tracker:
            preparer = preparer(req_tracker=req_tracker)
            resolver = resolver(preparer=preparer)
    else:
        preparer = preparer()
        resolver = resolver(preparer=preparer)
    return finder, preparer, resolver


def find_all_matches(finder, ireq):
    """Find all matching dependencies using the supplied finder and the
    given ireq.

    :param finder: A package finder for discovering matching candidates.
    :type finder: :class:`~pip._internal.index.PackageFinder`
    :param ireq: An install requirement.
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :return: A list of matching candidates.
    :rtype: list[:class:`~pip._internal.index.InstallationCandidate`]
    """

    matches = [m for m in candidates if m.version in ireq.specifier]
    return matches


def get_abstract_dependencies(reqs, sources=None, parent=None):
    """Get all abstract dependencies for a given list of requirements.

    Given a set of requirements, convert each requirement to an Abstract Dependency.

    :param reqs: A list of Requirements
    :type reqs: list[:class:`~requirementslib.models.requirements.Requirement`]
    :param sources: Pipfile-formatted sources, defaults to None
    :param sources: list[dict], optional
    :param parent: The parent of this list of dependencies, defaults to None
    :param parent: :class:`~requirementslib.models.requirements.Requirement`, optional
    :return: A list of Abstract Dependencies
    :rtype: list[:class:`~requirementslib.models.dependency.AbstractDependency`]
    """

def get_abstract_dependencies(reqs, sources=None, parent=None):
    deps = []
    from .requirements import Requirement

    for req in reqs:
        if isinstance(req, InstallRequirement):
            requirement = Requirement.from_line(
                "{0}{1}".format(req.name, req.specifier)
            )
            if req.link:
                requirement.req.link = req.link
                requirement.markers = req.markers
                requirement.req.markers = req.markers
                requirement.extras = req.extras
                requirement.req.extras = req.extras
        elif isinstance(req, Requirement):
            requirement = copy.deepcopy(req)
        else:
            requirement = Requirement.from_line(req)
        dep = AbstractDependency.from_requirement(requirement, parent=parent)
        deps.append(dep)
    return deps


def get_dependencies(ireq, sources=None, parent=None):
    if not isinstance(ireq, InstallRequirement):
        name = getattr(
            ireq, "project_name", getattr(ireq, "project", getattr(ireq, "name", None))
        )
        version = getattr(ireq, "version")
        ireq = InstallRequirement.from_line("{0}=={1}".format(name, version))
    cached_deps = get_dependencies_from_cache(ireq)
    if not cached_deps:
        cached_deps = get_dependencies_from_wheel_cache(ireq)
    if not cached_deps:
        cached_deps = get_dependencies_from_json(ireq)
    if not cached_deps:
        cached_deps = get_dependencies_from_index(ireq, sources)
    return set(cached_deps)


def get_dependencies_from_wheel_cache(ireq):
    """Retrieves dependencies for the given install requirement from the wheel cache.

    :param ireq: A single InstallRequirement
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str) or None
    """

    matches = WHEEL_CACHE.get(ireq.link, name_from_req(ireq.req))
    if matches:
        return set(matches)
    return


def get_dependencies_from_json(ireq):
    """Retrieves dependencies for the given install requirement from the json api.

    :param ireq: A single InstallRequirement
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str) or None
    """

    if not (is_pinned_requirement(ireq)):
        raise TypeError("Expected pinned InstallRequirement, got {}".format(ireq))

    session = requests.session()

    def gen(ireq):
        url = "https://pypi.org/pypi/{0}/json".format(ireq.req.name)
        releases = session.get(url).json()["releases"]
        matches = [r for r in releases if "=={0}".format(r) == str(ireq.req.specifier)]
        if not matches:
            return

        release_requires = session.get(
            "https://pypi.org/pypi/{0}/{1}/json".format(ireq.req.name, matches[0])
        ).json()
        try:
            requires_dist = release_requires["info"]["requires_dist"]
        except KeyError:
            try:
                requires_dist = release_requires["info"]["requires"]
            except KeyError:
                return
        if requires_dist:
            for requires in requires_dist:
                i = InstallRequirement.from_line(requires)
                if "extra" not in repr(i.markers):
                    yield i

    if ireq not in DEPCACHE:
        DEPCACHE[ireq] = [str(g) for g in gen(ireq)]

    try:
        cache_val = DEPCACHE[ireq]
    except KeyError:
        cache_val = None
    return set(cache_val)


def get_dependencies_from_cache(dep):
    """Retrieves dependencies for the given install requirement from the dependency cache.

    :param ireq: A single InstallRequirement
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str) or None
    """

    if dep in DEPCACHE:
        return set(DEPCACHE[dep])
    return


def get_dependencies_from_index(dep, sources=None):
    """Retrieves dependencies for the given install requirement from the pip resolver.

    :param ireq: A single InstallRequirement
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :param sources: Pipfile-formatted sources, defaults to None
    :type sources: list[dict], optional
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str) or None
    """

    dep.is_direct = True
    reqset = RequirementSet()
    reqset.add_requirement(dep)
    _, _, resolver = get_resolver(sources)
    from setuptools.dist import distutils

    if not dep.prepared and dep.link is not None:
        with temp_cd(dep.setup_py_dir):
            try:
                distutils.core.run_setup(dep.setup_py)
            except Exception:
                pass
    try:
        resolver.resolve(reqset)
    except Exception:
        reqset.cleanup_files()
        return set()
    requirements = reqset.requirements.values()
    reqset.cleanup_files()
    return set(requirements)


def get_grouped_dependencies(constraints):
    # We need to track what contributed a specifierset
    # as well as which specifiers were required by the root node
    # in order to resolve any conflicts when we are deciding which thing to backtrack on
    # then we take the loose match (which _is_ flexible) and start moving backwards in
    # versions by popping them off of a stack and checking for the conflicting package
    for _, ireqs in full_groupby(constraints, key=key_from_ireq):
        ireqs = list(ireqs)
        editable_ireq = first(ireqs, key=lambda ireq: ireq.editable)
        if editable_ireq:
            yield editable_ireq  # ignore all the other specs: the editable one is the one that counts
            continue
        ireqs = iter(ireqs)
        # deepcopy the accumulator so as to not modify the self.our_constraints invariant
        combined_ireq = copy.deepcopy(next(ireqs))
        for ireq in ireqs:
            # NOTE we may be losing some info on dropped reqs here
            try:
                combined_ireq.req.specifier &= ireq.req.specifier
            except TypeError:
                if ireq.req.specifier._specs and not combined_ireq.req.specifier._specs:
                    combined_ireq.req.specifier._specs = ireq.req.specifier._specs
            combined_ireq.constraint &= ireq.constraint
            if not combined_ireq.markers:
                combined_ireq.markers = ireq.markers
            else:
                _markers = combined_ireq.markers._markers
                if not isinstance(_markers[0], (tuple, list)):
                    combined_ireq.markers._markers = [
                        _markers,
                        "and",
                        ireq.markers._markers,
                    ]
            # Return a sorted, de-duped tuple of extras
            combined_ireq.extras = tuple(
                sorted(tuple(combined_ireq.extras) + tuple(ireq.extras))
            )
        yield combined_ireq
