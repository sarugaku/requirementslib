# -*- coding=utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
import sys
from collections import namedtuple

import six
import vistir
from hypothesis import strategies as st
from packaging.markers import MARKER_OP, VARIABLE
from six.moves.urllib import parse as urllib_parse

from requirementslib.models.url import URI

parsed_url = namedtuple("ParsedUrl", "scheme netloc path params query fragment")
parsed_url.__new__.__defaults__ = ("", "", "", "", "", "")
relative_path = namedtuple("RelativePath", "leading_dots separator dest")
relative_path.__new__.__defaults__ = ("", "", "")
MarkerTuple = namedtuple("MarkerTuple", "variable op value")
MarkerTuple.__new__.__defaults__ = ("", "", "")
url_alphabet = "abcdefghijklmnopqrstuvwxyz1234567890-"
uri_schemes = ("http", "https", "ssh", "file", "sftp", "ftp")
vcs_schemes = (
    "git",
    "git+http",
    "git+https",
    "git+ssh",
    "git+git",
    "git+file",
    "hg",
    "hg+http",
    "hg+https",
    "hg+ssh",
    "hg+static-http",
    "svn",
    "svn+ssh",
    "svn+http",
    "svn+https",
    "svn+svn",
    "bzr",
    "bzr+http",
    "bzr+https",
    "bzr+ssh",
    "bzr+sftp",
    "bzr+ftp",
    "bzr+lp",
)


# from https://github.com/twisted/txacme/blob/master/src/txacme/test/strategies.py
def dns_labels():
    """
    Strategy for generating limited charset DNS labels.
    """
    # This is too limited, but whatever
    return st.text(
        "abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=25
    ).filter(
        lambda s: not any(
            [s.startswith("-"), s.endswith("-"), s.isdigit(), s[2:4] == "--"]
        )
    )


def valid_names():
    return st.text(url_alphabet, min_size=1, max_size=25).filter(
        lambda s: not any([s.startswith("-"), s.endswith("-")])
    )


def dns_names():
    """
    Strategy for generating limited charset DNS names.
    """
    return st.lists(dns_labels(), min_size=1, max_size=10).map(".".join)


