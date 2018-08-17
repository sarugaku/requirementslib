# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import os
from vistir.compat import Path

from .requirements import Requirement

import plette.lockfiles


class Lockfile(plette.lockfiles.Lockfile):
    @classmethod
    def load(cls, path):
        if not path:
            path = os.curdir
        path = Path(path).absolute()
        if path.is_dir():
            path = path / "Pipfile.lock"
        elif path.name == "Pipfile":
            path = path.parent / "Pipfile.lock"
        if not path.exists():
            raise OSError("Path does not exist: %s" % path)
        return cls.create(path.parent, lockfile_name=path.name)

    @classmethod
    def create(cls, project_path, lockfile_name="Pipfile.lock"):
        """Create a new lockfile instance

        :param project_path: Path to  project root
        :type project_path: str or :class:`~pathlib.Path`
        :returns: List[:class:`~requirementslib.Requirement`] objects
        """

        if not isinstance(project_path, Path):
            project_path = Path(project_path)
        lockfile_path = project_path / lockfile_name
        requirements = []
        dev_requirements = []
        with lockfile_path.open(encoding="utf-8") as f:
            lockfile = super(Lockfile, cls).load(f)
        for k in lockfile["develop"].keys():
            dev_requirements.append(Requirement.from_pipfile(k, lockfile.develop[k]._data))
        for k in lockfile["default"].keys():
            requirements.append(Requirement.from_pipfile(k, lockfile.default[k]._data))
        lockfile.requirements = requirements
        lockfile.dev_requirements = dev_requirements
        lockfile.path = lockfile_path
        return lockfile

    @property
    def dev_requirements_list(self):
        return [r.as_pipfile() for r in self.dev_requirements]

    @property
    def requirements_list(self):
        return [r.as_pipfile() for r in self.requirements]

    def write(self):
        super(Lockfile, self).dump(self.path, encoding="utf-8")

    def as_requirements(self, include_hashes=False, dev=False):
        """Returns a list of requirements in pip-style format"""
        lines = []
        section = self.dev_requirements if dev else self.requirements
        for req in section:
            r = req.as_line()
            if not include_hashes:
                r = r.split("--hash", 1)[0]
            lines.append(r.strip())
        return lines
