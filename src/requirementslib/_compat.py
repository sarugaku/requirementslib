# -*- coding=utf-8 -*-
import functools
import importlib
import io
import os
import six
import sys
import warnings
from first import first
from shutil import rmtree
from tempfile import _bin_openflags, gettempdir, _mkstemp_inner, mkdtemp

try:
    from tempfile import _infer_return_type
except ImportError:

    def _infer_return_type(*args):
        _types = set()
        for arg in args:
            if isinstance(type(arg), six.string_types):
                _types.add(str)
            elif isinstance(type(arg), bytes):
                _types.add(bytes)
            elif arg:
                _types.add(type(arg))
        return _types.pop()

try:
    from weakref import finalize
except ImportError:
    from backports.weakref import finalize

has_modutil = False
if sys.version_info[:2] >= (3, 7):
    try:
        import modutil
    except ImportError:
        has_modutil = False
    else:
        has_modutil = True

if sys.version_info[:2] >= (3, 5):
    try:
        from pathlib import Path
    except ImportError:
        from pathlib2 import Path
else:
    from pathlib2 import Path

# Use these imports as compatibility imports
if six.PY3:
    class FileNotFoundError(FileNotFoundError):
        pass

else:
    class FileNotFoundError(IOError):
        pass

    class ResourceWarning(Warning):
        pass

try:
    from urllib.parse import urlparse, unquote
except ImportError:
    from urlparse import urlparse, unquote


def get_package(module, subimport=None):
    package = None
    if subimport:
        package = subimport
    else:
        module, _, package = module.rpartition(".")
    return module, package


def do_import(module_path, subimport=None, old_path=None):
    old_path = old_path or module_path
    internal = "pip._internal.{0}".format(module_path)
    pip9 = "pip.{0}".format(old_path)
    imported = None
    if has_modutil:
        to_import, package = get_package(internal, subimport)
        mod, imp_getattr = modutil.lazy_import(__name__, {to_import,})
        old_import, package = get_package(pip9, subimport)
        mod, old_getattr = modutil.lazy_import(__name__, {old_import,})
        chained = modutil.chained___getattr__(__name__, imp_getattr, old_getattr,)
        _, _, module_name = to_import.rpartition(".")
        try:
            imported = chained(module_name)
        except modutil.ModuleAttributeError:
            _, _, module_name = old_import.rpartition(".")
            imported = chained(module_name)
        return getattr(imported, package)
    to_import, package = get_package(internal, subimport)
    try:
        imported = importlib.import_module(to_import)
    except ImportError:
        to_import, package = get_package(pip9, subimport)
        imported = importlib.import_module(to_import)
    return getattr(imported, package)


InstallRequirement = do_import("req.req_install", "InstallRequirement")
USER_CACHE_DIR = do_import("locations", "USER_CACHE_DIR")
FAVORITE_HASH = do_import("utils.hashes", "FAVORITE_HASH")
is_file_url = do_import("download", "is_file_url")
url_to_path = do_import("download", "url_to_path")
path_to_url = do_import("download", "path_to_url")
is_archive_file = do_import("download", "is_archive_file")
_strip_extras = do_import("req.req_install", "_strip_extras")
Link = do_import("index", "Link")
Wheel = do_import("wheel", "Wheel")
is_installable_dir = do_import("utils.misc", "is_installable_dir", old_path="utils")
make_abstract_dist = do_import(
    "operations.prepare", "make_abstract_dist", old_path="req.req_set"
)
VcsSupport = do_import("vcs", "VcsSupport")
RequirementPreparer = do_import("operations.prepare", "RequirementPreparer")
Resolver = do_import("resolve", "Resolver")
RequirementSet = do_import("req.req_set", "RequirementSet")
PackageFinder = do_import("index", "PackageFinder")
WheelCache = do_import("cache", "WheelCache")
Command = do_import("basecommand", "Command")
cmdoptions = do_import("cmdoptions")


class TemporaryDirectory(object):
    """Create and return a temporary directory.  This has the same
    behavior as mkdtemp but can be used as a context manager.  For
    example:

        with TemporaryDirectory() as tmpdir:
            ...

    Upon exiting the context, the directory and everything contained
    in it are removed.
    """

    def __init__(self, suffix=None, prefix=None, dir=None):
        self.name = mkdtemp(suffix, prefix, dir)
        self._finalizer = finalize(
            self,
            self._cleanup,
            self.name,
            warn_message="Implicitly cleaning up {!r}".format(self),
        )

    @classmethod
    def _cleanup(cls, name, warn_message):
        rmtree(name)
        warnings.warn(warn_message, ResourceWarning)

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self._finalizer.detach():
            rmtree(self.name)


