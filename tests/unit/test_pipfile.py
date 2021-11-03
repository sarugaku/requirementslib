# -*- coding: utf-8 -*-
import itertools
from pathlib import Path

import pytest

from requirementslib.exceptions import RequirementError
from requirementslib.models.lockfile import Lockfile
from requirementslib.models.pipfile import Pipfile


@pytest.mark.parametrize(
    "extension, default_len, dev_len, requires_python",
    [
        ("both-sections", 1, 1, "3.6"),
        ("dev-only", 0, 2, "3.6"),
        ("no-dev", 2, 0, "3.6"),
        ("no-sections", 0, 0, "3.6"),
        ("requires-python", 0, 2, "3.6"),
        ("no-sources", 0, 2, "3.6"),
        ("sources-key", 0, 2, "3.6"),
    ],
)
def test_pipfile_loader(
    pathlib_tmpdir, pipfile_dir, extension, default_len, dev_len, requires_python
):
    pipfile_location = pipfile_dir / "Pipfile.{0}".format(extension)
    pyproject_location = pipfile_dir / "pyproject.toml"
    pipfile_path = pathlib_tmpdir.joinpath(pipfile_location.stem)
    pyproject_path = pathlib_tmpdir.joinpath(pyproject_location.name)
    pipfile_path.write_text(pipfile_location.read_text())
    pyproject_path.write_text(pyproject_location.read_text())
    pipfile = Pipfile.load(pipfile_path.absolute().as_posix())
    assert len(pipfile.requirements) == len(pipfile.packages) == default_len
    assert len(pipfile.dev_requirements) == len(pipfile.dev_packages) == dev_len
    assert len(pipfile.sources) != 0
    for dev, only in itertools.product((True, False), (True, False)):
        expected_len = dev_len if dev else default_len
        if dev and not only:
            expected_len += default_len
        assert len(pipfile.get_deps(dev=dev, only=only)) == expected_len
    if default_len > 0:
        assert pipfile["packages"] is not None
    if dev_len > 0:
        assert pipfile["dev-packages"] is not None
    if (default_len + dev_len) > 0:
        assert "requests" in pipfile
    assert pipfile.path.as_posix() == pipfile_path.absolute().as_posix()
    assert pipfile.requires_python == requires_python
    assert pipfile.allow_prereleases is True
    assert isinstance(pipfile.build_requires, list)
    assert pipfile.build_backend is not None
    lockfile_from_pipfile = Lockfile.lockfile_from_pipfile(pipfile.path.as_posix())
    assert lockfile_from_pipfile is not None
    pipfile["dev-packages"]["six"] = "*"
    pipfile.write()


def test_failures(pathlib_tmpdir):
    with pytest.raises(RuntimeError):
        Pipfile.load_projectfile(None)
    fake_path = Path("my_fake_directory").absolute()
    with pytest.raises(FileNotFoundError):
        Pipfile.load_projectfile(fake_path)
    project_dir = pathlib_tmpdir.joinpath("project")
    project_dir.mkdir()
    with pytest.raises(RequirementError):
        Pipfile.load_projectfile(project_dir, create=False)
