# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import os

from hypothesis import assume, given, strategies as st
from six.moves.urllib_parse import quote_plus, unquote_plus, urlsplit, urlunsplit
from vistir.compat import Path

from requirementslib.models.url import URI

from .strategies import auth_url_strategy, repository_url, url_regex


@given(auth_url_strategy())
def test_uri(authurl):
    auth = "{}".format(authurl.auth) if authurl.auth != ":" else ""
    port = ":{}".format(authurl.port) if authurl.port != 0 else ""
    path = "" if not authurl.path else "/{}".format(authurl.path)
    url = "{}{}{}{}{}".format(authurl.scheme, auth, authurl.domain, port, path)
    parsed_url = URI.parse(url)
    # result = urlsplit(url)
    # new_path = ""
    # if result.path:
    #     new_path = Path(result.path).resolve().as_posix()
    #     if os.name == "nt":
    #         # because windows will put a drive here even if it was
    #         # just an empty string
    #         new_path = new_path[2:]
    # rewritten_url = urlunsplit(result._replace(path=new_path))
    # assume(result.scheme and result.netloc)
    assume(authurl.scheme and authurl.domain)
    # assert parsed_url.base_url == rewritten_url, "{} {} {}".format(
    #     result.path, new_path, Path(result.path).as_posix()
    # )
    assert parsed_url.base_url == url, "{} {} {!s}".format(
        parsed_url.base_url, url, authurl
    )
    if parsed_url.username or parsed_url.password:
        assert "----" in parsed_url.safe_string
        assert "****" in parsed_url.hidden_auth


@given(repository_url())
def test_repository_url(url):
    parsed_url = URI.parse(url)
    url_without_fragment, _, _ = url.rpartition("#")
    url_without_fragment_or_ref, _, _ = url.rpartition("@")
    if parsed_url.ref:
        if parsed_url.fragment:
            assert parsed_url.url_without_ref == "{0}#{1}".format(
                url_without_fragment_or_ref, parsed_url.fragment
            )
        else:
            assert parsed_url.url_without_ref == url_without_fragment_or_ref
        assert parsed_url.url_without_fragment_or_ref == url_without_fragment_or_ref
    else:
        assert parsed_url.url_without_ref == url
        if parsed_url.fragment:
            assert parsed_url.url_without_fragment_or_ref == url_without_fragment
        else:
            assert parsed_url.url_without_fragment_or_ref == url
    if parsed_url.fragment:
        assert parsed_url.url_without_fragment == url_without_fragment
    else:
        assert parsed_url.url_without_fragment == url
