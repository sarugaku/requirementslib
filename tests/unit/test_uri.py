# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from hypothesis import assume, given, strategies as st
from six.moves.urllib_parse import quote_plus, unquote_plus, urlsplit, urlunsplit

from requirementslib.models.url import URI

from .strategies import auth_url, repository_url, url_regex


@given(auth_url())
def test_uri(url):
    parsed_url = URI.parse(url)
    result = urlsplit(url)
    assume(result.scheme and result.netloc)
    rewritten_url = urlunsplit(result._replace(netloc=unquote_plus(result.netloc)))
    assert parsed_url.base_url == rewritten_url
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
