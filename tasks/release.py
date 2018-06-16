#!/usr/bin/env python
# -*- coding: utf-8 -*-
import invoke
import re
import sys
from .vendoring import mkdir_p, drop_dir, remove_all, _get_git_root
TASK_NAME = 'RELEASE'


def find_version(version_path):
    version_file = version_path.read_text()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


def get_version_file(ctx):
    version_path = _get_git_root(ctx) / 'src' / 'requirementslib' / '__init__.py'
    return version_path


def get_version(ctx):
    version = find_version(get_version_file(ctx))
    return version


def log(msg):
    global TASK_NAME
    print('[release.%s] %s' % TASK_NAME, msg)


def get_dist_dir(ctx):
    return _get_git_root(ctx) / 'dist'


def get_build_dir(ctx):
    return _get_git_root(ctx) / 'build'


def drop_dist_dirs(ctx):
    log('Dropping Dist dir...')
    drop_dir(get_dist_dir(ctx))
    log('Dropping build dir...')
    drop_dir(get_build_dir(ctx))


@invoke.task
def build_dists(ctx):
    global TASK_NAME
    TASK_NAME = 'BUILD_DISTS'
    drop_dist_dirs(ctx)
    log('Building sdist using %s ....' % sys.executable)
    ctx.run('%s setup.py sdist' % sys.executable)
    log('Building wheel using %s ....' % sys.executable)
    ctx.run('%s setup.py bdist_wheel' % sys.executable)


@invoke.task(build_dists)
def upload_dists(ctx):
    global TASK_NAME
    TASK_NAME = 'UPLOAD_RELEASE'
    log('Uploading distributions to pypi...')
    ctx.run('twine upload dist/*')


@invoke.task
def generate_changelog(ctx, commit=False):
    global TASK_NAME
    TASK_NAME = 'LOCK_CHANGELOG'
    log('Generating changelog...')
    ctx.run('towncrier')
    if commit:
        log('Committing...')
        ctx.run('git add .')
        ctx.run('git commit -m "Update changelog."')


@invoke.task
def tag_version(ctx, push=False):
    global TASK_NAME
    TASK_NAME = 'TAG_VERSION'
    version = get_version(ctx)
    log('Tagging revision: v%s' % version)
    ctx.run('git tag v%s' % version)
    if push:
        log('Pushing tags...')
        ctx.run('git push --tags')
