# -*- coding: utf-8 -*-
import pytest

from requirementslib.models.pipfile import Pipfile


@pytest.mark.parametrize(
    "extension, default_len, dev_len, requires_python",
    [
        ("both-sections", 1, 1, "3.6"),
        ("dev-only", 0, 2, "3.6"),
        ("no-dev", 2, 0, "3.6"),
        ("no-sections", 0, 0, "3.6"),
        ("requires-python", 0, 2, "3.6"),
    ],
)
def test_pipfile_loader(pipfile_dir, extension, default_len, dev_len, requires_python):
    pipfile_path = pipfile_dir / "Pipfile.{0}".format(extension)
    pipfile = Pipfile.load(pipfile_path.absolute().as_posix())
    assert len(pipfile.requirements) == len(pipfile.packages) == default_len
    assert len(pipfile.dev_requirements) == len(pipfile.dev_packages) == dev_len
    assert pipfile.requires_python == requires_python
    assert pipfile.allow_prereleases is True
