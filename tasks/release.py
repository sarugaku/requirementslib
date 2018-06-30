#!/usr/bin/env python
# -*- coding: utf-8 -*-
import invoke
from parver import Version
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
    print('[release] %s' % msg)


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
def build_dists(ctx, drop_existing=True):
    if drop_existing:
        drop_dist_dirs(ctx)
    log('Building sdist using %s ....' % sys.executable)
    ctx.run('%s setup.py sdist' % sys.executable)
    log('Building wheel using %s ....' % sys.executable)
    ctx.run('%s setup.py bdist_wheel' % sys.executable)


@invoke.task(build_dists)
def upload_dists(ctx, build=False):
    if build:
        build_dists(ctx)
    log('Uploading distributions to pypi...')
    ctx.run('twine upload dist/*')


@invoke.task
def generate_changelog(ctx, commit=False):
    log('Generating changelog...')
    ctx.run('towncrier')
    if commit:
        log('Committing...')
        ctx.run('git add .')
        ctx.run('git commit -m "Update changelog."')


@invoke.task
def tag_version(ctx, push=False):
    version = get_version(ctx)
    log('Tagging revision: v%s' % version)
    ctx.run('git tag v%s' % version)
    if push:
        log('Pushing tags...')
        ctx.run('git push --tags')


@invoke.task
def bump_version(ctx, dry_run=False, major=False, minor=False, micro=True, dev=False, pre=False, tag=None, clear=False, commit=False,):
    _current_version = get_version(ctx)
    current_version = Version.parse(_current_version)
    if pre and not tag:
        print('Using "pre" requires a corresponding tag.')
        return
    if not dev and not pre:
        new_version = current_version.clear(pre=True, dev=True)
    if pre and dev:
        print("Pre and dev cannot be used together.")
        return
    elif dev:
        new_version = new_version.bump_dev()
    elif pre:
        new_version = new_version.bump_pre(tag=tag)
    if major:
        new_version = new_version.bump_release(0)
    elif minor:
        new_version = new_version.bump_release(1)
    elif micro:
        new_version = new_version.bump_release(2)
    if clear:
        new_version = new_version.clear(dev=True, pre=True, post=True)
    log('Updating version to %s' % new_version.normalize())
    version_file = get_version_file(ctx)
    file_contents = version_file.read_text()
    log('Found current version: %s' % _current_version)
    if dry_run:
        log('Would update to: %s' % new_version.normalize())
    else:
        log('Updating to: %s' % new_version.normalize())
        version_file.write_text(file_contents.replace(_current_version, str(new_version.normalize())))
        if commit:
            log('Committing...')
            ctx.run('git commit -s -m "Bumped version."')
