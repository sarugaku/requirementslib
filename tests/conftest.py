# -*- coding=utf-8 -*-

import contextlib
import io
import json
import os
import pathlib
import random
import shutil
import subprocess as sp
import warnings

import distlib.wheel
import pytest
import requests

import requirementslib.fileutils

CURRENT_FILE = pathlib.Path(__file__).absolute()


def check_for_mercurial():
    c = sp.run(["hg, --help"], shell=True, capture_output=True)
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
    yield pathlib.Path(str(tmpdir))
    try:
        tmpdir.remove(ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def pip_src_dir(request, pathlib_tmpdir):
    old_src_dir = os.environ.get("PIP_SRC", "")
    os.environ["PIP_SRC"] = pathlib_tmpdir.as_posix()

    def finalize():
        os.environ["PIP_SRC"] = old_src_dir

    request.addfinalizer(finalize)
    return request


@pytest.fixture(autouse=True)
def monkeypatch_if_needed(monkeypatch):
    from requirementslib.models.setup_info import SetupInfo

    with monkeypatch.context() as m:
        if SKIP_INTERNET:
            m.setattr(SetupInfo, "get_info", mock_run_requires)
        yield


@pytest.fixture(scope="session")
def artifact_dir():
    return CURRENT_FILE.parent.joinpath("artifacts")


@pytest.fixture(scope="session")
def fixture_dir():
    return CURRENT_FILE.parent.joinpath("fixtures")


@pytest.fixture(scope="session")
def setup_py_dir(fixture_dir):
    return fixture_dir / "setup_py"


@pytest.fixture(scope="session")
def setup_cfg_dir(fixture_dir):
    return fixture_dir / "setup_cfg"


@pytest.fixture(scope="session")
def pipfile_dir(fixture_dir):
    return fixture_dir / "pipfile"


@pytest.fixture
def package_json(fixture_dir, request):
    name = request.param["name"]
    json_path = fixture_dir / "{0}.json".format(name)
    return json.loads(json_path.read_text())


@pytest.fixture
def monkeypatch_wheel_download(monkeypatch, fixture_dir):
    @contextlib.contextmanager
    def open_file(link, session=None, stream=True):
        link_filename = os.path.basename(link)
        dirname = distlib.wheel.Wheel(link_filename).name
        wheel_path = fixture_dir / "wheels" / dirname / link_filename
        buff = io.BytesIO(wheel_path.read_bytes())
        yield buff

    with monkeypatch.context() as m:
        m.setattr(requirementslib.fileutils, "open_file", open_file)
        yield


@pytest.fixture
def gen_metadata(request):
    name = request.param.get("name", "test-package")
    version = request.param.get(
        version,
        "{0}.{1}.{2}".format(
            random.randint(0, 5), random.randint(0, 10), random.randint(0, 10)
        ),
    )
    default_packages = ['enum34 ; python_version < "3.4"', "six", "requests"]
    packages = "\n".join(
        [
            "Requires-Dist: {0}".format(pkg)
            for pkg in request.param.get("packages", default_packages)
        ]
    )
    return """
Metadata-Version: 2.1
Name: {name}
Version: {version}
Summary: This is a test package
Home-page: http://test-package.test
Author: Test Author
Author-email: Fake-Author@test-package.test
License: MIT
Download-URL: https://github.com/this-is-fake/fake
Platform: UNKNOWN
Classifier: Development Status :: 4 - Beta
Classifier: Intended Audience :: Developers
Classifier: Operating System :: OS Independent
Classifier: Programming Language :: Python
Classifier: Programming Language :: Python :: 2.7
Classifier: Programming Language :: Python :: 3.5
Classifier: Programming Language :: Python :: 3.6
Classifier: Programming Language :: Python :: 3.7
Classifier: Programming Language :: Python :: 3.8
{packages}
""".format(
        name=name, version=version, packages=packages
    )


@pytest.fixture
def test_artifact(artifact_dir, pathlib_tmpdir, request):
    import requirementslib.utils

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
