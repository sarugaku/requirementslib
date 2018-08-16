# -*- coding: utf-8 -*-
import os

import attr
import contoml
import toml

from first import first

from vistir.compat import FileNotFoundError, Path

from .._vendor import pipfile
from ..exceptions import RequirementError
from .dependencies import get_finder, get_pip_options
from .requirements import Requirement
from .resolvers import DependencyResolver
from .utils import filter_none, format_requirement, optional_instance_of


@attr.s
class Source(object):
    #: URL to PyPI instance
    url = attr.ib(default="pypi")
    #: If False, skip SSL checks
    verify_ssl = attr.ib(default=True, validator=optional_instance_of(bool))
    #: human name to refer to this source (can be referenced in packages or dev-packages)
    name = attr.ib(default="")

    def get_dict(self):
        return attr.asdict(self)

    @property
    def expanded(self):
        source_dict = attr.asdict(self).copy()
        source_dict["url"] = os.path.expandvars(source_dict.get("url"))
        return source_dict


@attr.s
class Hash(object):
    hash_type = attr.ib(default="sha256")
    value = attr.ib(default=None)

    def get_dict(self):
        return {self.hash_type: self.value}

    def as_line(self):
        return "{0}:{1}".format(self.hash_type, self.value)

    @classmethod
    def parse(cls, value):
        hash_type = 'sha256'
        if ':' in value:
            hash_type, value = value.split(':', 1)
        return cls.create(**{hash_type: value})

    @classmethod
    def create(cls, *args, **kwargs):
        hash_type = next((k for k in kwargs.keys()), None)
        value = kwargs.get(hash_type)
        return cls(hash_type=hash_type, value=value)


@attr.s
class Section(object):
    ALLOWED_NAMES = ("packages", "dev-packages")
    #: Name of the pipfile section
    name = attr.ib(default="packages")
    #: A list of requirements that are contained by the section
    requirements = attr.ib(default=list)

    def get_dict(self):
        _dict = {}
        for req in self.requirements:
            _dict.update(req.as_pipfile())
        return {self.name: _dict}

    @property
    def vcs_requirements(self):
        return [req for req in self.requirements if req.is_vcs]

    @property
    def editable_requirements(self):
        return [req for req in self.requirements if req.editable]


@attr.s
class RequiresSection(object):
    python_version = attr.ib(default=None)
    python_full_version = attr.ib(default=None)

    def get_dict(self):
        requires = attr.asdict(self, filter=filter_none)
        if not requires:
            return {}
        return {"requires": requires}

    def has_value(self):
        if self.python_version or self.python_full_version:
            return True
        return False

    @classmethod
    def create(cls, *args, **kwargs):
        return cls(**kwargs)


@attr.s
class PipenvSection(object):
    allow_prereleases = attr.ib(default=False)

    def get_dict(self):
        if self.allow_prereleases:
            return {"pipenv": attr.asdict(self)}
        return {}


