# -*- coding=utf-8 -*-
import attr
import copy
import requests
from collections import defaultdict
from first import first
from itertools import chain
from .utils import full_groupby, key_from_ireq, is_pinned_requirement, name_from_req, _requirement_to_str_lowercase_name
from .cache import CACHE_DIR, DependencyCache
from .._compat import RequirementPreparer, Resolver, WheelCache, RequirementSet, PackageFinder, TemporaryDirectory, InstallRequirement, FormatControl
from ..utils import fs_str, prepare_pip_source_args, get_pip_command, prepare_pip_source_args, temp_cd
import os

DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, 'pkgs'))
WHEEL_DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, 'wheels'))
DEPCACHE = DependencyCache()
WHEEL_CACHE = WheelCache(CACHE_DIR, FormatControl(None, None))


@attr.s
class AbstractDependency(object):
    name = attr.ib(default=None)
    specifiers = attr.ib(default=None)
    markers = attr.ib(default=None)
    candidates = attr.ib(default=None)
    requirement = attr.ib(default=None)
    parent = attr.ib(default=None)
    dep_dict = attr.ib(default=attr.Factory(defaultdict))

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
        return set([c.get_version() for c in self.candidates])

    def compatible_versions(self, other):
        return self.version_set & other.version_set

    def is_root(self):
        return self.parent is None

    def iter_candidates(self):
        for candidate in self.candidates:
            candidate.parent = self.parent
            yield candidate

    def get_deps(self, candidate):
        key = candidate.as_line()
        if key not in self.dep_dict:
            self.dep_dict[key] = candidate.get_abstract_dependencies()
        return self.dep_dict[key]

    @property
    def parent_is_pinned(self):
        return is_pinned_requirement(self.parent.ireq)

    @classmethod
    def from_requirement(cls, requirement, parent=None):
        """from_requirement Creates a new :class:`~requirementslib.models.dependency.AbstractDependency`
        from a :class:`~requirementslib.models.requirements.Requirement` object.

        This class is used to find all candidates matching a given set of specifiers
        and a given requirement.

        :param requirement: A requirement for resolution
        :type requirement: :class:`~requirementslib.models.requirements.Requirement` object.
        """
        name = requirement.normalized_name
        specifiers = requirement.ireq.specifier
        markers = requirement.ireq.markers
        is_pinned = is_pinned_requirement(requirement.ireq)
        candidates = []
        if not is_pinned:
            from .requirements import Requirement
            for r in requirement.find_all_matches():
                req = Requirement.from_line("{0}=={1}".format(name, r.version))
                req.req.link = r.location
                req.parent = parent
                candidates.append(req)
        else:
            candidates = [requirement]
        candidates = sorted(candidates, key=lambda k: k.get_version())
        return cls(name=name, specifiers=specifiers, markers=markers, candidates=candidates, requirement=requirement, parent=parent)

    @classmethod
    def from_string(cls, line, parent=None):
        from .requirements import Requirement
        abstract_deps = []
        req = Requirement.from_line(line)
        abstract_dep = cls.from_requirement(req, parent=parent)
        # req.abstract_dep = abstract_dep
        # abstract_deps.append(abstract_dep)
        # abstract_deps.extend(req.get_abstract_dependencies())
        return abstract_dep


@attr.s
class DependencyResolver(object):
    root_nodes = attr.ib(default=attr.Factory(list))
    abstract_deps = attr.ib(default=attr.Factory(list))
    dep_dict = attr.ib(default=attr.Factory(defaultdict))

    def resolve(self):
        dep_dict = defaultdict(list)
        for node in self.root_nodes:
            abs_deps = node.get_abstract_dependencies()
            for dep in abs_deps:
                candidate = first(dep.iter_candidates())
                abs_deps.extend(dep.get_deps(candidate))
        for dep in abs_deps:
            dep_dict[dep.name].append(dep)
        self.abstract_deps = abs_deps
        self.dep_dict = dep_dict


def merge_abstract_dependencies(deps):
    parents = [dep.parent for dep in deps]
    deps = deps + list(parents)
    base_deps = [dep for dep in deps if dep.parent is None]
    base_deps.extend([dep for dep in deps if dep.parent and dep.parent.is_root()])
    candidates = defaultdict(list)
    for dep in base_deps:
        if dep.name in candidates:
            candidates[dep.name] = set(candidates[dep.name]) & set(dep.candidates)
        else:
            candidates[dep.name] = set(dep.candidates)
    for dep in deps:
        if dep.name in candidates:
            candidates[dep.name] = set(candidates[dep.name]) & set(dep.candidates)
        else:
            candidates[dep.name] = set(dep.candidates)
    return candidates


