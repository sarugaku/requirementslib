# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function

import os

import pytest
import vistir


def check_for_mercurial():
    c = vistir.misc.run(["hg, --help"], return_object=True, block=True, nospin=True,
                        combine_stderr=False)
    if c.returncode != 0:
        return False
    else:
        return True


HAS_MERCURIAL = check_for_mercurial()


def pytest_runtest_setup(item):
    if item.get_marker('needs_hg') is not None and not HAS_MERCURIAL:
        pytest.skip('requires mercurial')


@pytest.fixture
def pathlib_tmpdir(request, tmpdir):
    yield vistir.compat.Path(str(tmpdir))
    try:
        tmpdir.remove(ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def pip_src_dir(request, pathlib_tmpdir):
    old_src_dir = os.environ.get('PIP_SRC', '')
    os.environ['PIP_SRC'] = pathlib_tmpdir.as_posix()

    def finalize():
        os.environ['PIP_SRC'] = vistir.compat.fs_str(old_src_dir)

    request.addfinalizer(finalize)
    return request
