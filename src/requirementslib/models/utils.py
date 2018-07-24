# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import six
from attr import validators
from collections import OrderedDict
from itertools import chain, groupby
from first import first
from .._compat import Link
from ..utils import SCHEME_LIST, VCS_LIST, is_star


HASH_STRING = " --hash={0}"


def filter_none(k, v):
    if v:
        return True
    return False


def optional_instance_of(cls):
    return validators.optional(validators.instance_of(cls))


def extras_to_string(extras):
    """Turn a list of extras into a string"""
    if isinstance(extras, six.string_types):
        if extras.startswith("["):
            return extras

        else:
            extras = [extras]
    return "[{0}]".format(",".join(sorted(extras)))


def parse_extras(extras_str):
    """Turn a string of extras into a parsed extras list"""
    import requirements
    extras = first(
        requirements.parse("fakepkg{0}".format(extras_to_string(extras_str)))
    ).extras
    return extras


def specs_to_string(specs):
    """Turn a list of specifier tuples into a string"""
    if specs:
        if isinstance(specs, six.string_types):
            return specs
        return ",".join(["".join(spec) for spec in specs])
    return ""


def build_vcs_link(vcs, uri, name=None, ref=None, subdirectory=None, extras=None):
    if extras is None:
        extras = []
    vcs_start = "{0}+".format(vcs)
    if not uri.startswith(vcs_start):
        uri = "{0}{1}".format(vcs_start, uri)
    uri = add_ssh_scheme_to_git_uri(uri)
    if ref:
        uri = "{0}@{1}".format(uri, ref)
    if name:
        uri = "{0}#egg={1}".format(uri, name)
        if extras:
            extras = extras_to_string(extras)
            uri = "{0}{1}".format(uri, extras)
    if subdirectory:
        uri = "{0}&subdirectory={1}".format(uri, subdirectory)
    return Link(uri)


def get_version(pipfile_entry):
    if str(pipfile_entry) == "{}" or is_star(pipfile_entry):
        return ""

    elif hasattr(pipfile_entry, "keys") and "version" in pipfile_entry:
        if is_star(pipfile_entry.get("version")):
            return ""
        return pipfile_entry.get("version", "")

    if isinstance(pipfile_entry, six.string_types):
        return pipfile_entry
    return ""


def strip_ssh_from_git_uri(uri):
    """Return git+ssh:// formatted URI to git+git@ format"""
    if isinstance(uri, six.string_types):
        uri = uri.replace("git+ssh://", "git+", 1)
    return uri


def add_ssh_scheme_to_git_uri(uri):
    """Cleans VCS uris from pip format"""
    if isinstance(uri, six.string_types):
        # Add scheme for parsing purposes, this is also what pip does
        if uri.startswith("git+") and "://" not in uri:
            uri = uri.replace("git+", "git+ssh://", 1)
    return uri


def split_markers_from_line(line):
    """Split markers from a dependency"""
    from packaging.markers import Marker, InvalidMarker
    if not any(line.startswith(uri_prefix) for uri_prefix in SCHEME_LIST):
        marker_sep = ";"
    else:
        marker_sep = "; "
    markers = None
    if marker_sep in line:
        line, markers = line.split(marker_sep, 1)
        markers = markers.strip() if markers else None
    return line, markers


def split_vcs_method_from_uri(uri):
    """Split a vcs+uri formatted uri into (vcs, uri)"""
    vcs_start = "{0}+"
    vcs = first([vcs for vcs in VCS_LIST if uri.startswith(vcs_start.format(vcs))])
    if vcs:
        vcs, uri = uri.split("+", 1)
    return vcs, uri


def validate_vcs(instance, attr_, value):
    if value not in VCS_LIST:
        raise ValueError("Invalid vcs {0!r}".format(value))


def validate_path(instance, attr_, value):
    if not os.path.exists(value):
        raise ValueError("Invalid path {0!r}", format(value))


def validate_markers(instance, attr_, value):
    from packaging.markers import Marker, InvalidMarker
    try:
        Marker("{0}{1}".format(attr_.name, value))
    except InvalidMarker:
        raise ValueError("Invalid Marker {0}{1}".format(attr_, value))


def validate_specifiers(instance, attr_, value):
    from packaging.specifiers import SpecifierSet, InvalidSpecifier
    from packaging.markers import InvalidMarker
    if value == "":
        return True
    try:
        SpecifierSet(value)
    except (InvalidMarker, InvalidSpecifier):
        raise ValueError("Invalid Specifiers {0}".format(value))


def key_from_ireq(ireq):
    """Get a standardized key for an InstallRequirement."""
    if ireq.req is None and ireq.link is not None:
        return str(ireq.link)
    else:
        return key_from_req(ireq.req)


def key_from_req(req):
    """Get an all-lowercase version of the requirement's name."""
    if hasattr(req, 'key'):
        # from pkg_resources, such as installed dists for pip-sync
        key = req.key
    else:
        # from packaging, such as install requirements from requirements.txt
        key = req.name

    key = key.replace('_', '-').lower()
    return key


