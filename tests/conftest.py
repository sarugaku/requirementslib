# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function

import os
import shutil
import warnings

import pip_shims
import pytest
import requests
import vistir

import requirementslib.utils
from requirementslib.models.setup_info import SetupInfo

CURRENT_FILE = vistir.compat.Path(__file__).absolute()


def check_for_mercurial():
    c = vistir.misc.run(
        ["hg, --help"], return_object=True, block=True, nospin=True, combine_stderr=False
    )
    if c.returncode != 0:
        return False
    else:
        return True


def try_internet(url="http://clients3.google.com/generate_204", timeout=1.5):
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()


def check_internet():
    has_internet = False
    url = "http://clients3.google.com/generate_204"
    for i in range(3):
        try:
            try_internet(url)
        except Exception:
            continue
        else:
            has_internet = True
            break
    if not has_internet:
        warnings.warn("Failed connecting to internet: {0}".format(url), RuntimeWarning)
    return has_internet


HAS_INTERNET = check_internet()


def should_skip_internet():
    global HAS_INTERNET
    if os.environ.get("REQUIREMENTSLIB_SKIP_INTERNET_TESTS", None) is not None:
        return True
    return not HAS_INTERNET


HAS_MERCURIAL = check_for_mercurial()
SKIP_INTERNET = should_skip_internet()


def mock_run_requires(cls):
    return {}


def mock_unpack(
    link,
    source_dir,
    download_dir,
    only_download=False,
    session=None,
    hashes=None,
    progress_bar="off",
):
    return


def pytest_runtest_setup(item):
    if item.get_closest_marker("needs_hg") is not None and not HAS_MERCURIAL:
        pytest.skip("requires mercurial")
    elif item.get_closest_marker("needs_internet") is not None and SKIP_INTERNET:
        pytest.skip("requires internet access, skipping...")


@pytest.fixture
def pathlib_tmpdir(tmpdir):
    yield vistir.compat.Path(str(tmpdir))
    try:
        tmpdir.remove(ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def pip_src_dir(request, pathlib_tmpdir):
    old_src_dir = os.environ.get("PIP_SRC", "")
    os.environ["PIP_SRC"] = pathlib_tmpdir.as_posix()

    def finalize():
        os.environ["PIP_SRC"] = vistir.compat.fs_str(old_src_dir)

    request.addfinalizer(finalize)
    return request


@pytest.fixture(autouse=True)
def monkeypatch_if_needed(monkeypatch):
    with monkeypatch.context() as m:
        if SKIP_INTERNET:
            m.setattr(pip_shims.shims, "unpack_url", mock_unpack)
            m.setattr(SetupInfo, "get_info", mock_run_requires)
        yield


@pytest.fixture(scope="session")
def artifact_dir():
    return (
        vistir.compat.Path(requirementslib.utils.__file__)
        .absolute()
        .parent.parent.parent.joinpath("tests/artifacts")
    )


@pytest.fixture(scope="session")
def fixture_dir():
    return CURRENT_FILE.parent.joinpath("fixtures")


@pytest.fixture(scope="session")
def setup_py_dir(fixture_dir):
    return fixture_dir / "setup_py"


@pytest.fixture(scope="session")
def setup_cfg_dir(fixture_dir):
    return fixture_dir / "setup_cfg"


@pytest.fixture
def test_artifact(artifact_dir, pathlib_tmpdir, request):
    name = request.param["name"]
    as_artifact = request.param.get("as_artifact", False)
    target = artifact_dir.joinpath(name)
    if target.exists():
        if as_artifact:
            files = [path for path in target.iterdir() if path.is_file()]
        else:
            files = [path for path in target.iterdir() if path.is_dir()]
        files = sorted(files, reverse=True)
        installable_files = [
            f
            for f in files
            if requirementslib.utils.is_installable_file(f.as_posix())
            or f.joinpath("setup.py").exists()
            or f.joinpath("pyproject.toml").exists()
            or f.joinpath("setup.cfg").exists()
        ]
        installable = next(iter(f for f in installable_files), None)
        if installable:
            target_path = pathlib_tmpdir.joinpath(installable.name)
            if as_artifact:
                shutil.copy(installable.as_posix(), target_path.as_posix())
            else:
                shutil.copytree(installable.as_posix(), target_path.as_posix())
            yield target_path
            if as_artifact:
                target_path.unlink()
        else:
            raise RuntimeError(
                "failed to find installable artifact: %s (as_artifact: %s)\n"
                "files: %s\nInstallable: %s" % (name, as_artifact, files, installable)
            )