def _sanitize_params(prefix, suffix, dir):
    """Common parameter processing for most APIs in this module."""
    output_type = _infer_return_type(prefix, suffix, dir)
    if suffix is None:
        suffix = output_type()
    if prefix is None:
        if output_type is str:
            prefix = "tmp"
        else:
            prefix = os.fsencode("tmp")
    if dir is None:
        if output_type is str:
            dir = gettempdir()
        else:
            dir = os.fsencode(gettempdir())
    return prefix, suffix, dir, output_type


class _TemporaryFileCloser:
    """A separate object allowing proper closing of a temporary file's
    underlying file object, without adding a __del__ method to the
    temporary file."""

    file = None  # Set here since __del__ checks it
    close_called = False

    def __init__(self, file, name, delete=True):
        self.file = file
        self.name = name
        self.delete = delete

    # NT provides delete-on-close as a primitive, so we don't need
    # the wrapper to do anything special.  We still use it so that
    # file.name is useful (i.e. not "(fdopen)") with NamedTemporaryFile.
    if os.name != "nt":

        # Cache the unlinker so we don't get spurious errors at
        # shutdown when the module-level "os" is None'd out.  Note
        # that this must be referenced as self.unlink, because the
        # name TemporaryFileWrapper may also get None'd out before
        # __del__ is called.

        def close(self, unlink=os.unlink):
            if not self.close_called and self.file is not None:
                self.close_called = True
                try:
                    self.file.close()
                finally:
                    if self.delete:
                        unlink(self.name)

        # Need to ensure the file is deleted on __del__
        def __del__(self):
            self.close()

    else:
        def close(self):
            if not self.close_called:
                self.close_called = True
                self.file.close()


class _TemporaryFileWrapper:
    """Temporary file wrapper
    This class provides a wrapper around files opened for
    temporary use.  In particular, it seeks to automatically
    remove the file when it is no longer needed.
    """

    def __init__(self, file, name, delete=True):
        self.file = file
        self.name = name
        self.delete = delete
        self._closer = _TemporaryFileCloser(file, name, delete)

    def __getattr__(self, name):
        # Attribute lookups are delegated to the underlying file
        # and cached for non-numeric results
        # (i.e. methods are cached, closed and friends are not)
        file = self.__dict__["file"]
        a = getattr(file, name)
        if hasattr(a, "__call__"):
            func = a

            @functools.wraps(func)
            def func_wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            # Avoid closing the file as long as the wrapper is alive,
            # see issue #18879.
            func_wrapper._closer = self._closer
            a = func_wrapper
        if not isinstance(a, int):
            setattr(self, name, a)
        return a

    # The underlying __enter__ method returns the wrong object
    # (self.file) so override it to return the wrapper

    def __enter__(self):
        self.file.__enter__()
        return self

    # Need to trap __exit__ as well to ensure the file gets
    # deleted when used in a with statement

    def __exit__(self, exc, value, tb):
        result = self.file.__exit__(exc, value, tb)
        self.close()
        return result

    def close(self):
        """
        Close the temporary file, possibly deleting it.
        """
        self._closer.close()

    # iter() doesn't use __getattr__ to find the __iter__ method

    def __iter__(self):
        # Don't return iter(self.file), but yield from it to avoid closing
        # file as long as it's being used as iterator (see issue #23700).  We
        # can't use 'yield from' here because iter(file) returns the file
        # object itself, which has a close method, and thus the file would get
        # closed when the generator is finalized, due to PEP380 semantics.
        for line in self.file:
            yield line


def NamedTemporaryFile(
    mode="w+b",
    buffering=-1,
    encoding=None,
    newline=None,
    suffix=None,
    prefix=None,
    dir=None,
    delete=True,
):
    """Create and return a temporary file.
    Arguments:
    'prefix', 'suffix', 'dir' -- as for mkstemp.
    'mode' -- the mode argument to io.open (default "w+b").
    'buffering' -- the buffer size argument to io.open (default -1).
    'encoding' -- the encoding argument to io.open (default None)
    'newline' -- the newline argument to io.open (default None)
    'delete' -- whether the file is deleted on close (default True).
    The file is created as mkstemp() would do it.
    Returns an object with a file-like interface; the name of the file
    is accessible as its 'name' attribute.  The file will be automatically
    deleted when it is closed unless the 'delete' argument is set to False.
    """
    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)
    flags = _bin_openflags
    # Setting O_TEMPORARY in the flags causes the OS to delete
    # the file when it is closed.  This is only supported by Windows.
    if os.name == "nt" and delete:
        flags |= os.O_TEMPORARY
    if sys.version_info < (3, 5):
        (fd, name) = _mkstemp_inner(dir, prefix, suffix, flags)
    else:
        (fd, name) = _mkstemp_inner(dir, prefix, suffix, flags, output_type)
    try:
        file = io.open(
            fd, mode, buffering=buffering, newline=newline, encoding=encoding
        )
        return _TemporaryFileWrapper(file, name, delete)

    except BaseException:
        os.unlink(name)
        os.close(fd)
        raise