def get_resolver(sources=None):
    pip_command = get_pip_command()
    if not sources:
        sources = [{'url': 'https://pypi.org/simple', 'name': 'pypi', 'verify_ssl': True},]
    pip_args = []
    pip_args = prepare_pip_source_args(sources, pip_args)
    pip_options, _ = pip_command.parser.parse_args(pip_args)
    pip_options.cache_dir = CACHE_DIR
    session = pip_command._build_session(pip_options)
    wheel_cache = WheelCache(CACHE_DIR, pip_options.format_control)
    finder = PackageFinder(
        find_links=[],
        index_urls=[s.get('url') for s in sources],
        trusted_hosts=[],
        allow_all_prereleases=True,
        session=session,
    )
    download_dir = DOWNLOAD_DIR
    _build_dir = TemporaryDirectory(fs_str('build'))
    _source_dir = TemporaryDirectory(fs_str('source'))
    preparer = RequirementPreparer(
        build_dir=_build_dir.name,
        src_dir=_source_dir.name,
        download_dir=download_dir,
        wheel_download_dir=WHEEL_DOWNLOAD_DIR,
        progress_bar='off',
        build_isolation=True
    )
    resolver = Resolver(
        preparer=preparer,
        finder=finder,
        session=session,
        upgrade_strategy="to-satisfy-only",
        force_reinstall=False,
        ignore_dependencies=False,
        ignore_requires_python=False,
        ignore_installed=True,
        isolated=True,
        wheel_cache=wheel_cache,
        use_user_site=False,
    )
    return finder, preparer, resolver


def find_all_matches(finder, ireq):
    candidates = finder.find_all_candidates(ireq.name)
    matches = [m for m in candidates if m.version in ireq.specifier]
    return matches


def get_match_dependencies(ireqs):
    return [get_dependencies_from_index(ir) for ir in ireqs]


def get_abstract_dependencies(reqs, sources=None, parent=None):
    deps = []
    from .requirements import Requirement
    for req in reqs:
        if isinstance(req, InstallRequirement):
            requirement = Requirement.from_line("{0}{1}".format(req.name, req.specifier))
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
        name = getattr(ireq, 'project_name', getattr(ireq, 'project', getattr(ireq, 'name', None)))
        version = getattr(ireq, 'version')
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
    matches = WHEEL_CACHE.get(ireq.link, name_from_req(ireq.req))
    if matches:
        return set(matches)
    return


def get_dependencies_from_json(ireq):
    if not (is_pinned_requirement(ireq)):
        raise TypeError('Expected pinned InstallRequirement, got {}'.format(ireq))

    session = requests.session()

    def gen(ireq):
        url = 'https://pypi.org/pypi/{0}/json'.format(ireq.req.name)
        releases = session.get(url).json()['releases']
        matches = [
            r for r in releases
            if '=={0}'.format(r) == str(ireq.req.specifier)
        ]
        if not matches:
            return

        release_requires = session.get(
            'https://pypi.org/pypi/{0}/{1}/json'.format(
                ireq.req.name, matches[0],
            ),
        ).json()
        try:
            requires_dist = release_requires['info']['requires_dist']
        except KeyError:
            try:
                requires_dist = release_requires['info']['requires']
            except KeyError:
                return
        if requires_dist:
            for requires in requires_dist:
                i = InstallRequirement.from_line(requires)
                if 'extra' not in repr(i.markers):
                    yield i
    if ireq not in DEPCACHE:
        DEPCACHE[ireq] = [str(g) for g in gen(ireq)]

    try:
        cache_val = DEPCACHE[ireq]
    except KeyError:
        cache_val = None
    return set(cache_val)


def get_dependencies_from_cache(dep):
    if dep in DEPCACHE:
        return set(DEPCACHE[dep])
    return


def get_dependencies_from_index(dep, sources=None):
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
                    combined_ireq.markers._markers = [_markers, 'and', ireq.markers._markers]
            # Return a sorted, de-duped tuple of extras
            combined_ireq.extras = tuple(sorted(set(tuple(combined_ireq.extras) + tuple(ireq.extras))))
        yield combined_ireq
