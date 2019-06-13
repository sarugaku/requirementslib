# -*- coding: utf-8 -*-
import pytest

from requirementslib.exceptions import (
    FileCorruptException,
    FileExistsError,
    LockfileCorruptException,
    MissingParameter,
    PipfileCorruptException,
    PipfileNotFound,
)


@pytest.mark.parametrize(
    "exc_type, msg, match",
    [
        (FileExistsError, "somefile.txt", r".*somefile.txt.*"),
        (MissingParameter, "myparam", r".*Missing Parameter: myparam.*"),
        (
            FileCorruptException,
            "TheFile",
            r"ERROR: Failed to load file at TheFile.*\n.*it will be.*",
        ),
        (
            LockfileCorruptException,
            "Pipfile.lock",
            r"ERROR: Failed to load lockfile at Pipfile.lock.*\n.*it will be.*",
        ),
        (
            PipfileCorruptException,
            "Pipfile",
            r"ERROR: Failed to load Pipfile at Pipfile.*\n.*it will be .*",
        ),
        (PipfileNotFound, "Pipfile", r".*Pipfile.*"),
    ],
)
def test_fileexistserror(exc_type, msg, match):
    def raise_exc():
        raise exc_type(msg)

    with pytest.raises(exc_type, match=match):
        raise_exc()
