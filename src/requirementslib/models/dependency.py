# -*- coding=utf-8 -*-
from .._compat import RequirementPreparer, Resolver, WheelCache, RequirementSet, PackageFinder, TemporaryDirectory
from ..utils import fs_str, prepare_pip_source_args, get_pip_command, prepare_pip_source_args
import os
try:
    from pipenv.environments import PIPENV_CACHE_DIR as CACHE_DIR
except ImportError:
    from .._compat import USER_CACHE_DIR as CACHE_DIR

DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, 'pkgs'))
WHEEL_DOWNLOAD_DIR = fs_str(os.path.join(CACHE_DIR, 'wheels'))


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


def get_dependencies(dep, sources=None):
    dep.is_direct = True
    reqset = RequirementSet()
    reqset.add_requirement(dep)
    _, _, resolver = get_resolver(sources)
    resolver.resolve(reqset)
    requirements = reqset.requirements.values()
    reqset.cleanup_files()
    return requirements
