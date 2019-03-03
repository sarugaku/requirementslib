# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function

import attr
import pip_shims.shims
from orderedmultidict import omdict
from six.moves.urllib.parse import quote_plus, unquote_plus
from urllib3 import util as urllib3_util
from urllib3.util import parse_url as urllib3_parse
from urllib3.util.url import Url

from ..environment import MYPY_RUNNING

if MYPY_RUNNING:
    from typing import List, Tuple, Text, Union, TypeVar, Optional
    from pip_shims.shims import Link
    from vistir.compat import Path

    _T = TypeVar("_T")
    STRING_TYPE = Union[bytes, str, Text]
    S = TypeVar("S", bytes, str, Text)


def _get_parsed_url(url):
    # type: (S) -> Url
    """
    This is a stand-in function for `urllib3.util.parse_url`

    The orignal function doesn't handle special characters very well, this simply splits
    out the authentication section, creates the parsed url, then puts the authentication
    section back in, bypassing validation.

    :return: The new, parsed URL object
    :rtype: :class:`~urllib3.util.url.Url`
    """

    try:
        parsed = urllib3_parse(url)
    except ValueError:
        scheme, _, url = url.partition("://")
        auth, _, url = url.rpartition("@")
        url = "{scheme}://{url}".format(scheme=scheme, url=url)
        parsed = urllib3_parse(url)._replace(auth=auth)
    return parsed


def remove_password_from_url(url):
    # type: (S) -> S
    """
    Given a url, remove the password and insert 4 dashes

    :param url: The url to replace the authentication in
    :type url: S
    :return: The new URL without authentication
    :rtype: S
    """

    parsed = _get_parsed_url(url)
    if parsed.auth:
        auth, _, _ = parsed.auth.partition(":")
        return parsed._replace(auth="{auth}:----".format(auth=auth)).url
    return parsed.url


