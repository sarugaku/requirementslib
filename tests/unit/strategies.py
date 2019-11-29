# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import os
import re
import string
import sys
from collections import namedtuple

import six
import vistir
from hypothesis import assume, strategies as st
from hypothesis.provisional import URL_SAFE_CHARACTERS, domains, urls as url_strategy
from packaging.markers import MARKER_OP, VARIABLE
from packaging.specifiers import Specifier
from packaging.version import parse as parse_version
from pyparsing import Literal, MatchFirst, ParseExpression, ParserElement
from six.moves.urllib import parse as urllib_parse

from requirementslib.models.url import URI

parsed_url = namedtuple("ParsedUrl", "scheme netloc path params query fragment")
parsed_url.__new__.__defaults__ = ("", "", "", "", "", "")
relative_path = namedtuple("RelativePath", "leading_dots separator dest")
relative_path.__new__.__defaults__ = ("", "", "")
MarkerTuple = namedtuple("MarkerTuple", "variable op value")
MarkerTuple.__new__.__defaults__ = ("", "", "")
NormalRequirement = namedtuple(
    "NormalRequirement",
    "name specifier version extras markers hashes line line_without_markers as_list list_without_markers",
)
NormalRequirement.__new__.__defaults__ = (
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
)
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


def flatten_pyparsing_exprs(expr):
    exprs = set()
    for child in expr.exprs:
        if isinstance(child, (Literal, six.string_types)):
            exprs.add(str(child).strip('"'))
        elif isinstance(child, (MatchFirst, ParseExpression, ParserElement)):
            exprs.update(flatten_pyparsing_exprs(child))
    return exprs


def valid_names():
    return st.text(url_alphabet, min_size=1, max_size=25).filter(
        lambda s: not any([s.startswith("-"), s.endswith("-")])
    )


