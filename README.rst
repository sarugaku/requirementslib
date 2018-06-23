RequirementsLib: Requirement Management Library for Pip and Pipenv
===================================================================

.. image:: https://img.shields.io/pypi/v/requirementslib.svg
    :target: https://pypi.python.org/pypi/requirementslib

.. image:: https://img.shields.io/pypi/l/requirementslib.svg
    :target: https://pypi.python.org/pypi/requirementslib

.. image:: https://travis-ci.org/techalchemy/requirementslib.svg?branch=master
    :target: https://travis-ci.org/techalchemy/requirementslib

.. image:: https://ci.appveyor.com/api/projects/status/n16s8fhn71o0v0tl/branch/master?svg=true
    :target: https://ci.appveyor.com/project/techalchemy/requirementslib/branch/master

.. image:: https://img.shields.io/pypi/pyversions/requirementslib.svg
    :target: https://pypi.python.org/pypi/requirementslib

.. image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
    :target: https://saythanks.io/to/techalchemy

.. image:: https://readthedocs.org/projects/requirementslib/badge/?version=master
    :target: http://requirementslib.readthedocs.io/en/master/?badge=master
    :alt: Documentation Status

Installation
*************

Install from `PyPI`_:

  ::

    $ pipenv install --pre requirementslib

Install from `Github`_:

  ::

    $ pipenv install -e git+https://github.com/techalchemy/requirementslib.git#egg=requirementslib


.. _PyPI: https://www.pypi.org/project/requirementslib
.. _Github: https://github.com/techalchemy/requirementslib


.. _`Summary`:

Summary
********

RequirementsLib provides a simple layer for building and interacting with
requirements in both the `Pipfile <https://github.com/pypa/pipfile/>`_ format
and the `requirements.txt <https://github.com/pypa/pip/>`_ format.  This library
was originally built for converting between these formats in `Pipenv <https://github.com/pypa/pipenv>`_.

.. _`Usage`:

Usage
******

Importing a lockfile into your *setup.py* file
//////////////////////////////////////////////

You can use RequirementsLib to import your lockfile into your setup file for including your
**install_requires** dependencies:

  ::

    from requirementslib import Lockfile
    lockfile = Lockfile.create('/path/to/project/dir')
    install_requires = lockfile.as_requirements(dev=False)


Interacting with a *Pipfile* directly
//////////////////////////////////////

You can also interact directly with a Pipfile:

  ::

    >>> from requirementslib import Pipfile
    >>> pf = Pipfile.load('/home/hawk/git/pypa-pipenv')
    >>> pf.sections
    [Section(name='packages', requirements=[]), Section(name='dev-packages', requirements=[Requirement(name='pipenv', vcs=None, req=FileRequirement(setup_path=None, path='.', editable=True, uri='file:///home/hawk/git/pypa-pipenv', link=<Link file:///home/hawk/git/pypa-pipenv>, name='pipenv', req=<Requirement: "-e file:///home/hawk/git/pypa-pipenv">), markers='', specifiers=None, index=None, editable=True, hashes=[], extras=None),...]


And you can even write it back out into Pipfile's native format:

  ::

    >>> print(pf.dump(to_dict=False))
    [packages]

    [dev-packages]
    pipenv = {path = ".", editable = true}
    flake8 = ">=3.3.0,<4"
    pytest = "*"
    mock = "*"

    [scripts]
    tests = "bash ./run-tests.sh"

    [pipenv]
    allow_prereleases = true


Create a requirement object from *requirements.txt* format
///////////////////////////////////////////////////////////

  ::

    >>> from requirementslib import Requirement
    >>> r = Requirement.from_line('-e git+https://github.com/pypa/pipenv.git@master#egg=pipenv')
    >>> print(r)
    Requirement(name='pipenv', vcs='git', req=VCSRequirement(editable=True, uri='git+https://github.com/pypa/pipenv.git', path=None, vcs='git', ref='master', subdirectory=None, name='pipenv', link=<Link git+https://github.com/pypa/pipenv.git@master#egg=pipenv>, req=<Requirement: "-e git+https://github.com/pypa/pipenv.git@master#egg=pipenv">), markers=None, specifiers=None, index=None, editable=True, hashes=[], extras=[])

    >>> r.as_pipfile()
    {'pipenv': {'editable': True, 'ref': 'master', 'git': 'https://github.com/pypa/pipenv.git'}}


Or move from *Pipfile* format to *requirements.txt*:

  ::

    >>> r = Requirement.from_pipfile(name='pythonfinder', indexes=[], pipfile={'path': '../pythonfinder', 'editable': True})
    >>> r.as_line()
    '-e ../pythonfinder'


Integrations
*************

* `Pip <https://github.com/pypa/pip>`_
* `Pipenv <https://github.com/pypa/pipenv>`_
* `Pipfile`_
