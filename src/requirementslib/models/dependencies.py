# -*- coding=utf-8 -*-

import copy
import functools
import os

import attr
import first
import packaging.version
import requests

from .._compat import (
    pip_version,
    FormatControl,
    InstallRequirement,
    PackageFinder,
    RequirementPreparer,
    RequirementSet,
    RequirementTracker,
    Resolver,
    TemporaryDirectory,
    WheelCache,
)
from ..utils import (
    fs_str,
    get_pip_command,
    mkdir_p,
    prepare_pip_source_args,
    temp_cd,
)
from .cache import CACHE_DIR, DependencyCache
from .utils import (
    format_requirement,
    full_groupby,
    is_pinned_requirement,
    key_from_ireq,
    make_install_requirement,
    name_from_req,
    partialclass,
    version_from_ireq,
)


PKGS_DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, "pkgs"))
WHEEL_DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, "wheels"))

DEPENDENCY_CACHE = DependencyCache()
WHEEL_CACHE = WheelCache(CACHE_DIR, FormatControl(None, None))


def find_all_matches(finder, ireq, pre=False):
    """Find all matching dependencies using the supplied finder and the
    given ireq.

    :param finder: A package finder for discovering matching candidates.
    :type finder: :class:`~pip._internal.index.PackageFinder`
    :param ireq: An install requirement.
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :return: A list of matching candidates.
    :rtype: list[:class:`~pip._internal.index.InstallationCandidate`]
    """

    all_candidates = finder.find_all_candidates(ireq.name)
    filter_candidates = functools.partial(ireq.specifier.filter, (
        candidate.version for candidate in all_candidates
    ))
    allowed_versions = list(filter_candidates(prereleases=pre))
    if not pre and not allowed_versions:
        allowed_versions = list(filter_candidates(prereleases=True))
    candidates = {c for c in all_candidates if c.version in allowed_versions}
    return candidates


@attr.s
class AbstractDependency(object):
    name = attr.ib()
    specifiers = attr.ib()
    markers = attr.ib()
    candidates = attr.ib()
    requirement = attr.ib()
    parent = attr.ib()
    finder = attr.ib()
    dep_dict = attr.ib(default=attr.Factory(dict))

    @property
    def version_set(self):
        """Return the set of versions for the candidates in this abstract dependency.

        :return: A set of matching versions
        :rtype: set(str)
        """

        return set(packaging.version.parse(version_from_ireq(c)) for c in self.candidates)

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
            c
            for c in self.candidates
            if packaging.version.parse(version_from_ireq(c)) in compatible_versions
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
            finder=self.finder
        )

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
        is_constraint = bool(parent)
        finder = get_finder(sources=None)
        candidates = []
        if not is_pinned:
            for r in requirement.find_all_matches(finder=finder):
                req = make_install_requirement(
                    name, r.version, extras=extras, markers=markers, constraint=is_constraint,
                )
                req.req.link = r.location
                req.parent = parent
                candidates.append(req)
        else:
            candidates = [requirement.ireq]
        candidates = sorted(
            set(candidates), key=lambda k: packaging.version.parse(version_from_ireq(k)),
        )
        return cls(
            name=name,
            specifiers=specifiers,
            markers=markers,
            candidates=candidates,
            requirement=requirement,
            parent=parent,
            finder=finder,
        )

    @classmethod
    def from_string(cls, line, parent=None):
        from .requirements import Requirement

        req = Requirement.from_line(line)
        abstract_dep = cls.from_requirement(req, parent=parent)
        return abstract_dep


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
    """Get all dependencies for a given install requirement.

    :param ireq: A single InstallRequirement
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :param sources: Pipfile-formatted sources, defaults to None
    :type sources: list[dict], optional
    :param parent: The parent of this list of dependencies, defaults to None
    :type parent: :class:`~pip._internal.req.req_install.InstallRequirement`
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str)
    """

    if not isinstance(ireq, InstallRequirement):
        name = getattr(
            ireq, "project_name", getattr(ireq, "project", getattr(ireq, "name", None))
        )
        version = getattr(ireq, "version")
        ireq = InstallRequirement.from_line("{0}=={1}".format(name, version))
    getters = [
        get_dependencies_from_cache,
        get_dependencies_from_wheel_cache,
        get_dependencies_from_json,
        functools.partial(get_dependencies_from_index, sources=sources)
    ]
    for getter in getters:
        deps = getter(ireq)
        if deps is not None:
            return deps
    raise RuntimeError('failed to get dependencies for {}'.format(ireq))