def urls():
    """
    Strategy for generating urls.
    """
    return st.builds(
        URI,
        scheme=st.sampled_from(uri_schemes),
        host=dns_names(),
        port=st.integers(min_value=1, max_value=65535),
        path=st.lists(
            st.text(
                max_size=64,
                alphabet=st.characters(
                    blacklist_characters="/?#", blacklist_categories=("Cs",)
                ),
            ),
            min_size=1,
            max_size=10,
        )
        .map("".join)
        .map(vistir.misc.to_text)
        .map("".join),
        query=st.lists(
            st.text(
                max_size=10,
                alphabet=st.characters(
                    blacklist_characters="/?#", blacklist_categories=("Cs",)
                ),
            ),
            min_size=2,
            max_size=2,
        )
        .map("=".join)
        .map(vistir.misc.to_text),
        ref=st.text(max_size=64, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"),
        subdirectory=st.text(
            max_size=64, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"
        ),
        extras=st.lists(
            st.text(max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_"),
            min_size=0,
            max_size=10,
        ),
    )


def legal_path_chars():
    # Control characters
    blacklist = ["/"]
    if os.name == "nt":
        blacklist.extend(["<", ">", ":", '"', "\\", "|", "?", "*"])
    return (
        st.text(
            st.characters(
                blacklist_characters=blacklist,
                blacklist_categories=("Cs",),
                min_codepoint=32,
            ),
            min_size=0,
            max_size=64,
        )
        .filter(lambda s: not any(s.endswith(c) for c in [".", "/", "./", "/.", " "]))
        .filter(lambda s: not s.startswith("/"))
        .filter(lambda s: s not in ["", ".", "./", ".."])
    )


def relative_paths():
    relative_leaders = (".", "..")
    separators = [
        vistir.misc.to_text(sep)
        for sep in (os.sep, os.path.sep, os.path.altsep)
        if sep is not None
    ]
    return st.builds(
        relative_path,
        leading_dots=st.sampled_from(relative_leaders),
        separator=st.sampled_from(separators),
        dest=legal_path_chars(),
    )


def unparsed_urls():
    return st.builds(urllib_parse.urlunparse, urls())


def vcs_requirements():
    return st.builds(
        parsed_url,
        scheme=st.sampled_from(vcs_schemes),
        netloc=dns_names(),
        path=st.lists(
            st.text(max_size=64, alphabet=url_alphabet), min_size=1, max_size=10
        )
        .map(vistir.misc.to_text)
        .map("".join),
        fragment=valid_names(),
    )


def unparse_requirement(r):
    _r, paths, fragment = r[:-2], r[-2], r[-1]
    paths = "/".join(paths)
    fragment = "#egg={0}".format(fragment)
    url = _r + (paths, fragment)
    return urllib_parse.urlunparse(url)


def vcs_req():
    return st.builds(unparse_requirement, vcs_requirements())


sample_values = sorted(
    [
        "posix",
        "java",
        "nt",  # os.name
        "linux",
        "linux2",
        "darwin",
        "win32",
        "java1.8.0_51" "x86_64",  # sys.platform
        "i386",  # platform.machine
        "CPython",
        "Jython",
        "PyPy",  # platform.python_implementation
        "4.18.0-22-generic",
        "10",  # platform.release
        "Linux",
        "Windows",
        "Java",  # platform.system
        "#1 SMP Fri Apr 25 13:07:35 EDT 2014 Java HotSpot(TM) 64-Bit Server VM, 25.51-b03,"
        " Oracle Corporation Darwin Kernel Version 14.5.0: Wed Jul 29 "
        "02:18:53 PDT 2015; root:xnu-2782.40.9~2/RELEASE_X86_64",
        "#23-Ubuntu SMP Tue Jun 4 20:22:46 UTC 2019",  # platform.version
        "2.7",
        "3.5",
        "3.6",
        "3.7",
        "3.8",  # platform.python_version[:3]
        "2.7.16",
        "3.5.7",
        "3.6.8",
        "3.7.3",
        "3.8.0b1",  # platform.python_full_version or implementation_version
        "cpython",
        "pypy",
        "jython",  # sys.implementation.name
    ]
)


def random_marker_variables():
    variables = sorted(
        [str(v).strip('"') for v in list(VARIABLE) if str(v).strip('"') != "extra"]
    )
    return st.sampled_from(variables)


def random_marker_values():
    return st.sampled_from(sample_values)


def random_marker_ops():
    return st.sampled_from([str(m).strip('"') for m in list(MARKER_OP)])


def randomized_marker():
    return st.builds(
        MarkerTuple,
        variable=random_marker_variables(),
        op=random_marker_ops(),
        value=random_marker_values(),
    )


def randomized_markers():
    return st.lists(randomized_markers(), max_size=4).map(" and ".join)


@st.composite
def random_marker_str(
    draw,
    marker_vars=random_marker_variables(),
    ops=random_marker_ops(),
    values=random_marker_values(),
):
    marker_var = draw(marker_vars)
    op = draw(ops)
    if op in ("in", "not in"):
        value = ", ".join(draw(st.lists(values, min_size=2, max_size=4)))
    else:
        value = draw(values)
    return "{0} {1} '{2}'".format(marker_var, op, value)


repository_defaults = (None, None, None, "master", "git", "https", "github.com")
repository_fields = [
    "user",
    "repo",
    "pkg_name",
    "extras",
    "subdirectory",
    "ref",
    "vcs_type",
    "scheme",
    "base_url",
]
if sys.version_info[:2] >= (3, 0):
    Repository = namedtuple("Repository", repository_fields, defaults=repository_defaults)
else:
    Repository = namedtuple("Repository", repository_fields)
    Repository.__new__.__defaults__ = repository_defaults

available_repos = [
    Repository("sarugaku", "pythonfinder"),
    Repository("sarugaku", "pythonfinder", extras=["dev"]),
    Repository("sarugkau", "vistir", extras=["spinner"]),
    Repository("sarugkau", "vistir", ref="0.4.1"),
    Repository("sarugaku", "shellingham"),
    Repository("sarugaku", "shellingham", scheme="ssh"),
    Repository("kennethreitz", "requests"),
    Repository("kennethreitz", "requests", extras=["security"]),
    Repository("kennethreitz", "tablib"),
    Repository("benjaminp", "six"),
    Repository("sarugaku", "plette"),
    Repository("sarugaku", "plette", extras=["validation"]),
    Repository("sarugaku", "passa"),
    Repository("sarugaku", "passa", scheme="ssh"),
]


def random_repositories():
    return st.sampled_from(available_repos)


@st.composite
def repository_url(draw, elements=random_repositories()):
    repo = draw(elements)
    repo_dict = dict(repo._asdict())
    ref = repo_dict.pop("ref", None)
    extras = repo_dict.pop("extras", None)
    subdir = repo_dict.pop("subdirectory", None)
    pkg_name = repo_dict.pop("pkg_name", None)
    if pkg_name is None:
        pkg_name = repo_dict.get("repo")
    extras_str = ""
    ref_str = ""
    subdir_str = ""
    if ref:
        ref_str = "@{0}".format(ref)
    if extras and isinstance(extras, six.string_types):
        extras = [extras]
    if extras:
        extras_str = "[{0}]".format(",".join(extras))
    if subdir:
        subdir_str = "&subdirectory={0}".format(subdir)
    repo_dict.update(
        {"ref": ref_str, "extras": extras_str, "subdir": subdir_str, "pkg_name": pkg_name}
    )
    line = "{vcs_type}+{scheme}://{base_url}/{user}/{repo}.git{ref}#egg={pkg_name}{subdir}".format(
        **repo_dict
    )
    return line


@st.composite
def repository_line(draw, repositories=repository_url(), markers=random_marker_str()):
    prefix = draw(st.sampled_from(["-e ", ""]))
    marker_selection = draw(markers)
    marker_str = ""
    if marker_selection:
        marker_str = "; {0}".format(marker_selection)
    line = "{0}{1}{2}".format(prefix, draw(repositories), marker_str)
    return line
