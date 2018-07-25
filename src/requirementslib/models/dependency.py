# -*- coding=utf-8 -*-
import copy
import requests
from first import first
from .utils import full_groupby, key_from_ireq, is_pinned_requirement, name_from_req
from .cache import CACHE_DIR, DependencyCache
from .._compat import RequirementPreparer, Resolver, WheelCache, RequirementSet, PackageFinder, TemporaryDirectory, InstallRequirement, FormatControl
from ..utils import fs_str, prepare_pip_source_args, get_pip_command, prepare_pip_source_args
import os

DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, 'pkgs'))
WHEEL_DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, 'wheels'))
DEPCACHE = DependencyCache()
WHEEL_CACHE = WheelCache(CACHE_DIR, FormatControl(None, None))


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
        build_isolation=False
    )
    resolver = Resolver(
        preparer=preparer,
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
    return finder, preparer, resolver


def find_all_matches(finder, ireq):
    candidates = finder.find_all_candidates(ireq.name)
    matches = [m for m in candidates if m.version in ireq.specifier]
    return matches


def get_match_dependencies(ireqs):
    return [get_dependencies_from_index(ir) for ir in ireqs]


def get_dependencies(ireq, sources=None):
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
    return cached_deps


def get_dependencies_from_wheel_cache(ireq):
    return WHEEL_CACHE.get(ireq.link, name_from_req(ireq.req))


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
    return cache_val


def get_dependencies_from_cache(dep):
    if dep in DEPCACHE:
        return DEPCACHE[dep]
    return


def get_dependencies_from_index(dep, sources=None):
    dep.is_direct = True
    reqset = RequirementSet()
    reqset.add_requirement(dep)
    _, _, resolver = get_resolver(sources)
    resolver.resolve(reqset)
    requirements = reqset.requirements.values()
    reqset.cleanup_files()
    return requirements


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
