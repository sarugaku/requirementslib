# -*- coding: utf-8 -*-
import pytest
from packaging.markers import Marker
from packaging.specifiers import Specifier, SpecifierSet
from packaging.version import Version

import requirementslib.models.markers


@pytest.mark.parametrize(
    "version, cleaned",
    [
        ("3.0.*", (3, 0)),
        ("3.1.*", (3, 1)),
        ("3.2.*", (3, 2)),
        ("3.4.*", (3, 4)),
        ("3.*", (3,)),
        ("3.*.4", (3,)),
        ("*", tuple()),
        ("*.3.4", tuple()),
        ("3.4.7", (3, 4, '7')),
        ("3.11.0b1", (3, 11, '0b1')),
    ],
)
def test_tuplize_version(version, cleaned):
    assert requirementslib.models.markers._tuplize_version(version) == cleaned


@pytest.mark.parametrize(
    "version_tuple, version_str",
    [((3, 0), "3.0"), ((3, 7, 3), "3.7.3"), ("3.7.3", "3.7.3")],
)
def test_format_version(version_tuple, version_str):
    assert requirementslib.models.markers._format_version(version_tuple) == version_str


@pytest.mark.parametrize(
    "specifier, rounded_specifier",
    [
        ("<=3.6", Specifier("<3.7")),
        (Specifier("<=3.6"), Specifier("<3.7")),
        (">2.6", Specifier(">=2.7")),
        (Specifier(">2.6"), Specifier(">=2.7")),
        (">1.1", Specifier(">=1.2")),
    ],
)
def test_format_pyspec(specifier, rounded_specifier):
    assert requirementslib.models.markers._format_pyspec(specifier) == rounded_specifier


@pytest.mark.parametrize(
    "specset, new_set",
    [
        (
            "!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*",
            [("!=", (3, 0)), ("!=", (3, 1)), ("!=", (3, 2)), ("!=", (3, 3))],
        ),
        (
            "!=3.*,!=3.11.0b1,!=*.2,!=*",
            [("!=", ()), ("!=", ()), ("!=", (3,)), ("!=", (3, 11, '0b1'))],
        )
    ],
)
def test_get_specs(specset, new_set):
    assert requirementslib.models.markers._get_specs(specset) == new_set


@pytest.mark.parametrize(
    "specset, new_set",
    [
        (SpecifierSet("!=3.0,!=3.1,!=3.2,!=3.3"), [("not in", "3.0, 3.1, 3.2, 3.3")]),
        (SpecifierSet("==3.0,==3.1,==3.2,==3.3"), [("in", "3.0, 3.1, 3.2, 3.3")]),
        (
            SpecifierSet("!=3.0,!=3.1,!=3.2,!=3.3,>=2.7,<3.7"),
            [(">=", "2.7"), ("not in", "3.0, 3.1, 3.2, 3.3"), ("<", "3.7")],
        ),
        (SpecifierSet(">2.6,>=2.7,<3.6,<3.7"), [(">=", "2.7"), ("<", "3.7")]),
        (SpecifierSet("!=3.11.0b1"), [("!=", "3.11.0b1")]),
        (SpecifierSet("!=*.3"), [("!=", "")]),

    ],
)
def test_cleanup_pyspecs(specset, new_set):
    assert requirementslib.models.markers.cleanup_pyspecs(specset) == new_set


@pytest.mark.parametrize(
    "specset, versions",
    [
        (
            SpecifierSet("!=3.0,!=3.1,!=3.2,!=3.3"),
            [
                ("!=", Version("3.0")),
                ("!=", Version("3.1")),
                ("!=", Version("3.2")),
                ("!=", Version("3.3")),
            ],
        ),
        (
            SpecifierSet("==3.0.*,==3.1.*,==3.2.*,==3.3.*"),
            [
                ("==", Version("3.0")),
                ("==", Version("3.1")),
                ("==", Version("3.2")),
                ("==", Version("3.3")),
            ],
        ),
        (
            SpecifierSet("!=3.0,!=3.1,!=3.2,!=3.3,>=2.7,<3.7"),
            [
                (">=", Version("2.7")),
                ("!=", Version("3.0")),
                ("!=", Version("3.1")),
                ("!=", Version("3.2")),
                ("!=", Version("3.3")),
                ("<", Version("3.7")),
            ],
        ),
        (
            SpecifierSet(">2.6,>=2.7,<3.6,<3.7"),
            [
                (">", Version("2.6")),
                (">=", Version("2.7")),
                ("<", Version("3.6")),
                ("<", Version("3.7")),
            ],
        ),
    ],
)
def test_get_versions(specset, versions):
    assert requirementslib.models.markers.get_versions(specset) == versions


