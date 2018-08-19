# -*- coding=utf-8 -*-
import os
from vistir.contextmanagers import temp_environ


def test_lockfile(tmpdir):
    with temp_environ():
        os.environ['PIPENV_CACHE_DIR'] = tmpdir.strpath
        from requirementslib import Lockfile
        lockfile = Lockfile.create('.')

        requires = lockfile.as_requirements(dev=False)
        assert requires == []

        requires = lockfile.as_requirements(dev=True)
        assert 'attrs==18.1.0' in requires
