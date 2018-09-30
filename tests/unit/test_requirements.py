# -*- coding: utf-8 -*-
import os
import pytest
from first import first
from requirementslib import Requirement
from vistir.compat import Path


UNIT_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.dirname(UNIT_TEST_DIR)
ARTIFACTS_DIR = os.path.join(TEST_DIR, 'artifacts')
TEST_WHEEL = os.path.join(ARTIFACTS_DIR, 'six', 'six-1.11.0-py2.py3-none-any.whl')
TEST_WHEEL_PATH = Path(TEST_WHEEL)
TEST_WHEEL_URI = TEST_WHEEL_PATH.absolute().as_uri()
TEST_PROJECT_RELATIVE_DIR = 'tests/artifacts/six/six-1.11.0-py2.py3-none-any.whl'

# Pipfile format <-> requirements.txt format.
DEP_PIP_PAIRS = [
    ({'requests': '*'}, 'requests'),
    ({'requests': {'extras': ['socks'], 'version': '*'}}, 'requests[socks]'),
    ({'django': '>1.10'}, 'django>1.10'),
    ({'Django': '>1.10'}, 'Django>1.10'),
    (
        {'requests': {'extras': ['socks'], 'version': '>1.10'}},
        'requests[socks]>1.10',
    ),
    (
        {'requests': {'extras': ['socks'], 'version': '==1.10'}},
        'requests[socks]==1.10',
    ),
    (
        {'pinax': {
            'git': 'git://github.com/pinax/pinax.git',
            'ref': '1.4',
            'editable': True,
        }},
        '-e git+git://github.com/pinax/pinax.git@1.4#egg=pinax',
    ),
    (
        {'pinax': {'git': 'git://github.com/pinax/pinax.git', 'ref': '1.4'}},
        'git+git://github.com/pinax/pinax.git@1.4#egg=pinax',
    ),
    (   # Mercurial.
        {'MyProject': {
            'hg': 'http://hg.myproject.org/MyProject', 'ref': 'da39a3ee5e6b',
        }},
        'hg+http://hg.myproject.org/MyProject@da39a3ee5e6b#egg=MyProject',
    ),
    (   # SVN.
        {'MyProject': {
            'svn': 'svn://svn.myproject.org/svn/MyProject', 'editable': True,
        }},
        '-e svn+svn://svn.myproject.org/svn/MyProject#egg=MyProject',
    ),
    (
        # Extras in url
        {'discord.py': {
                'file': 'https://github.com/Rapptz/discord.py/archive/rewrite.zip',
                'extras': ['voice']
        }},
        'https://github.com/Rapptz/discord.py/archive/rewrite.zip#egg=discord.py[voice]',
    ),
    (
        {'requests': {
            'git': 'https://github.com/requests/requests.git',
            'ref': 'master', 'extras': ['security'],
            'editable': False
        }},
        'git+https://github.com/requests/requests.git@master#egg=requests[security]',
    ),
    (
        {'FooProject': {
            'version': '==1.2',
            'hashes': [
                'sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
            ],
        }},
        'FooProject==1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
    ),
    (
        {'FooProject': {
            'version': '==1.2',
            'extras': ['stuff'],
            'hashes': [
                'sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
            ],
        }},
        'FooProject[stuff]==1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
    ),
    (
        {'six': {
            'file': '{0}'.format(TEST_WHEEL_URI)
        }},
        TEST_WHEEL_URI
    ),
    (
        {'plette': {
            'extras': ['validation'], 'version': '>=0.1.1'
        }},
        'plette[validation] (>=0.1.1)'
    ),
    (
        {'pythonfinder': {
            'ref': 'master', 'git': 'https://github.com/techalchemy/pythonfinder.git',
            'subdirectory': 'mysubdir', 'extras': ['dev'], 'editable': True
        }},
        '-e git+https://github.com/techalchemy/pythonfinder.git@master#egg=pythonfinder[dev]&subdirectory=mysubdir'
    )
]

# These are legacy Pipfile formats we need to be able to do Pipfile -> pip,
# but don't need to for pip -> Pipfile anymore.
DEP_PIP_PAIRS_LEGACY_PIPFILE = [
    (
        {'FooProject': {
            'version': '==1.2',
            'hash': 'sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
        }},
        'FooProject==1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
    ),
    (
        {'FooProject': {
            'version': '==1.2',
            'extras': ['stuff'],
            'hash': 'sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
        }},
        'FooProject[stuff]==1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
    ),
]


@pytest.mark.utils
@pytest.mark.parametrize('expected, requirement', DEP_PIP_PAIRS)
def test_convert_from_pip(expected, requirement):
    pkg_name = first(expected.keys())
    pkg_pipfile = expected[pkg_name]
    if hasattr(pkg_pipfile, 'keys') and 'editable' in pkg_pipfile and not pkg_pipfile['editable']:
        del expected[pkg_name]['editable']
    assert Requirement.from_line(requirement).as_pipfile() == expected


@pytest.mark.to_line
@pytest.mark.parametrize(
    'requirement, expected', DEP_PIP_PAIRS + DEP_PIP_PAIRS_LEGACY_PIPFILE,
)
def test_convert_from_pipfile(requirement, expected):
    pkg_name = first(requirement.keys())
    pkg_pipfile = requirement[pkg_name]
    req = Requirement.from_pipfile(pkg_name, pkg_pipfile)
    if " (" in expected and expected.endswith(")"):
        # To strip out plette[validation] (>=0.1.1)
        expected = expected.replace(" (", "").rstrip(")")
    assert req.as_line() == expected.lower() if '://' not in expected else expected