def get_dependencies_from_wheel_cache(ireq):
    """Retrieves dependencies for the given install requirement from the wheel cache.

    :param ireq: A single InstallRequirement
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str) or None
    """

    matches = WHEEL_CACHE.get(ireq.link, name_from_req(ireq.req))
    if matches:
        matches = set(matches)
        if not DEPENDENCY_CACHE.get(ireq):
            DEPENDENCY_CACHE[ireq] = [format_requirement(m) for m in matches]
        return matches
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
    version = str(ireq.req.specifier).lstrip("=")

    def gen(ireq):
        info = session.get(
            "https://pypi.org/pypi/{0}/{1}/json".format(ireq.req.name, version)
        ).json()["info"]
        requires_dist = info.get("requires_dist", info.get("requires"))
        if not requires_dist:   # The API can return None for this.
            return
        for requires in requires_dist:
            i = InstallRequirement.from_line(requires)
            if "extra" not in repr(i.markers):
                # TODO: Get dependencies for matching extra.
                yield format_requirement(i)

    if ireq not in DEPENDENCY_CACHE:
        reqs = DEPENDENCY_CACHE[ireq] = list(gen(ireq))
        req_iter = iter(reqs)
    else:
        req_iter = gen(ireq)
    return set(req_iter)


def get_dependencies_from_cache(dep):
    """Retrieves dependencies for the given install requirement from the dependency cache.

    :param ireq: A single InstallRequirement
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str) or None
    """

    if dep in DEPENDENCY_CACHE:
        return set(DEPENDENCY_CACHE[dep])
    return


def get_dependencies_from_index(dep, sources=None, pip_options=None, wheel_cache=None):
    """Retrieves dependencies for the given install requirement from the pip resolver.

    :param ireq: A single InstallRequirement
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :param sources: Pipfile-formatted sources, defaults to None
    :type sources: list[dict], optional
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str) or None
    """

    finder = get_finder(sources=sources, pip_options=pip_options)
    if not wheel_cache:
        wheel_cache = WheelCache(CACHE_DIR, pip_options.format_control)
    dep.is_direct = True
    reqset = RequirementSet()
    reqset.add_requirement(dep)
    _, resolver = get_resolver(finder=finder, wheel_cache=wheel_cache)
    resolver.require_hashes = False
    from setuptools.dist import distutils

    if not dep.prepared and dep.link is not None:
        with temp_cd(dep.setup_py_dir):
            try:
                distutils.core.run_setup(dep.setup_py)
            except Exception:
                pass
    requirements = None
    prev_tracker = os.environ.get('PIP_REQ_TRACKER')
    try:
        requirements = resolver._resolve_one(reqset, dep)
    except Exception:
        requirements = []
    finally:
        reqset.cleanup_files()
        del os.environ['PIP_REQ_TRACKER']
        if prev_tracker:
            os.environ['PIP_REQ_TRACKER'] = prev_tracker
        try:
            wheel_cache.cleanup()
        except AttributeError:
            pass

    # requirements = reqset.requirements.values()
    reqs = set(requirements)
    DEPENDENCY_CACHE[dep] = [format_requirement(r) for r in reqs]
    return reqs


