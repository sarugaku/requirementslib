"""A collection for utilities for working with files and paths."""
import os
from typing import Any, Text
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.parse import urlparse


def is_file_url(url: Any) -> bool:
    """Returns true if the given url is a file url."""
    if not url:
        return False
    if not isinstance(url, str):
        try:
            url = url.url
        except AttributeError:
            raise ValueError("Cannot parse url from unknown type: {!r}".format(url))
    return urllib_parse.urlparse(url.lower()).scheme == "file"


def is_valid_url(url: str) -> bool:
    """Checks if a given string is an url."""
    pieces = urlparse(url)
    return all([pieces.scheme, pieces.netloc])


def url_to_path(url: str) -> str:
    """Convert a valid file url to a local filesystem path.

    Follows logic taken from pip's equivalent function
    """
    assert is_file_url(url), "Only file: urls can be converted to local paths"
    _, netloc, path, _, _ = urllib_parse.urlsplit(url)
    # Netlocs are UNC paths
    if netloc:
        netloc = "\\\\" + netloc

    path = urllib_request.url2pathname(netloc + path)
    return urllib_parse.unquote(path)


if os.name == "nt":
    # from click _winconsole.py
    from ctypes import create_unicode_buffer, windll

    def get_long_path(short_path: Text) -> Text:
        BUFFER_SIZE = 500
        buffer = create_unicode_buffer(BUFFER_SIZE)
        get_long_path_name = windll.kernel32.GetLongPathNameW
        get_long_path_name(short_path, buffer, BUFFER_SIZE)
        return buffer.value


def normalize_path(path):
    """Return a case-normalized absolute variable-expanded path.

    :param str path: The non-normalized path
    :return: A normalized, expanded, case-normalized path
    :rtype: str
    """

    path = os.path.abspath(os.path.expandvars(os.path.expanduser(str(path))))
    if os.name == "nt" and os.path.exists(path):

        path = get_long_path(path)

    return os.path.normpath(os.path.normcase(path))