@pytest.mark.parametrize(
    "marker, extras",
    [
        (Marker("extra == 'security' and os_name == 'nt'"), {"security"}),
        (Marker("os_name == 'security' and python_version >= '2.7'"), set()),
    ],
)
def test_get_extras(marker, extras):
    assert requirementslib.models.markers.get_contained_extras(marker) == extras


@pytest.mark.parametrize(
    "marker, pyversions",
    [
        (
            Marker(
                "os_name == 'nt' and python_version >= '2.7' and python_version <= '3.5'"
            ),
            SpecifierSet("<=3.5,>=2.7"),
        ),
        (
            Marker(
                "os_name == 'posix' and python_version >= '2.7' and python_version not in '3.0.*,3.1.*,3.2.*,3.3.*'"
            ),
            SpecifierSet("!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,>=2.7"),
        ),
        (
            Marker(
                "python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'"
            ),
            SpecifierSet("!=3.0,!=3.1,!=3.2,!=3.3,!=3.4,>=2.7"),
        ),
    ],
)
def test_get_pyversions(marker, pyversions):
    assert requirementslib.models.markers.get_contained_pyversions(marker) == pyversions


@pytest.mark.parametrize(
    "marker, expected",
    [
        (
            Marker(
                "os_name == 'nt' and python_version >= '2.7' and python_version <= '3.5'"
            ),
            "python_version >= '2.7' and python_version < '3.6' and os_name == 'nt'",
        ),
        (
            Marker(
                "os_name == 'posix' and python_version >= '2.7' and python_version not in '3.0.*,3.1.*,3.2.*,3.3.*'"
            ),
            "python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3' and os_name == 'posix'",
        ),
        (
            Marker(
                "python_version > '3.5' and python_version < '3.7' and python_version > '3.5'"
            ),
            "python_version >= '3.6' and python_version < '3.7'",
        ),
        (
            Marker("python_version < '3.11.0b1'"),
            "python_full_version < '3.11.0b1'",
        ),
    ],
)
def test_normalize_marker_str(marker, expected):
    assert requirementslib.models.markers.normalize_marker_str(marker) == expected


@pytest.mark.parametrize(
    "marker",
    [
        Marker("python_version < '*'"),
        Marker("python_version < '*.3'"),
        Marker("python_version < '*.3.2'"),
    ],
)
def test_normalize_marker_str_invalid_marker(marker):
    with pytest.raises(ValueError):
        requirementslib.models.markers.normalize_marker_str(marker)


@pytest.mark.parametrize(
    "marker, contains_extras, contains_pyversion",
    [
        (Marker("os_name == 'nt'"), False, False),
        (Marker("extra == 'security' or extra == 'socks'"), True, False),
        (Marker("extra == 'security' and python_version >= '2.7'"), True, True),
        (
            Marker(
                "python_version >= '2.7' and python_version not in '3.0.*, 3.1.*, 3.2.*, 3.3.*'"
            ),
            False,
            True,
        ),
    ],
)
def test_contains_extras_or_pyversions(marker, contains_extras, contains_pyversion):
    assert requirementslib.models.markers.contains_extra(marker) is contains_extras
    assert requirementslib.models.markers.contains_pyversion(marker) is contains_pyversion


@pytest.mark.parametrize(
    "marker, expected",
    [
        ("!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*", 'python_version not in "3.0, 3.1, 3.2, 3.3"'),
        # This is a broken version but we can still parse it correctly
        ("!=3.0*,!=3.1*,!=3.2*,!=3.3*", 'python_version not in "3.0, 3.1, 3.2, 3.3"'),
        (
            ">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,~=3.7",
            'python_version >= "2.7" and python_version not in "3.0, 3.1, 3.2, 3.3" and python_version ~= "3.7"',
        ),
        ("<=3.5,>=2.7", 'python_version >= "2.7" and python_version < "3.6"'),
        (">=3.6.1", 'python_full_version >= "3.6.1"'),
        ("!=3.2.1,>=3.1", 'python_version >= "3.1" and python_full_version != "3.2.1"'),
        (
            "!=3.0.*,!=3.1.1,!=3.1.2",
            'python_version != "3.0" and python_full_version not in "3.1.1, 3.1.2"',
        ),
        (
            "!=3.0.*,!=3.1.1,>=3.1.4",
            'python_version != "3.0" and python_full_version != "3.1.1" and python_full_version >= "3.1.4"',
        ),
    ],
)
def test_marker_from_specifier(marker, expected):
    assert str(requirementslib.models.markers.marker_from_specifier(marker)) == expected