@attr.s
class Pipfile(object):
    #: Path to the pipfile
    path = attr.ib(default=None, converter=Path, validator=optional_instance_of(Path))
    #: Sources listed in the pipfile
    sources = attr.ib(default=attr.Factory(list))
    #: Sections contained by the pipfile
    sections = attr.ib(default=attr.Factory(list))
    #: Scripts found in the pipfile
    scripts = attr.ib(default=attr.Factory(dict))
    #: This section stores information about what python version is required
    requires = attr.ib(default=attr.Factory(RequiresSection))
    #: This section stores information about pipenv such as prerelease requirements
    pipenv = attr.ib(default=attr.Factory(PipenvSection))
    #: This is the sha256 hash of the pipfile (without environment interpolation)
    pipfile_hash = attr.ib()

    @pipfile_hash.default
    def get_hash(self):
        p = pipfile.load(self.path.as_posix(), inject_env=False)
        return p.hash

    @property
    def requires_python(self):
        return self.requires.requires_python

    @property
    def allow_prereleases(self):
        return self.pipenv.allow_prereleases

    def get_sources(self):
        """Return a dictionary with a list of dictionaries of pipfile sources"""
        _dict = {}
        for src in self.sources:
            _dict.update(src.get_dict())
        return {"source": _dict} if _dict else {}

    def get_sections(self):
        """Return a dictionary with both pipfile sections and requirements"""
        _dict = {}
        for section in self.sections:
            _dict.update(section.get_dict())
        return _dict

    def get_pipenv(self):
        pipenv_dict = self.pipenv.get_dict()
        if pipenv_dict:
            return pipenv_dict
        return {}

    def get_requires(self):
        req_dict = self.requires.get_dict()
        return req_dict if req_dict else {}

    def get_dict(self):
        _dict = attr.asdict(self, recurse=False)
        for k in ["path", "pipfile_hash", "sources", "sections", "requires", "pipenv"]:
            if k in _dict:
                _dict.pop(k)
        return _dict

    def build_lockfile(self):
        from .lockfile import Lockfile
        resolved = self.resolve()
        hashes = resolved.get_hashes()
        dev_names = [req.name for req in self.dev_packages.requirements]
        req_names = [req.name for req in self.packages.requirements]
        dev_reqs, reqs = [], []
        for req, pin in resolved.pinned_deps.items():
            parent = None
            _current_dep = resolved.dep_dict[req]
            while True:
                if _current_dep.parent:
                    parent = _current_dep.parent.name
                    _current_dep = _current_dep.parent
                break
            requirement = None
            requirement = Requirement.from_line(format_requirement(pin))
            requirement.hashes = [Hash(value=v) for v in hashes.get(req, [])]
            if req in req_names:
                reqs.append(req)
            elif req in dev_names:
                dev_reqs.append(req)
            # If the requirement in question inherits from a dev requirement we still
            # need to add it to the dev dependencies
            if parent and parent in dev_names and req not in dev_names:
                dev_reqs.append(req)
            # If the requirement in question inherits from a non-dev requirement we
            # will still need to make sure it gets added to the non-dev section
            if parent and parent in req_names and req not in req_names:
                reqs.append(req)

        creation_dict = {
            "path": self.path.parent / 'Pipfile.lock',
            "pipfile_hash": Hash(value=self.get_hash()),
            "sources": [s for s in self.sources],
            "dev_requirements": dev_reqs,
            "requirements": reqs,
        }
        if self.requires.has_value():
            creation_dict['requires'] = self.requires
        lockfile = Lockfile(**creation_dict)
        return lockfile

    def dump(self, to_dict=False):
        """Dumps the pipfile to a toml string
        """

        _dict = self.get_sources()
        _dict.update(self.get_sections())
        _dict.update(self.get_dict())
        _dict.update(self.get_pipenv())
        _dict.update(self.get_requires())
        if to_dict:
            return _dict
        return contoml.dumps(_dict)

    @classmethod
    def load(cls, path):
        if not isinstance(path, Path):
            path = Path(path)
        pipfile_path = path / "Pipfile"
        if not path.exists():
            raise FileNotFoundError("%s is not a valid project path!" % path)
        elif not pipfile_path.exists() or not pipfile_path.is_file():
            raise RequirementError("%s is not a valid Pipfile" % pipfile_path)
        pipfile_dict = toml.load(pipfile_path.as_posix())
        sections = [cls.get_section(pipfile_dict, s) for s in Section.ALLOWED_NAMES]
        pipenv = pipfile_dict.get("pipenv", {})
        requires = pipfile_dict.get("requires", {})
        creation_dict = {
            "path": pipfile_path,
            "sources": [Source(**src) for src in pipfile_dict.get("source", [])],
            "sections": sections,
            "scripts": pipfile_dict.get("scripts"),
        }
        if requires:
            creation_dict["requires"] = RequiresSection(**requires)
        if pipenv:
            creation_dict["pipenv"] = PipenvSection(**pipenv)
        return cls(**creation_dict)

    def resolve(self):
        option_sources = [s.expanded for s in self.sources]
        pip_args = []
        if self.pipenv.allow_prereleases:
            pip_args.append('--pre')
        pip_options = get_pip_options(pip_args, sources=option_sources)
        finder = get_finder(sources=option_sources, pip_options=pip_options)
        resolver = DependencyResolver.create(finder=finder, allow_prereleases=self.pipenv.allow_prereleases)
        pkg_dict = {}
        for pkg in self.dev_packages.requirements + self.packages.requirements:
            pkg_dict[pkg.name] = pkg
        resolver.resolve(list(pkg_dict.values()))
        return resolver

    @property
    def dev_packages(self):
        return first(s for s in self.sections if s.name == "dev-packages")

    @property
    def packages(self):
        return first(s for s in self.sections if s.name == "packages")

    @staticmethod
    def get_section(pf_dict, section):
        """Get section objects from a pipfile dictionary

        :param pf_dict: A toml loaded pipfile dictionary
        :type pf_dict: dict
        :returns: Section objects
        """
        sect = pf_dict.get(section)
        requirements = []
        if section not in Section.ALLOWED_NAMES:
            raise ValueError("Not a valid pipfile section name: %s" % section)
        for name, pf_entry in sect.items():
            requirements.append(Requirement.from_pipfile(name, pf_entry))
        return Section(name=section, requirements=requirements)
