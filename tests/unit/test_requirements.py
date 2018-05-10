# -*- coding: utf-8 -*-
import os
import pytest
from first import first
from requirementslib import Requirement


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


@pytest.mark.utils
def test_convert_from_pip_fail_if_no_egg():
    """Parsing should fail without `#egg=`.
    """
    dep = 'git+https://github.com/kennethreitz/requests.git'
    with pytest.raises(ValueError) as e:
        dep = Requirement.from_line(dep).as_pipfile()
        assert 'pipenv requires an #egg fragment for vcs' in str(e)


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