def urls():
    """
    Strategy for generating urls.
    """

    def url_encode(s):
        return "".join(c if c in URL_SAFE_CHARACTERS else "%%%02X" % ord(c) for c in s)

    return st.builds(
        URI,
        scheme=st.sampled_from(uri_schemes),
        host=domains(),
        port=st.integers(min_value=1, max_value=65535),
        path=st.lists(st.text(string.printable).map(url_encode)).map("/".join),
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
            st.text(max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-."),
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
    def url_encode(s):
        return "".join(c if c in URL_SAFE_CHARACTERS else "%%%02X" % ord(c) for c in s)

    return st.builds(
        parsed_url,
        scheme=st.sampled_from(vcs_schemes),
        netloc=domains(),
        path=st.lists(st.text(string.printable).map(url_encode)).map("/".join),
        fragment=valid_names(),
    )


def auth_list():
    return st.lists(st.text(string.printable), min_size=0, max_size=2)


@st.composite
def auth_strings(draw, auth=auth_list()):
    def url_encode(s):
        if not s:
            return ""
        chars = []
        for c in s:
            if not c:
                continue
            elif c in URL_SAFE_CHARACTERS:
                chars.append(c)
            else:
                chars.append("%%%02X" % ord(c))
        return "".join(chars)

    auth_section = draw(auth)
    if auth_section and len(auth_section) == 2:
        user, password = auth_section
        if user and password:
            result = "{0}:{1}".format(
                "".join([url_encode(s) for s in user]),
                "".join([url_encode(s) for s in password]),
            )
        elif user and not password:
            result = "".join([url_encode(s) for s in user])
        elif password and not user:
            result = "".join([url_encode(s) for s in password])
        else:
            result = ""
    elif auth_section and len(auth_section) == 1:
        result = "{0}".format("".join([url_encode(s) for s in auth_section]))
    else:
        result = ""
    return result


@st.composite
def auth_url(draw, auth_string=auth_strings()):
    # taken from the hypothesis provisional url generation strategy
    def url_encode(s):
        return "".join(c if c in URL_SAFE_CHARACTERS else "%%%02X" % ord(c) for c in s)

    path = draw(
        st.lists(
            st.text(string.printable).map(url_encode).filter(lambda x: x not in ["", "."])
        ).map("/".join)
    )
    port = draw(st.integers(min_value=0, max_value=65535))
    port_str = ""
    if port and int(port) != 0:
        port_str = ":{0!s}".format(port)
    auth = draw(auth_string)
    if auth:
        auth = "{0}@".format(auth)
    if auth == ":@":
        auth = ""
    # none of the python url parsers can handle auth strings ending with "/"
    # assume(not any(auth.startswith(c) for c in ["/", ":", "@"]))
    assume(not any(auth.endswith(c) for c in [":", ":@"]))
    # assume(not all(["#" in auth, ":" not in auth]))
    domain = draw(domains().map(lambda x: x.lower()).filter(lambda x: x != ""))
    scheme = draw(st.sampled_from(uri_schemes))
    scheme_sep = "://" if not scheme.startswith("file") else ":///"
    return "{}{}{}{}{}/{}".format(scheme, scheme_sep, auth, domain, port_str, path)


def repo_url_strategy():
    def url_encode(s):
        return "".join(c if c in URL_SAFE_CHARACTERS else "%%%02X" % ord(c) for c in s)

    paths = st.lists(st.text(string.printable).map(url_encode)).map("/".join)
    ports = st.integers(min_value=0, max_value=65535).map(":{}".format)
    fragments = (
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-.")
        .map(url_encode)
        .map("#egg={}".format)
        .map(lambda x: "" if x == "#egg=" else x)
    )
    refs = (
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-")
        .map(url_encode)
        .map("@{}".format)
        .map(lambda x: "" if x == "@" else x)
    )
    scheme = (
        st.sampled_from(vcs_schemes)
        .filter(lambda x: "+" in x)
        .map("{}://".format)
        .map(lambda x: x.replace("file://", "file:///"))
    )
    auth = (
        auth_string()
        .map("{}@".format)
        .map(lambda x: "" if x == "@" else x)
        .map(lambda x: x.replace(":@", "@") if x.endswith(":@") else x)
    )
    domain = domains().map(lambda x: x.lower())
    return st.builds(
        "{}{}{}{}{}{}{}".format,
        scheme,
        auth,
        domain,
        st.just("|") | ports,
        paths,
        refs,
        fragments,
    ).map(lambda x: x.replace("|", ":") if "git+git@" in x else x.replace("|", "/"))


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
    variables = sorted([v for v in flatten_pyparsing_exprs(VARIABLE) if v != "extra"])
    return st.sampled_from(variables)


def random_marker_values():
    return st.sampled_from(sample_values)


def random_marker_ops():
    return st.sampled_from(sorted(flatten_pyparsing_exprs(MARKER_OP)))


def marker_tuple_val_lists():
    return st.builds(
        MarkerTuple,
        variable=random_marker_variables(),
        op=st.sampled_from(["in", "not in"]),
        value=st.lists(random_marker_values(), min_size=2, max_size=4)
        .map(", ".join)
        .map("'{0}'".format),
    ).map(" ".join)


def marker_tuple():
    return st.builds(
        MarkerTuple,
        variable=random_marker_variables(),
        op=random_marker_ops().filter(lambda x: x not in ("in", "not in")),
        value=random_marker_values().map("'{0}'".format),
    ).map(" ".join)


@st.composite
def random_op_val_pair(draw, ops=random_marker_ops(), vals=random_marker_values()):
    op = draw(ops)
    if op in ("in", "not in"):
        val = draw(
            st.lists(vals, min_size=2, max_size=4).map(", ".join).map("'{0}'".format)
        )
    else:
        val = draw(vals)
    return "{0} {1}".format(op, val)


def random_marker_strings():
    return st.lists(
        marker_tuple() | marker_tuple_val_lists(), min_size=0, max_size=3
    ).map(" and ".join)


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
if sys.version_info[:2] >= (3, 7):
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
    scheme = draw(
        st.sampled_from(vcs_schemes)
        .filter(lambda s: "+" in s)
        .filter(lambda s: "file" not in s)
    )
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
    if scheme == "git+git":
        repo_dict["scheme"] = "{0}@".format(scheme)
        repo_dict["pathsep"] = ":"
    else:
        repo_dict["scheme"] = "{0}://".format(scheme)
        repo_dict["pathsep"] = "/"
    repo_dict.update(
        {"ref": ref_str, "extras": extras_str, "subdir": subdir_str, "pkg_name": pkg_name}
    )
    line = "{scheme}{base_url}{pathsep}{user}/{repo}.git{ref}#egg={pkg_name}{subdir}".format(
        **repo_dict
    )
    return line


@st.composite
def repository_line(draw, repositories=repository_url(), markers=random_marker_strings()):
    prefix = draw(st.sampled_from(["-e ", ""]))
    marker_selection = draw(markers)
    marker_str = ""
    if marker_selection:
        marker_str = "; {0}".format(marker_selection)
    if prefix:
        line = ""
    line = "{0}{1}{2}".format(prefix, draw(repositories), marker_str)
    return line


known_requirements = (
    (
        "six",
        ["1.11.0", "1.12.0"],
        None,
        [
            [
                "1.12.0",
                [
                    "sha256:3350809f0555b11f552448330d0b52d5f24c91a322ea4a15ef22629740f3761c",
                    "sha256:d16a0141ec1a18405cd4ce8b4613101da75da0e9a7aec5bdd4fa804d0e0eba73",
                ],
            ]
        ],
    ),
    ("vistir", ["0.4.1", "0.4.2"], ["spinner"], None),
    ("requests", ["2.14", "2.18.4", "2.22.0", "2.21.1"], ["security", "socks"], None),
    ("plette", [], ["validation"], None),
    ("django", ["1.10", "1.11"], None, None),
)


def random_requirements():
    return st.sampled_from(known_requirements)


def make_version_key(value):
    if value is None:
        return -1
    return parse_version(value)


@st.composite
def requirements(
    draw, requirement_selection=random_requirements(), markers=random_marker_strings()
):
    req = draw(requirement_selection)
    marker_selection = draw(markers)
    name, versions, extras, hashes = req
    line = "{0}".format(name)
    if extras is not None:
        extras_choice = draw(st.one_of(st.lists(st.sampled_from(extras)), st.none()))
    else:
        extras_choice = None
    if versions is not None:
        version_choice = draw(st.one_of(st.sampled_from(versions), st.none()))
    else:
        version_choice = None
    hashes_option = None
    if hashes:
        hashes_option = next(iter(h for v, h in hashes if v == version_choice), [])
    spec_op = ""
    extras_list = sorted(set(extras_choice)) if extras_choice is not None else []
    extras_str = "[{0}]".format(",".join(extras_list)) if extras_list else ""
    if not version_choice:
        version_str = ""
    else:
        spec_op = draw(st.sampled_from(list(Specifier._operators.keys())))
        version_str = "{0}{1}".format(spec_op, version_choice)
    line = line_without_markers = "{0}{1}{2}".format(
        line.strip(), extras_str.strip(), version_str.strip()
    )
    as_list = ["{0}".format(line)]
    list_without_markers = as_list[:]
    marker_str = ""
    if marker_selection:
        marker_str = "; {0}".format(marker_selection)
        line = "{0}{1}".format(line, marker_str)
        as_list = ["{0}".format(line)]
    if hashes_option:
        hashes_list = sorted(set(hashes_option))
        hashes_line = " ".join(["--hash={0}".format(h) for h in hashes_list])
        line = "{0} {1}".format(line, hashes_line)
        line_without_markers = "{0} {1}".format(line_without_markers, hashes_line)
        as_list.extend(hashes_list)
        list_without_markers.extend(hashes_list)
    else:
        hashes_list = None
    return NormalRequirement(
        name=name,
        specifier=spec_op,
        version=version_choice,
        extras=extras_list,
        markers=marker_selection,
        hashes=hashes_list,
        line=line,
        line_without_markers=line_without_markers,
        as_list=as_list,
        list_without_markers=list_without_markers,
    )


url_regex = re.compile(
    (
        "^"
        # protocol identifier (optional)
        # short syntax // still required
        "(?:(?:(?:https?|ftp):)?\\/\\/)"
        # user:pass BasicAuth (optional)
        "(?:\\S+(?::\\S*)?@)?"
        "(?:"
        # IP address exclusion
        # private & local networks
        "(?!(?:10|127)(?:\\.\\d{1,3}){3})"
        "(?!(?:169\\.254|192\\.168)(?:\\.\\d{1,3}){2})"
        "(?!172\\.(?:1[6-9]|2\\d|3[0-1])(?:\\.\\d{1,3}){2})"
        # IP address dotted notation octets
        # excludes loopback network 0.0.0.0
        # excludes reserved space >= 224.0.0.0
        # excludes network & broadcast addresses
        # (first & last IP address of each class)
        "(?:[1-9]\\d?|1\\d\\d|2[01]\\d|22[0-3])"
        "(?:\\.(?:1?\\d{1,2}|2[0-4]\\d|25[0-5])){2}"
        "(?:\\.(?:[1-9]\\d?|1\\d\\d|2[0-4]\\d|25[0-4]))"
        "|"
        # host & domain names, may end with dot
        # can be replaced by a shortest alternative
        # (?![-_])(?:[-\\w\\u00a1-\\uffff]{0,63}[^-_]\\.)+
        "(?:"
        "(?:"
        "[a-z0-9\\u00a1-\\uffff]"
        "[a-z0-9\\u00a1-\\uffff_-]{0,62}"
        ")?" + "[a-z0-9\\u00a1-\\uffff]\\."
        ")+" +
        # TLD identifier name, may end with dot
        "(?:[a-z\\u00a1-\\uffff]{2,}\\.?)"
        ")"
        # port number (optional)
        "(?::\\d{2,5})?"
        # resource path (optional)
        "(?:[/?#]\\S*)?"
        "$"
    )
)
