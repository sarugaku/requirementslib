# -*- coding: utf-8 -*-
from __future__ import absolute_import
import attr
import json
import os
import six
from .requirements import Requirement
from .pipfile import Source, Hash, RequiresSection
from .utils import optional_instance_of
from ..utils import atomic_open_for_write
from .._compat import Path, FileNotFoundError


DEFAULT_NEWLINES = u"\n"


def preferred_newlines(f):
    if isinstance(f.newlines, six.text_type):
        return f.newlines
    return DEFAULT_NEWLINES


class _LockFileEncoder(json.JSONEncoder):
    """A specilized JSON encoder to convert loaded TOML data into a lock file.

    This adds a few characteristics to the encoder:

    * The JSON is always prettified with indents and spaces.
    * PrettyTOML's container elements are seamlessly encodable.
    * The output is always UTF-8-encoded text, never binary, even on Python 2.
    """

    def __init__(self, newlines=None):
        self.newlines = DEFAULT_NEWLINES if not newlines else newlines
        super(_LockFileEncoder, self).__init__(
            indent=4, separators=(",", ": "), sort_keys=True
        )

    def default(self, obj):
        from prettytoml.elements.common import ContainerElement, TokenElement

        if isinstance(obj, (ContainerElement, TokenElement)):
            return obj.primitive_value
        return super(_LockFileEncoder, self).default(obj)

    def encode(self, obj):
        content = super(_LockFileEncoder, self).encode(obj)
        if not isinstance(content, six.text_type):
            content = content.decode("utf-8")
        return content


@attr.s
class Lockfile(object):
    dev_requirements = attr.ib(default=attr.Factory(list))
    requirements = attr.ib(default=attr.Factory(list))
    sources = attr.ib(default=attr.Factory(list))
    path = attr.ib(default=None, validator=optional_instance_of(Path))
    pipfile_hash = attr.ib(default=None, validator=optional_instance_of(Hash))
    encoder = attr.ib(default=None, validator=optional_instance_of(_LockFileEncoder))
    pipfile_spec = attr.ib(default=6, converter=int)
    requires = attr.ib(default=None, validator=optional_instance_of(RequiresSection))

    @classmethod
    def load(cls, path=None):
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
        sources = []
        pipfile_hash = None
        if not lockfile_path.exists():
            raise FileNotFoundError("No such lockfile: %s" % lockfile_path)

        with lockfile_path.open(encoding="utf-8") as f:
            lockfile = json.load(f)
            encoder = _LockFileEncoder(newlines=preferred_newlines(f))
        for k in lockfile["develop"].keys():
            dev_requirements.append(Requirement.from_pipfile(k, lockfile["develop"][k]))
        for k in lockfile["default"].keys():
            requirements.append(Requirement.from_pipfile(k, lockfile["default"][k]))
        meta = lockfile["_meta"]
        pipfile_hash = Hash.create(**meta.get("hash")) if "hash" in meta else None
        pipfile_spec = meta.get("pipfile-spec", 6)
        requires = None
        if "requires" in meta:
            requires = RequiresSection.create(**meta.get("requires"))
        for source in meta.get("sources", []):
            sources.append(
                Source(
                    url=source.get("url"),
                    verify_ssl=source.get("verify_ssl", True),
                    name=source.get("name"),
                )
            )

        return cls(
            path=lockfile_path,
            requirements=requirements,
            dev_requirements=dev_requirements,
            encoder=encoder,
            sources=sources,
            pipfile_hash=pipfile_hash,
            pipfile_spec=pipfile_spec,
            requires=requires,
        )

    @property
    def dev_requirements_list(self):
        return [r.as_pipfile() for r in self.dev_requirements]

    @property
    def requirements_list(self):
        return [r.as_pipfile() for r in self.requirements]

    @property
    def meta(self):
        return_dict = {"pipfile-spec": self.pipfile_spec}
        if self.sources:
            return_dict["sources"] = [s.get_dict() for s in self.sources]
        if self.pipfile_hash:
            return_dict["hash"] = self.pipfile_hash.get_dict()
        if self.requires:
            return_dict["requires"] = self.requires.get_dict()
        return return_dict

    def as_dict(self):
        return_dict = {
            "_meta": self.meta,
            "develop": {
                pkg: entry
                for req in self.dev_requirements_list
                for pkg, entry in req.items
            },
            "default": {
                pkg: entry for req in self.requirements_list for pkg, entry in req.items
            },
        }
        return return_dict

    def write(self):
        if not self.encoder:
            self.encoder = _LockFileEncoder(newlines=DEFAULT_NEWLINES)
        s = self.encoder.encode(self.as_dict())
        open_kwargs = {"newline": self.encoder.newlines, "encoding": "utf-8"}
        with atomic_open_for_write(self.lockfile_path.as_posix(), **open_kwargs) as f:
            f.write(s)
            # Write newline at end of document. GH-319.
            # Only need '\n' here; the file object handles the rest.
            if not s.endswith(u"\n"):
                f.write(u"\n")

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
