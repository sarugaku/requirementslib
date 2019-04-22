# -*- coding=utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
from collections import namedtuple

import vistir
from hypothesis import strategies as st
from six.moves.urllib import parse as urllib_parse

from requirementslib.models.url import URI

parsed_url = namedtuple("ParsedUrl", "scheme netloc path params query fragment")
parsed_url.__new__.__defaults__ = ("", "", "", "", "", "")
relative_path = namedtuple("RelativePath", "leading_dots separator dest")
relative_path.__new__.__defaults__ = ("", "", "")
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
