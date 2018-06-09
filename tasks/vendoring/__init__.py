# -*- coding=utf-8 -*-
""""Vendoring script, python 3.5 needed"""
# Taken from pip
# see https://github.com/pypa/pip/blob/95bcf8c5f6394298035a7332c441868f3b0169f4/tasks/vendoring/__init__.py
from pathlib import Path
import tarfile
import zipfile
import os
import re
import shutil
import invoke
import requests

TASK_NAME = 'update'

LIBRARY_DIRNAMES = {
    'requirements-parser': 'requirements',
    'backports.shutil_get_terminal_size': 'backports/shutil_get_terminal_size',
    'backports.weakref': 'backports/weakref',
    'shutil_backports': 'backports/shutil_get_terminal_size',
    'python-dotenv': 'dotenv',
    'pip-tools': 'piptools',
    'setuptools': 'pkg_resources',
    'msgpack-python': 'msgpack',
    'attrs': 'attr',
}

# from time to time, remove the no longer needed ones
HARDCODED_LICENSE_URLS = {
}

FILE_WHITE_LIST = (
    'Makefile',
    'vendor.txt',
    'requirements.txt',
    '_vendor.txt',
    'patched.txt',
    '__init__.py',
    'README.rst',
    'README.md',
)

LIBRARY_RENAMES = {
    'pip': 'pipenv.patched.notpip'
}


