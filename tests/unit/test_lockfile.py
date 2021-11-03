# -*- coding=utf-8 -*-
import json
import os
import textwrap

import pytest
from vistir.contextmanagers import cd, temp_environ

from requirementslib.exceptions import MissingParameter, PipfileNotFound
from requirementslib.models.lockfile import Lockfile
from requirementslib.models.pipfile import Pipfile
from requirementslib.models.requirements import Requirement


def test_lockfile(tmpdir, fixture_dir):
    with temp_environ():
        os.environ["PIPENV_CACHE_DIR"] = tmpdir.strpath
        lockfile = Lockfile.create(fixture_dir / "lockfile")

        requires = lockfile.as_requirements(dev=True)
        assert any(req.startswith("attrs") for req in requires)

        requires = lockfile.as_requirements(dev=False)
        assert requires == []


def test_lockfile_requirements(pathlib_tmpdir):
    lockfile = pathlib_tmpdir.joinpath("Pipfile.lock")
    lockfile.write_text(
        textwrap.dedent(
            u"""
    {
        "_meta": {
            "hash": {
                "sha256": "88d256c1798cc297772ecd3d2152013e0b28201a5364a1c0f8e4dde79b6e200c"
            },
            "pipfile-spec": 6,
            "requires": {},
            "sources": [
                {
                    "name": "pypi",
                    "url": "https://pypi.org/simple",
                    "verify_ssl": true
                }
            ]
        },
        "default": {},
        "develop": {
            "alabaster": {
                "hashes": [
                    "sha256:674bb3bab080f598371f4443c5008cbfeb1a5e622dd312395d2d82af2c54c456",
                    "sha256:b63b1f4dc77c074d386752ec4a8a7517600f6c0db8cd42980cae17ab7b3275d7"
                ],
                "version": "==0.7.11"
            },
            "apipkg": {
                "hashes": [
                    "sha256:37228cda29411948b422fae072f57e31d3396d2ee1c9783775980ee9c9990af6",
                    "sha256:58587dd4dc3daefad0487f6d9ae32b4542b185e1c36db6993290e7c41ca2b47c"
                ],
                "markers": "python_version >= '2.7' and python_version != '3.0.*' and python_version != '3.1.*' and python_version != '3.2.*' and python_version != '3.3.*'",
                "version": "==1.5"
            },
            "appdirs": {
                "hashes": [
                    "sha256:9e5896d1372858f8dd3344faf4e5014d21849c756c8d5701f78f8a103b372d92",
                    "sha256:d8b24664561d0d34ddfaec54636d502d7cea6e29c3eaf68f3df6180863e2166e"
                ],
                "version": "==1.4.3"
            },
            "argparse": {
                "hashes": [
                    "sha256:62b089a55be1d8949cd2bc7e0df0bddb9e028faefc8c32038cc84862aefdd6e4",
                    "sha256:c31647edb69fd3d465a847ea3157d37bed1f95f19760b11a47aa91c04b666314"
                ],
                "markers": "python_version == '2.6'",
                "version": "==1.4.0"
            },
            "certifi": {
                "hashes": [
                    "sha256:376690d6f16d32f9d1fe8932551d80b23e9d393a8578c5633a2ed39a64861638",
                    "sha256:456048c7e371c089d0a77a5212fb37a2c2dce1e24146e3b7e0261736aaeaa22a"
                ],
                "version": "==2018.8.24"
            },
            "chardet": {
                "hashes": [
                    "sha256:84ab92ed1c4d4f16916e05906b6b75a6c0fb5db821cc65e70cbd64a3e2a5eaae",
                    "sha256:fc323ffcaeaed0e0a02bf4d117757b98aed530d9ed4531e3e15460124c106691"
                ],
                "version": "==3.0.4"
            },
            "requests": {
                "path": ".",
                "editable": true
            }
        }
    }
    """.strip()
        )
    )
    loaded = Lockfile.load(lockfile.as_posix())
    dump_to = pathlib_tmpdir.joinpath("new_lockfile")
    dump_to.mkdir()
    from_data = Lockfile.from_data(
        dump_to.as_posix(), json.loads(lockfile.read_text()), meta_from_project=False
    )
    assert isinstance(loaded.dev_requirements[0], Requirement)
    assert isinstance(loaded.dev_requirements_list[0], dict)
    with cd(pathlib_tmpdir.as_posix()):
        auto_detected_path = Lockfile()
        assert (
            auto_detected_path.path.absolute().as_posix()
            == lockfile.absolute().as_posix()
        )
        assert auto_detected_path["develop-editable"]["requests"] is not None


def test_failure(pipfile_dir):
    pipfile_location = pipfile_dir / "Pipfile.both-sections"
    with pytest.raises(PipfileNotFound):
        Lockfile.lockfile_from_pipfile("some_fake_pipfile_path")
    with pytest.raises(MissingParameter):
        Lockfile.from_data(None, None)
    with pytest.raises(MissingParameter):
        Lockfile.from_data(pipfile_location.as_posix(), None)
    with pytest.raises(MissingParameter):
        Lockfile.from_data(None, {})
    with pytest.raises(TypeError):
        Lockfile.from_data(pipfile_location.as_posix(), True)