@attr.s
class URI(object):
    #: The target hostname, e.g. `amazon.com`
    host = attr.ib(type=str)
    #: The URI Scheme, e.g. `salesforce`
    scheme = attr.ib(default="https", type=str)
    #: The numeric port of the url if specified
    port = attr.ib(default=None, type=int)
    #: The url path, e.g. `/path/to/endpoint`
    path = attr.ib(default="", type=str)
    #: Query parameters, e.g. `?variable=value...`
    query = attr.ib(default="", type=str)
    #: URL Fragments, e.g. `#fragment=value`
    fragment = attr.ib(default="", type=str)
    #: Subdirectory fragment, e.g. `&subdirectory=blah...`
    subdirectory = attr.ib(default="", type=str)
    #: VCS ref this URI points at, if available
    ref = attr.ib(default="", type=str)
    #: The username if provided, parsed from `user:password@hostname`
    username = attr.ib(default="", type=str)
    #: Password parsed from `user:password@hostname`
    password = attr.ib(default="", type=str, repr=False)
    #: An orderedmultidict representing query fragments
    query_dict = attr.ib(factory=omdict, type=omdict)
    #: The name of the specified package in case it is a VCS URI with an egg fragment
    name = attr.ib(default="", type=str)
    #: Any extras requested from the requirement
    extras = attr.ib(factory=tuple, type=tuple)
    #: Whether the url was parsed as a direct pep508-style URL
    is_direct_url = attr.ib(default=False, type=bool)
    #: Whether the url was an implicit `git+ssh` url (passed as `git+git@`)
    is_implicit_ssh = attr.ib(default=False, type=bool)
    _auth = attr.ib(default=None, type=str, repr=False)
    _fragment_dict = attr.ib(factory=dict, type=dict)

    def __attrs_post_init__(self):
        # type: () -> None
        self._parse_auth()._parse_query()._parse_fragment()

    def _parse_query(self):
        # type: () -> URI
        if self.query is None:
            self.query = ""
        queries = self.query.split("&")
        query_items = []
        for q in queries:
            key, _, val = q.partition("=")
            val = unquote_plus(val.replace("+", " "))
            query_items.append((key, val))
        self.query_dict.load(query_items)
        return self

    def _parse_fragment(self):
        # type: () -> URI
        if self.fragment is None:
            self.subdirectory = ""
            self.fragment = ""
        fragments = self.fragment.split("&")
        fragment_items = {}
        for q in fragments:
            key, _, val = q.partition("=")
            val = unquote_plus(val.replace("+", " "))
            fragment_items[key] = val
            if key == "egg":
                from .utils import parse_extras

                name, extras = pip_shims.shims._strip_extras(val)
                self.name = name
                if extras:
                    self.extras = tuple(parse_extras(extras))
            elif key == "subdirectory":
                self.subdirectory = val
        self._fragment_dict = fragment_items
        return self

    def _parse_auth(self):
        # type: () -> URI
        if self._auth:
            self.username, _, password = self._auth.partition(":")
            self.password = quote_plus(password)
        return self

    def get_password(self, unquote=False, include_token=True):
        # type: (bool, bool) -> str
        password = self.password
        if password and unquote:
            password = unquote_plus(password)
        else:
            password = ""
        return password

    @staticmethod
    def parse_subdirectory(url_part):
        # type: (str) -> Tuple[str, Optional[str]]
        subdir = None
        if "&subdirectory" in url_part:
            url_part, _, subdir = url_part.rpartition("&")
            subdir = "&{0}".format(subdir.strip())
        return url_part.strip(), subdir

    @classmethod
    def parse(cls, url):
        # type: (S) -> URI
        from .utils import DIRECT_URL_RE, split_ref_from_uri

        is_direct_url = False
        name_with_extras = None
        is_implicit_ssh = url.strip().startswith("git+git@")
        if is_implicit_ssh:
            from ..utils import add_ssh_scheme_to_git_uri

            url = add_ssh_scheme_to_git_uri(url)
        direct_match = DIRECT_URL_RE.match(url)
        if direct_match is not None:
            is_direct_url = True
            name_with_extras, _, url = url.partition("@")
            name_with_extras = name_with_extras.strip()
        url, ref = split_ref_from_uri(url.strip())
        parsed = _get_parsed_url(url)
        parsed_dict = dict(parsed._asdict()).copy()
        parsed_dict["is_direct_url"] = is_direct_url
        parsed_dict["is_implicit_ssh"] = is_implicit_ssh
        if name_with_extras:
            fragment = ""
            if parsed_dict["fragment"] is not None:
                fragment = "{0}".format(parsed_dict["fragment"])
            elif "&subdirectory" in parsed_dict["path"]:
                path, fragment = cls.parse_subdirectory(parsed_dict["path"])
                parsed_dict["path"] = path
            elif ref is not None and "&subdirectory" in ref:
                ref, fragment = cls.parse_subdirectory(ref)
            parsed_dict["fragment"] = "egg={0}{1}".format(name_with_extras, fragment)
        if ref is not None:
            parsed_dict["ref"] = ref.strip()
        return cls(**parsed_dict)

    def to_string(
        self,
        escape_password=True,  # type: bool
        unquote=True,  # type: bool
        direct=None,  # type: Optional[bool]
        strip_ssh=False,  # type: bool
    ):
        # type: (...) -> str
        """
        Converts the current URI to a string, unquoting or escaping the password as needed

        :param escape_password: Whether to replace password with ``----``, default True
        :param escape_password: bool, optional
        :param unquote: Whether to unquote url-escapes in the password, default False
        :param unquote: bool, optional
        :param bool direct: Whether to format as a direct URL
        :param bool strip_ssh: Whether to strip the SSH scheme from the url (git only)
        :return: The reconstructed string representing the URI
        :rtype: str
        """

        if direct is None:
            direct = self.is_direct_url
        if escape_password:
            password = "----" if (self.password or self.username) else ""
        else:
            password = self.get_password(unquote=unquote)
        auth = ""
        if self.username:
            if password:
                auth = "{self.username}:{password}@".format(password=password, self=self)
            else:
                auth = "{self.username}@".format(self=self)
        query = ""
        if self.query:
            query = "{query}?{self.query}".format(query=query, self=self)
        if not direct:
            if self.name:
                fragment = "#egg={self.name_with_extras}".format(self=self)
            elif self.extras and self.scheme and self.scheme.startswith("file"):
                from .utils import extras_to_string

                fragment = extras_to_string(self.extras)
            else:
                fragment = ""
            query = "{query}{fragment}".format(query=query, fragment=fragment)
        if self.subdirectory:
            query = "{query}&subdirectory={self.subdirectory}".format(
                query=query, self=self
            )
        url = "{self.scheme}://{auth}{self.host_port_path}{query}".format(
            auth=auth, self=self, query=query
        )
        if strip_ssh:
            from ..utils import strip_ssh_from_git_uri

            url = strip_ssh_from_git_uri(url)
        if self.name and direct:
            return "{self.name_with_extras}@ {url}".format(self=self, url=url)
        return url

    @property
    def host_port_path(self):
        # type: () -> str
        host = self.host
        if self.port:
            host = "{host}:{self.port!s}".format(host=host, self=self)
        path = "{self.path}".format(self=self)
        if self.ref:
            path = "{path}@{self.ref}".format(path=path, self=self)
        return "{host}{path}".format(host=host, path=path)

    @property
    def name_with_extras(self):
        # type: () -> str
        from .utils import extras_to_string

        if not self.name:
            return ""
        extras = extras_to_string(self.extras)
        return "{self.name}{extras}".format(self=self, extras=extras)

    @property
    def safe_string(self):
        # type: () -> str
        return self.to_string(escape_password=True, unquote=True)

    @property
    def unsafe_string(self):
        # type: () -> str
        return self.to_string(escape_password=False, unquote=True)

    @property
    def uri_escape(self):
        # type: () -> str
        return self.to_string(escape_password=False, unquote=False)

    @property
    def is_vcs(self):
        # type: () -> bool
        from ..utils import VCS_SCHEMES

        return self.scheme in VCS_SCHEMES

    def __str__(self):
        # type: () -> str
        return self.to_string(escape_password=True, unquote=True)
