# -*- coding=utf-8 -*-
import attr

import six
from .dependencies import AbstractDependency
from .utils import (
    format_requirement,
    version_from_ireq,
)
from ..utils import log


class ResolutionError(Exception):
    pass


@attr.s
class DependencyResolver(object):
    pinned_deps = attr.ib(default=attr.Factory(dict))
    #: A dictionary of abstract dependencies by name
    dep_dict = attr.ib(default=attr.Factory(dict))
    #: A dictionary of sets of version numbers that are valid for a candidate currently
    candidate_dict = attr.ib(default=attr.Factory(dict))
    #: A historical record of pins
    pin_history = attr.ib(default=attr.Factory(dict))

    @property
    def dependencies(self):
        return list(self.dep_dict.values())

    @property
    def resolution(self):
        return list(self.pinned_deps.values())

    def add_abstract_dep(self, dep):
        """Add an abstract dependency by either creating a new entry or
        merging with an old one.

        :param dep: An abstract dependency to add
        :type dep: :class:`~requirementslib.models.dependency.AbstractDependency`
        :raises ResolutionError: Raised when the given dependency is not compatible with
                                 an existing abstract dependency.
        """

        if dep.name in self.dep_dict:
            compatible_versions = self.dep_dict[dep.name].compatible_versions(dep)
            if compatible_versions:
                self.candidate_dict[dep.name] = compatible_versions
                self.dep_dict[dep.name] = self.dep_dict[
                    dep.name
                ].compatible_abstract_dep(dep)
            else:
                raise ResolutionError
        else:
            self.candidate_dict[dep.name] = dep.version_set
            self.dep_dict[dep.name] = dep

    def pin_deps(self):
        """Pins the current abstract dependencies and adds them to the history dict.

        Adds any new dependencies to the abstract dependencies already present by
        merging them together to form new, compatible abstract dependencies.
        """

        for name in list(self.dep_dict.keys()):
            candidates = self.dep_dict[name].candidates[:]
            abs_dep = self.dep_dict[name]
            while candidates:
                pin = candidates.pop()
                new_version = version_from_ireq(pin)
                # Move on from existing pins if the new pin isn't compatible
                if name in self.pinned_deps:
                    old_version = version_from_ireq(self.pinned_deps[name])
                    if (new_version != old_version and
                            new_version not in self.candidate_dict[name]):
                        continue
                pin.parent = abs_dep.parent
                pin_subdeps = self.dep_dict[name].get_deps(pin)
                backup = self.dep_dict.copy(), self.candidate_dict.copy()
                try:
                    for pin_dep in pin_subdeps:
                        self.add_abstract_dep(pin_dep)
                except ResolutionError:
                    self.dep_dict, self.candidate_dict = backup
                    continue
                else:
                    self.pinned_deps[name] = pin
                    break

    def resolve(self, root_nodes, max_rounds=20):
        """Resolves dependencies using a backtracking resolver and multiple endpoints.

        Note: this resolver caches aggressively.
        Runs for *max_rounds* or until any two pinning rounds yield the same outcome.

        :param root_nodes: A list of the root requirements.
        :type root_nodes: list[:class:`~requirementslib.models.requirements.Requirement`]
        :param max_rounds: The max number of resolution rounds, defaults to 20
        :param max_rounds: int, optional
        :raises RuntimeError: Raised when max rounds is exceeded without a resolution.
        """
        if self.dep_dict:
            raise RuntimeError("Do not use the same resolver more than once")

        # Coerce input into AbstractDependency instances.
        # We accept str, Requirement, and AbstractDependency as input.
        for dep in root_nodes:
            if isinstance(dep, six.string_types):
                dep = AbstractDependency.from_string(dep)
            elif not isinstance(dep, AbstractDependency):
                dep = AbstractDependency.from_requirement(dep)
            self.add_abstract_dep(dep)

        for round_ in range(max_rounds):
            self.pin_deps()
            self.pin_history[round_] = self.pinned_deps.copy()

            if round_ > 0:
                previous_round = set(self.pin_history[round_ - 1].values())
                current_values = set(self.pin_history[round_].values())
                difference = current_values - previous_round
            else:
                difference = set(self.pin_history[round_].values())

            log.debug("\n")
            log.debug("{:=^30}".format(" Round {0} ".format(round_)))
            log.debug("\n")
            if difference:
                log.debug("New Packages: ")
                for d in difference:
                    log.debug("{:>30}".format(format_requirement(d)))
            elif round_ >= 3:
                log.debug("Stable Pins: ")
                for d in current_values:
                    log.debug("{:>30}".format(format_requirement(d)))
                return
            else:
                log.debug("No New Packages.")
        # TODO: Raise a better error.
        raise RuntimeError("cannot resolve after {} rounds".format(max_rounds))