@pytest.mark.utils
def test_convert_from_pip_fail_if_no_egg():
    """Parsing should fail without `#egg=`.
    """
    dep = 'git+https://github.com/kennethreitz/requests.git'
    with pytest.raises(ValueError) as e:
        dep = Requirement.from_line(dep).as_pipfile()
        assert 'pipenv requires an #egg fragment for vcs' in str(e)


@pytest.mark.editable
def test_one_way_editable_extras():
    dep = '-e .[socks]'
    dep = Requirement.from_line(dep).as_pipfile()
    k = first(dep.keys())
    assert dep[k]['extras'] == ['socks']


@pytest.mark.utils
def test_convert_from_pip_git_uri_normalize():
    """Pip does not parse this correctly, but we can (by converting to ssh://).
    """
    dep = 'git+git@host:user/repo.git#egg=myname'
    dep = Requirement.from_line(dep).as_pipfile()
    assert dep == {
        'myname': {
            'git': 'git@host:user/repo.git',
        }
    }


@pytest.mark.utils
@pytest.mark.requirements
def test_get_requirements():
    # Test eggs in URLs
    url_with_egg = Requirement.from_line(
        'https://github.com/IndustriaTech/django-user-clipboard/archive/0.6.1.zip#egg=django-user-clipboard'
    ).requirement
    assert url_with_egg.url == 'https://github.com/IndustriaTech/django-user-clipboard/archive/0.6.1.zip'
    assert url_with_egg.name == 'django-user-clipboard'
    # Test URLs without eggs pointing at installable zipfiles
    url = Requirement.from_line(
        'https://github.com/kennethreitz/tablib/archive/0.12.1.zip'
    ).requirement
    assert url.url == 'https://github.com/kennethreitz/tablib/archive/0.12.1.zip'
    wheel_line = "https://github.com/pypa/pipenv/raw/master/tests/test_artifacts/six-1.11.0+mkl-py2.py3-none-any.whl"
    wheel = Requirement.from_line(wheel_line)
    assert wheel.as_pipfile() == {
        "six": {'file': 'https://github.com/pypa/pipenv/raw/master/tests/test_artifacts/six-1.11.0+mkl-py2.py3-none-any.whl'}
    }
    # Requirementslib inserts egg fragments as names when possible if we know the appropriate name
    # this allows for custom naming
    assert Requirement.from_pipfile(wheel.name, list(wheel.as_pipfile().values())[0]).as_line().split("#")[0] == wheel_line
    # Test VCS urls with refs and eggnames
    vcs_url = Requirement.from_line(
        'git+https://github.com/kennethreitz/tablib.git@master#egg=tablib'
    ).requirement
    assert vcs_url.vcs == 'git' and vcs_url.name == 'tablib' and vcs_url.revision == 'master'
    assert vcs_url.url == 'git+https://github.com/kennethreitz/tablib.git'
    # Test normal package requirement
    normal = Requirement.from_line('tablib').requirement
    assert normal.name == 'tablib'
    # Pinned package  requirement
    spec = Requirement.from_line('tablib==0.12.1').requirement
    assert spec.name == 'tablib' and spec.specs == [('==', '0.12.1')]
    # Test complex package with both extras and markers
    extras_markers = Requirement.from_line(
        "requests[security]; os_name=='posix'"
    ).requirement
    assert extras_markers.extras == ['security']
    assert extras_markers.name == 'requests'
    assert str(extras_markers.marker) == 'os_name == "posix"'
    # Test VCS uris get generated correctly, retain git+git@ if supplied that way, and are named according to egg fragment
    git_reformat = Requirement.from_line(
        '-e git+git@github.com:pypa/pipenv.git#egg=pipenv'
    ).requirement
    assert git_reformat.url == 'git+git@github.com:pypa/pipenv.git'
    assert git_reformat.name == 'pipenv'
    assert git_reformat.editable
    # Previously VCS uris were being treated as local files, so make sure these are not handled that way
    assert not git_reformat.local_file
    # Test regression where VCS uris were being handled as paths rather than VCS entries
    assert git_reformat.vcs == 'git'
    assert git_reformat.link.url == 'git+ssh://git@github.com/pypa/pipenv.git#egg=pipenv'
    # Test VCS requirements being added with extras for constraint_line
    git_extras = Requirement.from_line(
        '-e git+https://github.com/requests/requests.git@master#egg=requests[security]'
    )
    assert git_extras.as_line() == '-e git+https://github.com/requests/requests.git@master#egg=requests[security]'
    assert git_extras.constraint_line == '-e git+https://github.com/requests/requests.git@master#egg=requests[security]'
    # these will fail due to not being real paths
    # local_wheel = Requirement.from_pipfile('six', {'path': '../wheels/six/six-1.11.0-py2.py3-none-any.whl'})
    # assert local_wheel.as_line() == 'file:///home/hawk/git/wheels/six/six-1.11.0-py2.py3-none-any.whl'
    # local_wheel_from_line = Requirement.from_line('../wheels/six/six-1.11.0-py2.py3-none-any.whl')
    # assert local_wheel_from_line.as_pipfile() == {'six': {'path': '../wheels/six/six-1.11.0-py2.py3-none-any.whl'}}


def test_get_ref():
    r = Requirement.from_line("-e git+https://github.com/sarugaku/shellingham.git@1.2.1#egg=shellingham")
    assert r.commit_hash == "9abe7464dab5cc362fe08361619d3fb15f2e16ab"


def test_get_local_ref(tmpdir):
    six_dir = tmpdir.join("six")
    import vistir
    c = vistir.misc.run(["git", "clone", "https://github.com/benjaminp/six.git", six_dir.strpath], return_object=True, nospin=True)
    assert c.returncode == 0
    r = Requirement.from_line("git+{0}#egg=six".format(Path(six_dir.strpath).as_uri()))
    assert r.commit_hash