def _requirement_to_str_lowercase_name(requirement):
    """
    Formats a packaging.requirements.Requirement with a lowercase name.

    This is simply a copy of
    https://github.com/pypa/packaging/blob/16.8/packaging/requirements.py#L109-L124
    modified to lowercase the dependency name.

    Previously, we were invoking the original Requirement.__str__ method and
    lowercasing the entire result, which would lowercase the name, *and* other,
    important stuff that should not be lowercased (such as the marker). See
    this issue for more information: https://github.com/pypa/pipenv/issues/2113.
    """
    parts = [requirement.name.lower()]

    if requirement.extras:
        parts.append("[{0}]".format(",".join(sorted(requirement.extras))))

    if requirement.specifier:
        parts.append(str(requirement.specifier))

    if requirement.url:
        parts.append("@ {0}".format(requirement.url))

    if requirement.marker:
        parts.append("; {0}".format(requirement.marker))

    return "".join(parts)


def format_requirement(ireq, marker=None):
    """
    Generic formatter for pretty printing InstallRequirements to the terminal
    in a less verbose way than using its `__str__` method.
    """
    if ireq.editable:
        line = '-e {}'.format(ireq.link)
    else:
        line = _requirement_to_str_lowercase_name(ireq.req)

    if marker and ';' not in line:
        line = '{}; {}'.format(line, marker)

    return line


def format_specifier(ireq):
    """
    Generic formatter for pretty printing the specifier part of
    InstallRequirements to the terminal.
    """
    # TODO: Ideally, this is carried over to the pip library itself
    specs = ireq.specifier._specs if ireq.req is not None else []
    specs = sorted(specs, key=lambda x: x._spec[1])
    return ','.join(str(s) for s in specs) or '<any>'


def is_pinned_requirement(ireq):
    """
    Returns whether an InstallRequirement is a "pinned" requirement.

    An InstallRequirement is considered pinned if:

    - Is not editable
    - It has exactly one specifier
    - That specifier is "=="
    - The version does not contain a wildcard

    Examples:
        django==1.8   # pinned
        django>1.8    # NOT pinned
        django~=1.8   # NOT pinned
        django==1.*   # NOT pinned
    """
    if ireq.editable:
        return False

    if len(ireq.specifier._specs) != 1:
        return False

    op, version = first(ireq.specifier._specs)._spec
    return (op == '==' or op == '===') and not version.endswith('.*')


def as_tuple(ireq):
    """
    Pulls out the (name: str, version:str, extras:(str)) tuple from the pinned InstallRequirement.
    """
    if not is_pinned_requirement(ireq):
        raise TypeError('Expected a pinned InstallRequirement, got {}'.format(ireq))

    name = key_from_req(ireq.req)
    version = first(ireq.specifier._specs)._spec[1]
    extras = tuple(sorted(ireq.extras))
    return name, version, extras


def full_groupby(iterable, key=None):
    """Like groupby(), but sorts the input on the group key first."""
    return groupby(sorted(iterable, key=key), key=key)


def flat_map(fn, collection):
    """Map a function over a collection and flatten the result by one-level"""
    return chain.from_iterable(map(fn, collection))


def lookup_table(values, key=None, keyval=None, unique=False, use_lists=False):
    """
    Builds a dict-based lookup table (index) elegantly.

    Supports building normal and unique lookup tables.  For example:

    >>> assert lookup_table(
    ...     ['foo', 'bar', 'baz', 'qux', 'quux'], lambda s: s[0]) == {
    ...     'b': {'bar', 'baz'},
    ...     'f': {'foo'},
    ...     'q': {'quux', 'qux'}
    ... }

    For key functions that uniquely identify values, set unique=True:

    >>> assert lookup_table(
    ...     ['foo', 'bar', 'baz', 'qux', 'quux'], lambda s: s[0],
    ...     unique=True) == {
    ...     'b': 'baz',
    ...     'f': 'foo',
    ...     'q': 'quux'
    ... }

    The values of the resulting lookup table will be values, not sets.

    For extra power, you can even change the values while building up the LUT.
    To do so, use the `keyval` function instead of the `key` arg:

    >>> assert lookup_table(
    ...     ['foo', 'bar', 'baz', 'qux', 'quux'],
    ...     keyval=lambda s: (s[0], s[1:])) == {
    ...     'b': {'ar', 'az'},
    ...     'f': {'oo'},
    ...     'q': {'uux', 'ux'}
    ... }

    """
    if keyval is None:
        if key is None:
            keyval = (lambda v: v)
        else:
            keyval = (lambda v: (key(v), v))

    if unique:
        return dict(keyval(v) for v in values)

    lut = {}
    for value in values:
        k, v = keyval(value)
        try:
            s = lut[k]
        except KeyError:
            if use_lists:
                s = lut[k] = list()
            else:
                s = lut[k] = set()
        if use_lists:
            s.append(v)
        else:
            s.add(v)
    return dict(lut)


def dedup(iterable):
    """Deduplicate an iterable object like iter(set(iterable)) but
    order-reserved.
    """
    return iter(OrderedDict.fromkeys(iterable))


def name_from_req(req):
    """Get the name of the requirement"""
    if hasattr(req, 'project_name'):
        # from pkg_resources, such as installed dists for pip-sync
        return req.project_name
    else:
        # from packaging, such as install requirements from requirements.txt
        return req.name