def get_pip_options(sources=None, pip_command=None, *args):
    """Build a pip command from a list of sources

    :param *args: positional arguments passed through to the pip parser
    :param sources: A list of pipfile-formatted sources, defaults to None
    :param sources: list[dict], optional
    :param pip_command: A pre-built pip command instance
    :type pip_command: :class:`~pip._internal.cli.base_command.Command`
    :return: An instance of pip_options using the supplied arguments plus sane defaults
    :rtype: :class:`~pip._internal.cli.cmdoptions`
    """

    if not pip_command:
        pip_command = get_pip_command()
    if not sources:
        sources = [
            {"url": "https://pypi.org/simple", "name": "pypi", "verify_ssl": True}
        ]
    mkdir_p(CACHE_DIR)
    pip_args = [pos_arg for pos_arg in args]
    pip_args = prepare_pip_source_args(sources, pip_args)
    pip_options, _ = pip_command.parser.parse_args(pip_args)
    pip_options.cache_dir = CACHE_DIR
    return pip_options


def get_finder(sources=None, pip_command=None, pip_options=None):
    """Get a package finder for looking up candidates to install

    :param sources: A list of pipfile-formatted sources, defaults to None
    :param sources: list[dict], optional
    :param pip_command: A pip command instance, defaults to None
    :type pip_command: :class:`~pip._internal.cli.base_command.Command`
    :param pip_options: A pip options, defaults to None
    :type pip_options: :class:`~pip._internal.cli.cmdoptions`
    :return: A package finder
    :rtype: :class:`~pip._internal.index.PackageFinder`
    """

    if not pip_command:
        pip_command = get_pip_command()
    if not sources:
        sources = [
            {"url": "https://pypi.org/simple", "name": "pypi", "verify_ssl": True}
        ]
    if not pip_options:
        pip_options = get_pip_options(sources=sources, pip_command=pip_command)
    session = pip_command._build_session(pip_options)
    finder = PackageFinder(
        find_links=[],
        index_urls=[s.get("url") for s in sources],
        trusted_hosts=[],
        allow_all_prereleases=pip_options.pre,
        session=session,
    )
    return finder


def get_resolver(finder=None, wheel_cache=None):
    """Given a package finder, return a preparer, and resolver.

    :param finder: A package finder to use for searching the index
    :type finder: :class:`~pip._internal.index.PackageFinder`
    :return: A 3-tuple of finder, preparer, resolver
    :rtype: (:class:`~pip._internal.operations.prepare.RequirementPreparer`, :class:`~pip._internal.resolve.Resolver`)
    """

    pip_command = get_pip_command()
    pip_options = get_pip_options(pip_command=pip_command)
    if not finder:
        finder = get_finder(pip_command=pip_command, pip_options=pip_options)
    if not wheel_cache:
        wheel_cache = WheelCache(CACHE_DIR, pip_options.format_control)
    download_dir = PKGS_DOWNLOAD_DIR
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
        session=finder.session,
        upgrade_strategy="to-satisfy-only",
        force_reinstall=True,
        ignore_dependencies=False,
        ignore_requires_python=True,
        ignore_installed=True,
        isolated=False,
        wheel_cache=wheel_cache,
        use_user_site=False,
    )
    if packaging.version.parse(pip_version) >= packaging.version.parse('18'):
        with RequirementTracker() as req_tracker:
            preparer = preparer(req_tracker=req_tracker)
            resolver = resolver(preparer=preparer)
    else:
        preparer = preparer()
        resolver = resolver(preparer=preparer)
    return preparer, resolver


def get_grouped_dependencies(constraints):
    # We need to track what contributed a specifierset
    # as well as which specifiers were required by the root node
    # in order to resolve any conflicts when we are deciding which thing to backtrack on
    # then we take the loose match (which _is_ flexible) and start moving backwards in
    # versions by popping them off of a stack and checking for the conflicting package
    for _, ireqs in full_groupby(constraints, key=key_from_ireq):
        ireqs = list(ireqs)
        editable_ireq = first.first(ireqs, key=lambda ireq: ireq.editable)
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
                sorted(set(tuple(combined_ireq.extras) + tuple(ireq.extras)))
            )
        yield combined_ireq
