from itertools import tee

import pytest
from plette.pipfiles import Pipfile

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
    pipfile.write_text("")
    project_file = requirementslib.models.project.ProjectFile.read(
        pipfile.as_posix(),
        Pipfile,
        invalid_ok=True,
    )
    assert project_file.model is not None
    project_file.write()
    assert project_file.dumps().strip() == pipfile.read_text().strip()


def test_dir_with_pipfile_creates_project_file(pathlib_tmpdir):
    pipfile = pathlib_tmpdir.joinpath("Pipfile")
    pipfile.write_text("")
    project_file = requirementslib.models.project.ProjectFile.read(
        pipfile.as_posix(), Pipfile
    )
    assert project_file.model is not None