def mkdir_p(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
        From: http://code.activestate.com/recipes/82465-a-friendly-mkdir/
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError(
            "a file with the same name as the desired dir, '{0}', already exists.".format(
                newdir
            )
        )

    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            mkdir_p(head)
        if tail:
            os.mkdir(newdir)


def drop_dir(path):
    if path.exists() and path.is_dir():
        shutil.rmtree(str(path))


def remove_all(paths):
    for path in paths:
        if path.is_dir():
            drop_dir(path)
        else:
            path.unlink()


def log(msg):
    print('[vendoring.%s] %s' % (TASK_NAME, msg))


def _get_git_root(ctx):
    return Path(ctx.run('git rev-parse --show-toplevel', hide=True).stdout.strip())


def _get_vendor_dir(ctx):
    return _get_git_root(ctx) / 'src' / 'requirementslib' / '_vendor'


def _find_requirements_file(ctx, vendor_dir):
    options = ['{0}.txt'.format(vendor_dir.name), 'requirements.txt', 'vendor.txt', 'patched.txt']
    return next((r for r in options if (vendor_dir / r).exists()), None)


def clean_vendor(ctx, vendor_dir):
    # Old _vendor cleanup
    remove_all(vendor_dir.glob('*.pyc'))
    log('Cleaning %s' % vendor_dir)
    for item in vendor_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(str(item))
        elif "LICENSE" in item.name or "COPYING" in item.name:
            continue
        elif item.name not in FILE_WHITE_LIST:
            item.unlink()
        else:
            log('Skipping %s' % item)


def detect_vendored_libs(vendor_dir):
    retval = []
    for item in vendor_dir.iterdir():
        if item.is_dir():
            retval.append(item.name)
        elif "LICENSE" in item.name or "COPYING" in item.name:
            continue
        elif item.name.endswith(".pyi"):
            continue
        elif item.name not in FILE_WHITE_LIST:
            retval.append(item.name[:-3])
    return retval


def rewrite_imports(package_dir, vendored_libs, vendor_dir):
    for item in package_dir.iterdir():
        if item.is_dir():
            rewrite_imports(item, vendored_libs, vendor_dir)
        elif item.name.endswith('.py'):
            rewrite_file_imports(item, vendored_libs, vendor_dir)


def rewrite_file_imports(item, vendored_libs, vendor_dir):
    """Rewrite 'import xxx' and 'from xxx import' for vendored_libs"""
    text = item.read_text(encoding='utf-8')
    renames = LIBRARY_RENAMES
    for k in LIBRARY_RENAMES.keys():
        if k not in vendored_libs:
            vendored_libs.append(k)
    for lib in vendored_libs:
        to_lib = lib
        if lib in renames:
            to_lib = renames[lib]
        text = re.sub(
            r'([\n\s]*)import %s([\n\s\.]+)' % lib,
            r'\1import %s\2' % to_lib,
            text,
        )
        text = re.sub(
            r'([\n\s]*)from %s([\s\.])+' % lib,
            r'\1from %s\2' % to_lib,
            text,
        )
        text = re.sub(
            r"(\n\s*)__import__\('%s([\s'\.])+" % lib,
            r"\1__import__('%s\2" % to_lib,
            text,
        )
    item.write_text(text, encoding='utf-8')


def apply_patch(ctx, patch_file_path):
    log('Applying patch %s' % patch_file_path.name)
    ctx.run('git apply --ignore-whitespace --verbose %s' % patch_file_path)


def rename_if_needed(ctx, vendor_dir, item):
    new_path = None
    if item.name in LIBRARY_RENAMES or item.name in LIBRARY_DIRNAMES:
        new_name = LIBRARY_RENAMES.get(item.name, LIBRARY_DIRNAMES.get(item.name))
        new_path = item.parent / new_name
        log('Renaming %s => %s' % (item.name, new_path))
        # handle existing directories
        try:
            item.rename(str(new_path))
        except OSError:
            for child in item.iterdir():
                child.rename(str(new_path / child.name))


def write_backport_imports(ctx, vendor_dir):
    backport_dir = vendor_dir / 'backports'
    if not backport_dir.exists():
        return
    backport_init = backport_dir / '__init__.py'
    backport_libs = detect_vendored_libs(backport_dir)
    init_py_lines = backport_init.read_text().splitlines()
    for lib in backport_libs:
        lib_line = 'from . import {0}'.format(lib)
        if lib_line not in init_py_lines:
            log('Adding backport %s to __init__.py exports' % lib)
            init_py_lines.append(lib_line)
    backport_init.write_text('\n'.join(init_py_lines) + '\n')


def vendor(ctx, vendor_dir, rewrite=True):
    log('Reinstalling vendored libraries')
    options = ['{0}.txt'.format(vendor_dir.name), 'requirements.txt', 'vendor.txt', 'patched.txt']
    requirements_file = next((r for r in options if (vendor_dir / r).exists()), None)
    if not requirements_file:
        raise FileNotFoundError("No vendor file found!")
    # We use --no-deps because we want to ensure that all of our dependencies
    # are added to vendor.txt, this includes all dependencies recursively up
    # the chain.
    ctx.run(
        'pip install -t {0} -r {0}/{1} --no-compile --no-deps'.format(
            str(vendor_dir),
            requirements_file,
        )
    )
    remove_all(vendor_dir.glob('*.dist-info'))
    remove_all(vendor_dir.glob('*.egg-info'))

    # Cleanup setuptools unneeded parts
    drop_dir(vendor_dir / 'bin')
    drop_dir(vendor_dir / 'tests')

    # Detect the vendored packages/modules
    vendored_libs = detect_vendored_libs(_get_vendor_dir(ctx))
    log("Detected vendored libraries: %s" % ", ".join(vendored_libs))

    # Apply pre-patches
    log("Applying pre-patches...")
    patch_dir = Path(__file__).parent / 'patches' / vendor_dir.name

    # Global import rewrites
    log('Renaming specified libs...')
    for item in vendor_dir.iterdir():
        if item.is_dir():
            if rewrite:
                log('Rewriting imports for %s...' % item)
                rewrite_imports(item, vendored_libs, vendor_dir)
            rename_if_needed(ctx, vendor_dir, item)
        elif item.name not in FILE_WHITE_LIST:
            if rewrite:
                rewrite_file_imports(item, vendored_libs, vendor_dir)
    write_backport_imports(ctx, vendor_dir)
    log('Applying post-patches...')
    patches = patch_dir.glob('*.patch')
    for patch in patches:
        apply_patch(ctx, patch)


@invoke.task
def rewrite_all_imports(ctx):
    vendor_dir = _get_vendor_dir(ctx)
    log('Using vendor dir: %s' % vendor_dir)
    vendored_libs = detect_vendored_libs(vendor_dir)
    log("Detected vendored libraries: %s" % ", ".join(vendored_libs))
    log("Rewriting all imports related to vendored libs")
    for item in vendor_dir.iterdir():
        if item.is_dir():
            rewrite_imports(item, vendored_libs)
        elif item.name not in FILE_WHITE_LIST:
            rewrite_file_imports(item, vendored_libs)


@invoke.task
def download_licenses(ctx, vendor_dir, requirements_file='vendor.txt'):
    log('Downloading licenses')
    if not vendor_dir:
        vendor_dir = _get_vendor_dir(ctx)
    requirements_file = _find_requirements_file(ctx, vendor_dir)
    tmp_dir = vendor_dir / '__tmp__'
    ctx.run(
        'pip download -r {0}/{1} --no-binary :all: --no-deps -d {2}'.format(
            str(vendor_dir),
            requirements_file,
            str(tmp_dir),
        )
    )
    for sdist in tmp_dir.iterdir():
        extract_license(vendor_dir, sdist)
    drop_dir(tmp_dir)


def extract_license(vendor_dir, sdist):
    if sdist.stem.endswith('.tar'):
        ext = sdist.suffix[1:]
        with tarfile.open(sdist, mode='r:{}'.format(ext)) as tar:
            found = find_and_extract_license(vendor_dir, tar, tar.getmembers())
    elif sdist.suffix == '.zip':
        with zipfile.ZipFile(sdist) as zip:
            found = find_and_extract_license(vendor_dir, zip, zip.infolist())
    else:
        raise NotImplementedError('new sdist type!')

    if not found:
        log('License not found in {}, will download'.format(sdist.name))
        license_fallback(vendor_dir, sdist.name)


def find_and_extract_license(vendor_dir, tar, members):
    found = False
    for member in members:
        try:
            name = member.name
        except AttributeError:  # zipfile
            name = member.filename
        if 'LICENSE' in name or 'COPYING' in name:
            if '/test' in name:
                # some testing licenses in hml5lib and distlib
                log('Ignoring {}'.format(name))
                continue
            found = True
            extract_license_member(vendor_dir, tar, member, name)
    return found


def license_fallback(vendor_dir, sdist_name):
    """Hardcoded license URLs. Check when updating if those are still needed"""
    libname = libname_from_dir(sdist_name)
    if libname not in HARDCODED_LICENSE_URLS:
        raise ValueError('No hardcoded URL for {} license'.format(libname))

    url = HARDCODED_LICENSE_URLS[libname]
    _, _, name = url.rpartition('/')
    dest = license_destination(vendor_dir, libname, name)
    r = requests.get(url, allow_redirects=True)
    log('Downloading {}'.format(url))
    r.raise_for_status()
    dest.write_bytes(r.content)


def libname_from_dir(dirname):
    """Reconstruct the library name without it's version"""
    parts = []
    for part in dirname.split('-'):
        if part[0].isdigit():
            break
        parts.append(part)
    return '-'.join(parts)


def license_destination(vendor_dir, libname, filename):
    """Given the (reconstructed) library name, find appropriate destination"""
    normal = vendor_dir / libname
    if normal.is_dir():
        return normal / filename
    lowercase = vendor_dir / libname.lower()
    if lowercase.is_dir():
        return lowercase / filename
    # Short circuit all logic if we are renaming the whole library
    if libname in LIBRARY_RENAMES:
        return vendor_dir / LIBRARY_RENAMES[libname] / filename
    if libname in LIBRARY_DIRNAMES:
        override = vendor_dir / LIBRARY_DIRNAMES[libname]
        if not override.exists() and override.parent.exists():
            # for flattened subdeps, specifically backports/weakref.py
            return (
                vendor_dir / override.parent
            ) / '{0}.{1}'.format(override.name, filename)
        return vendor_dir / LIBRARY_DIRNAMES[libname] / filename
    # fallback to libname.LICENSE (used for nondirs)
    return vendor_dir / '{}.{}'.format(libname, filename)


def extract_license_member(vendor_dir, tar, member, name):
    mpath = Path(name)  # relative path inside the sdist
    dirname = list(mpath.parents)[-2].name  # -1 is .
    libname = libname_from_dir(dirname)
    dest = license_destination(vendor_dir, libname, mpath.name)
    log('Extracting {} into {}'.format(name, dest))
    try:
        fileobj = tar.extractfile(member)
        dest.write_bytes(fileobj.read())
    except AttributeError:  # zipfile
        dest.write_bytes(tar.read(member))


@invoke.task()
def generate_patch(ctx, package_path, patch_description, base='HEAD'):
    vendor_dir = _get_vendor_dir(ctx)
    pkg = vendor_dir / package_path
    if not pkg.exists():
        raise ValueError('example usage: generate-patch pew some-description')
    if patch_description:
        patch_fn = '{0}-{1}.patch'.format(pkg.parts[1], patch_description)
    else:
        patch_fn = '{0}.patch'.format(pkg.parts[1])
    command = 'git diff {base} -p {root} > {out}'.format(
        base=base,
        root=Path('src').joinpath('requirementslib', '_vendor').as_posix(),
        out=Path(__file__).parent.joinpath('patches', patch_fn).as_posix(),
    )
    with ctx.cd(str(_get_git_root(ctx))):
        log(command)
        ctx.run(command)


@invoke.task(name=TASK_NAME)
def main(ctx):
    vendor_dir = _get_vendor_dir(ctx)
    log('Using vendor dir: %s' % vendor_dir)
    clean_vendor(ctx, vendor_dir)
    vendor(ctx, vendor_dir)
    download_licenses(ctx, vendor_dir)
    log('Revendoring complete')
