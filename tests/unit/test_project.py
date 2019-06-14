# -*- coding: utf-8 -*-
from itertools import tee

import pytest
import vistir.compat

import requirementslib.models.project

from .test_requirements import DEP_PIP_PAIRS


def pairwise(seq):
    a, b = tee(seq)
    next(b, None)
    return zip(a, b)


PIPFILE_ENTRIES = [entry for entry, pip_entry in DEP_PIP_PAIRS]
PAIRED_PIPFILE_ENTRIES = list(pairwise(PIPFILE_ENTRIES))


@pytest.mark.parametrize("entry_1, entry_2", PAIRED_PIPFILE_ENTRIES)
def test_pipfile_entry_comparisons(entry_1, entry_2):
    assert (
        requirementslib.models.project._are_pipfile_entries_equal(entry_1, entry_1)
        is True
    )
    assert (
        requirementslib.models.project._are_pipfile_entries_equal(entry_1, entry_2)
        is False
    )


def test_project_file_works_if_file_exists_but_is_empty(pathlib_tmpdir):
    pipfile = pathlib_tmpdir.joinpath("Pipfile")
    pipfile.write_text(u"")
    project_file = requirementslib.models.project.ProjectFile.read(
        pipfile.as_posix(),
        requirementslib.models.pipfile.plette.pipfiles.Pipfile,
        invalid_ok=True,
    )
    assert project_file.model is not None
    project_file.write()
    project_file_contents = pipfile.read_text()
    assert project_file.dumps().strip() == pipfile.read_text().strip()


def test_dir_with_empty_pipfile_file_raises_exception(pathlib_tmpdir):
    with pytest.raises(vistir.compat.FileNotFoundError):
        requirementslib.models.project.Project(root=pathlib_tmpdir.as_posix())


def test_dir_with_pipfile_creates_project_file(pathlib_tmpdir):
    pipfile = pathlib_tmpdir.joinpath("Pipfile")
    pipfile.write_text(u"")
    project_file = requirementslib.models.project.ProjectFile.read(
        pipfile.as_posix(), requirementslib.models.pipfile.plette.pipfiles.Pipfile
    )
    assert project_file.model is not None


def test_dir_with_pipfile_creates_project(pathlib_tmpdir):
    pipfile = pathlib_tmpdir.joinpath("Pipfile")
    pipfile.write_text(u"")
    project = requirementslib.models.project.Project(root=pathlib_tmpdir.as_posix())
    assert project.pipfile is not None
    assert vistir.compat.Path(project.pipfile_location).as_posix() == pipfile.as_posix()
    assert project.lockfile is None
    assert (
        vistir.compat.Path(project.lockfile_location).as_posix()
        == pathlib_tmpdir.joinpath("Pipfile.lock").as_posix()
    )
    project.add_line_to_pipfile("requests[security]", False)
    assert project.pipfile["packages"]["requests"]._data == {
        "extras": ["security"],
        "version": "*",
    }
    project.remove_keys_from_pipfile(["requests"], True, False)
    assert "requests" not in project.pipfile["packages"]
