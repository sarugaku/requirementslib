Requirementslib 2.1.0 (2022-10-08)
==================================


No significant changes.


Requirementslib 2.1.0 (2022-10-08)
==================================


Features
--------

- Support for named package categories in Pipfile and Pipfile.lock beyond the default and develop categories.  `#345 <https://github.com/sarugaku/requirementslib/issues/345>`_


Requirementslib 2.0.3 (2022-09-24)
==================================


Bug Fixes
---------

- Fix non-deterministic markers by removing ``lru_cache`` usage from ``markers.py``.  `#344 <https://github.com/sarugaku/requirementslib/issues/344>`_


Requirementslib 2.0.2 (2022-09-14)
==================================


Bug Fixes
---------

- Rely on ``packaging`` and ``pkg_resources`` internal to ``pip``.  `#343 <https://github.com/sarugaku/requirementslib/issues/343>`_


Requirementslib 2.0.1 (2022-08-29)
==================================


Bug Fixes
---------

- Fix bug with local file installs that are not marked ``editable = "true"`` getting an unexpected ``#egg`` fragment.  `#342 <https://github.com/sarugaku/requirementslib/issues/342>`_


Requirementslib 2.0.0 (2022-08-24)
==================================


Features
--------

- ``requirementslib`` has converted off of pip-shims project which had grown into a complicated interface to using ``pip``.
  It was problematic because ``pip-shims`` could never foresee and accommodate future looking changes to internal interfaces of ``pip``.
  Also, ``pip-shims`` slowed down this library and required downstream tools such as ``pipenv`` to continue vendoring it despite having already dropped usages.
  Due to the impact of this change, it requires a major version increase of ``requirementslib`` to ``2.0.0``
  To utilize version ``2.0.0`` of ``requirementslib``, ensure you have ``pip>=22.2`` as this has not been fully tested to support earlier versions of ``pip``
  Breakage of the internal ``pip`` interface usage is possible with earlier versions.
  Additionally, the interface on ``NamedRequierment`` renamed class method ``get_dependencies`` to ``dependencies`` and ``get_abstract_dependencies`` to ``abstract_dependencies`` in order to match interface with ``Line`` class and avoid naming collision with the utility methods they call.  `#334 <https://github.com/sarugaku/requirementslib/issues/334>`_
  

Bug Fixes
---------

- ``requirementslib`` adjusted code paths to prevent import of ``setuptools`` that causes issues when upgrading ``setuptools``.  `#339 <https://github.com/sarugaku/requirementslib/issues/339>`_


Requirementslib 1.6.9 (2022-07-27)
==================================


Bug Fixes
---------

- Rewrite imports of ``pip_shims.shims`` to be ``from pip_shims import shims`` so that they can be rewritten by the vendoring scripts in ``pipenv``.  `#332 <https://github.com/sarugaku/requirementslib/issues/332>`_


Requirementslib 1.6.8 (2022-07-22)
==================================


Bug Fixes
---------

- Resolved an issue introduced in 1.6.5 that failed to parse refs in VCS uris  `#330 <https://github.com/sarugaku/requirementslib/issues/330>`_


Requirementslib 1.6.7 (2022-07-07)
==================================


Bug Fixes
---------

- Fix tracebacks on encountering Annotated variables  `#307 <https://github.com/sarugaku/requirementslib/issues/307>`_
  
- Change style of ``packaging`` imports for downstream ``pipenv`` to be able to patch this more easily.  `#324 <https://github.com/sarugaku/requirementslib/issues/324>`_


Requirementslib 1.6.6 (2022-06-29)
==================================


Bug Fixes
---------

- Fix boolean logical bug whereby a name may have already been supplied to ``Line.parse_name`` but it was sometimes recomputed incorrectly.  `#319 <https://github.com/sarugaku/requirementslib/issues/319>`_
  
- In order to fix the requirementslib build and compatibility with ``pip==22.1`` this change adds a file
  ``requirementslib.models.old_pip_utils`` to maintain the prior version of ``unpack_url`` as ``old_unpack_url``
  that was dropped from ``pip==22.1``.  `#321 <https://github.com/sarugaku/requirementslib/issues/321>`_


Requirementslib 1.6.5 (2022-06-27)
==================================


Bug Fixes
---------

- Fix an issue for projects with an at sign (``@``) in the path  `#309 <https://github.com/sarugaku/requirementslib/issues/309>`_

- Resolved issue where a beta python version in the python_version marker would cause an error.  `#317 <https://github.com/sarugaku/requirementslib/issues/317>`_


Removals and Deprecations
-------------------------

- Fix deprecation warning for `setuptools.config.read_configuration` when using `setuptools >= v61.0.0`  `#315 <https://github.com/sarugaku/requirementslib/issues/315>`_


Requirementslib 1.6.4 (2022-04-24)
==================================


No significant changes.


Requirementslib 1.6.3 (2022-04-18)
==================================


Bug Fixes
---------

- Fixed bug introduced in `requirementslib==1.6.2` where the pyproject.toml would always be deleted after use.  `#313 <https://github.com/sarugaku/requirementslib/issues/313>`_


Requirementslib 1.6.2 (2022-04-18)
==================================


Features
--------

- Updates to support `pip==22.*` and pass in required verbosity argument to ``VcsSupport.obtain``.
  Pin ``pyparsing<3.0.0`` in order to prevent failure with parsing certain system markers.  `#308 <https://github.com/sarugaku/requirementslib/issues/308>`_


Bug Fixes
---------

- Handle edge case of installing from url with fragment containing a subdirectory as the location to the package.  `#312 <https://github.com/sarugaku/requirementslib/issues/312>`_


Removals and Deprecations
-------------------------

- Officially drop support for Python 3.6.  `#308 <https://github.com/sarugaku/requirementslib/issues/308>`_


Requirementslib 1.6.1 (2021-11-04)
==================================


Features
--------

- Simplify the ast parsing so that it will give up to building the metadata when it's unable to parse.  `#268 <https://github.com/sarugaku/requirementslib/issues/268>`_


Requirementslib 1.6.0 (2021-11-03)
==================================


Features
--------

- Switch from ``appdirs`` to ``platformdirs``.  `#295 <https://github.com/sarugaku/requirementslib/issues/295>`_


Bug Fixes
---------

- Fix an AST parse error on Python 3.9+.  `#288 <https://github.com/sarugaku/requirementslib/issues/288>`_

- Replace ``chardet`` with ``charset_normalizer``.  `#296 <https://github.com/sarugaku/requirementslib/issues/296>`_

- Fix the initialization of ``pep517.HookCaller``.  `#299 <https://github.com/sarugaku/requirementslib/issues/299>`_


Removals and Deprecations
-------------------------

- Officially drop support for Python 2.7 and 3.5.  `#301 <https://github.com/sarugaku/requirementslib/issues/301>`_


1.5.16 (2020-11-12)
===================

Features
--------

- Expand env vars in the URL of requirements.  `#276 <https://github.com/sarugaku/requirementslib/issues/276>`_


Removals and Deprecations
-------------------------

- Replace the deprecated arguments of ``attrs`` with recommended ones.  `#271 <https://github.com/sarugaku/requirementslib/issues/271>`_


1.5.15 (2020-11-04)
===================

Bug Fixes
---------

- Fix a bug that file URLs will be incorrectly unquoted during parsing.  `#274 <https://github.com/sarugaku/requirementslib/issues/274>`_


1.5.14 (2020-10-29)
===================

Bug Fixes
---------

- Fix the PEP 517 requires in default ``pyproject.toml`` and clean the temp files.  `#262 <https://github.com/sarugaku/requirementslib/issues/262>`_

- Fix an unparse error that the dictionary keys are unhashable.  `#266 <https://github.com/sarugaku/requirementslib/issues/266>`_

- Fix a bug that dist-info inside ``venv`` directory will be mistaken as the editable package's metadata.  `#273 <https://github.com/sarugaku/requirementslib/issues/273>`_


1.5.13 (2020-08-12)
===================

Bug Fixes
---------

- Don't copy whole tree for local directory dependencies.  `#259 <https://github.com/sarugaku/requirementslib/issues/259>`_


1.5.12 (2020-07-10)
===================

Bug Fixes
---------

- Fix a bug that assignments with type annotations are missing from the AST.  `#253 <https://github.com/sarugaku/requirementslib/issues/253>`_

- Fix a bug that ``package_dir`` points to a wrong location when parsing ``setup.cfg``.  `#255 <https://github.com/sarugaku/requirementslib/issues/255>`_


1.5.11 (2020-06-01)
===================

Bug Fixes
---------

- Packages which use a function call in ``setup.py`` to find their own name dynamically will now successfully resolve.  `#251 <https://github.com/sarugaku/requirementslib/issues/251>`_


1.5.10 (2020-06-01)
===================

Bug Fixes
---------

- Switch to BFS algorithm to iterate possible metadata directories.  `#186 <https://github.com/sarugaku/requirementslib/issues/186>`_

- Fix a bug that `+` character in URL auth are converted to a space.  `#244 <https://github.com/sarugaku/requirementslib/issues/244>`_

- Fixed an issue in the AST parser which caused failures when parsing ``setup.py`` files with assignments (e.g. ``variable = some_value``) to the same name more than once, followed by operations on those variables (e.g. ``new_value = variable + other_variable``).  `#246 <https://github.com/sarugaku/requirementslib/issues/246>`_

- Copy symlinks as well for local path requirements.  `#248 <https://github.com/sarugaku/requirementslib/issues/248>`_

- Fix a bug that non-string value for name argument will be taken as requirement name.  `#249 <https://github.com/sarugaku/requirementslib/issues/249>`_


1.5.9 (2020-05-19)
==================

Bug Fixes
---------

- Subdirectory fragments on VCS URLs which also contain ``#egg=`` fragments will now be included correctly in requirements.  `#236 <https://github.com/sarugaku/requirementslib/issues/236>`_

- Fixed a regression which caused collisions to occur between valid named requirements and invalid local filesystem paths.  `#239 <https://github.com/sarugaku/requirementslib/issues/239>`_

- Fixed a bug in ``setup.py`` parsing in which ``setup.py`` files which passed a dictionary to the ``setup`` function returned metadata that could not be meaningfully processed.  `#241 <https://github.com/sarugaku/requirementslib/issues/241>`_


1.5.8 (2020-05-14)
==================

Bug Fixes
---------

- Fix an issue where the list of not-supported python versions in a marker was being truncated.  `#228 <https://github.com/sarugaku/requirementslib/issues/228>`_

- Fixed a bug which prevented the use of ``wheel_cache`` instances from ``pip`` due to deprecated invocation.  `#230 <https://github.com/sarugaku/requirementslib/issues/230>`_

- ``Requirementslib`` will now ensure that ``PEP508`` style direct URL lines are preserved as being direct URL references when converting to and from ``Requirementslib.requirement`` instances.  `#232 <https://github.com/sarugaku/requirementslib/issues/232>`_

- Fix a bug that ``1.x`` specifiers can't be parsed correctly.  `#234 <https://github.com/sarugaku/requirementslib/issues/234>`_


1.5.7 (2020-04-23)
==================

Bug Fixes
---------

- Fixed a bug in ``AST`` parsing on python 2.7 which caused the parser to fail if any attributes could not be resolved.  `#226 <https://github.com/sarugaku/requirementslib/issues/226>`_


1.5.6 (2020-04-22)
==================

Features
--------

- Added ``requirementslib.models.metadata`` module with ``get_package``, ``get_package_version``, and ``get_package_from_requirement`` interfaces.  `#219 <https://github.com/sarugaku/requirementslib/issues/219>`_


Bug Fixes
---------

- Fixed an issue in parsing setup files that incorrectly parsed the ``in`` operator and failed to properly expand referenced dictionaries.  `#222 <https://github.com/sarugaku/requirementslib/issues/222>`_

- Fixed an issue that did not take into account micro versions when generating markers from ``python_requires``.  `#223 <https://github.com/sarugaku/requirementslib/issues/223>`_


1.5.5 (2020-03-31)
==================

Bug Fixes
---------

- Fixed an issue which prevented parsing of ``setup.cfg`` files using the ``setuptools`` native configuration reader.  `#216 <https://github.com/sarugaku/requirementslib/issues/216>`_

- URI instances will no longer print masked username fields when neither a username or password is supplied.  `#220 <https://github.com/sarugaku/requirementslib/issues/220>`_


1.5.4 (2020-03-25)
==================

Features
--------

- Added support for hiding tokens from URLs when printing them to the screen.  `#192 <https://github.com/sarugaku/requirementslib/issues/192>`_


Bug Fixes
---------

- Fix AST parsing when ``setup.py`` contains binary operators other than ``+`` and ``-``.  `#179 <https://github.com/sarugaku/requirementslib/issues/179>`_

- Fix test failures due to updates to the ``pyparsing`` API.  `#181 <https://github.com/sarugaku/requirementslib/issues/181>`_

- Fixed an issue with loading ``Pipfile`` data due to ``plette`` model misalignment.  `#182 <https://github.com/sarugaku/requirementslib/issues/182>`_

- Fixed failed calls to ``.lower`` on ``tomlkit``'s ``Bool`` object during pipfile load as the API seems to have changed here.  `#183 <https://github.com/sarugaku/requirementslib/issues/183>`_

- Added import guards to prevent ``ImportErrors`` which could occur when attempting to import now-removed ``pkg_resources.extern.requirements``.  `#185 <https://github.com/sarugaku/requirementslib/issues/185>`_

- Fixed an issue which prevented loading ``Lockfile``-based references to local paths when calling ``as_requirements()`` on a ``requirementslib.models.lockfile.Lockfile`` instance.  `#188 <https://github.com/sarugaku/requirementslib/issues/188>`_

- Updated references to ``Link`` instances which no longer have the ``is_artifact`` property.  `#190 <https://github.com/sarugaku/requirementslib/issues/190>`_

- Updated all references to newly shimmed code to fix breakages due to ``pip 19.3`` release:
  - Fixed references to ``Command`` object from ``pip`` in favor of ``InstallCommand`` which is now properly shimmed via ``pip-shims``
  - Fixed invocation of ``VcsSupport`` and ``VersionControl`` objects for compatibility
  - Removed addition of options to ``Command`` as they are redundant when using ``InstallCommand``
  - Cut ``get_finder`` and ``start_resolver`` over to newly shimmed approaches in ``pip-shims``  `#191 <https://github.com/sarugaku/requirementslib/issues/191>`_

- Fixed a bug in parsing of ``Pipfiles`` with missing or misnamed ``source`` sections which could cause ``tomlkit`` errors when loading legacy ``Pipfiles``.  `#194 <https://github.com/sarugaku/requirementslib/issues/194>`_

- Corrected an unexpected behavior which resulted in a ``KeyError`` when attempting to call ``__getitem__`` on a ``Pipfile`` instance with a section that was not present.  `#195 <https://github.com/sarugaku/requirementslib/issues/195>`_

- Fixed an issue in ``Lockfile`` path and model auto-detection when called without the ``load`` classmethod which caused initialization to fail due to an ``AttributeError``.  `#196 <https://github.com/sarugaku/requirementslib/issues/196>`_

- Fixed an issue which caused build directories to be deleted before dependencies could be determined for editable source reqiurements.  `#200 <https://github.com/sarugaku/requirementslib/issues/200>`_

- Fixed a bug which could cause parsing to fail for ``setup.cfg`` files on python 2.  `#202 <https://github.com/sarugaku/requirementslib/issues/202>`_

- Fixed an issue in binary operator mapping in the ``ast_parse_setup_py`` functionality of the dependency parser which could cause dependency resolution to fail.  `#204 <https://github.com/sarugaku/requirementslib/issues/204>`_

- Fixed an issue which prevented successful parsing of ``setup.py`` files which were not ``utf-8`` encoded.  `#205 <https://github.com/sarugaku/requirementslib/issues/205>`_

- Fixed an issue which caused mappings of binary operators to fail to evaluate when parsing ``setup.py`` files.  `#206 <https://github.com/sarugaku/requirementslib/issues/206>`_

- Fixed mapping and evaluation of boolean operators and comparisons when evaluating ``setup.py`` files with AST parser to discover dependencies.  `#207 <https://github.com/sarugaku/requirementslib/issues/207>`_


1.5.3 (2019-07-09)
==================

Features
--------

- Added support for parsing lists of variables as extras in `setup.py` files via ``ast.BinOp`` traversal.  `#177 <https://github.com/sarugaku/requirementslib/issues/177>`_


Bug Fixes
---------

- Fixed quoting of markers when formatting requirements as pip-compatible lines.  `#173 <https://github.com/sarugaku/requirementslib/issues/173>`_

- Quotes surrounding requirement lines will now be stripped only if matching pairs are found to ensure requirements can be parsed correctly.  `#176 <https://github.com/sarugaku/requirementslib/issues/176>`_


1.5.2 (2019-06-25)
==================

Bug Fixes
---------

- Added support to the AST parser for discovering non-standard invocations of ``setup`` in ``setup.py``, e.g. using the fully qualified function name.  `#163 <https://github.com/sarugaku/requirementslib/issues/163>`_

- Fixed an issue which caused dynamic references in ``setup.cfg`` to fail when ``package_dir`` was specified in ``setup.py``.  `#165 <https://github.com/sarugaku/requirementslib/issues/165>`_

- Fixed handling of ``@``-signs in  ``file:`` URLs, unbreaking the use of local packages in e.g. `Jenkins <https://jenkins.io>`_ workspaces.  `#168 <https://github.com/sarugaku/requirementslib/issues/168>`_

- Fixed occasional recursion error when parsing function references using AST parser on ``setup.py`` files.  `#169 <https://github.com/sarugaku/requirementslib/issues/169>`_

- Fixed an intermittent issue caused by the use of ``lru_cache`` on a helper function in the translation of markers.  `#171 <https://github.com/sarugaku/requirementslib/issues/171>`_

- Added enhanced ``get_line()`` functionality to ``Line`` objects and expanded test coverage to incorporate hypothesis.  `#174 <https://github.com/sarugaku/requirementslib/issues/174>`_,
  `#77 <https://github.com/sarugaku/requirementslib/issues/77>`_


1.5.1 (2019-05-19)
==================

Bug Fixes
---------

- Fixed a bug which caused local dependencies to incorrectly return ``wheel`` as their name.  `#158 <https://github.com/sarugaku/requirementslib/issues/158>`_

- Wheels which are successfully built but which contain no valid metadata will now correctly be skipped over during requirements parsing in favor of sdists.  `#160 <https://github.com/sarugaku/requirementslib/issues/160>`_


1.5.0 (2019-05-15)
==================

Features
--------

- Implemented an AST parser for ``setup.py`` for parsing package names, dependencies, and version information if available.  `#106 <https://github.com/sarugaku/requirementslib/issues/106>`_

- Fully implement marker merging and consolidation logic using ``requirement.merge_markers(markers)``.  `#153 <https://github.com/sarugaku/requirementslib/issues/153>`_


Bug Fixes
---------

- Updated ``attrs`` dependency to constraint ``>=18.2``.  `#142 <https://github.com/sarugaku/requirementslib/issues/142>`_

- Fixed a bug which forced early querying for dependencies via pypi or other indexes just by simply creating a ``Requirement`` instance.
  - Added the ability to skip tests requiring internet by setting ``REQUIREMENTSLIB_SKIP_INTERNET_TESTS``.  `#145 <https://github.com/sarugaku/requirementslib/issues/145>`_

- Egg fragments on ``PEP-508`` style direct URL dependencies are now disregarded rather than merged with the leading name.  `#146 <https://github.com/sarugaku/requirementslib/issues/146>`_

- Fixed a bug which prevented the successful loading of pipfiles using ``Pipfile.load``.  `#148 <https://github.com/sarugaku/requirementslib/issues/148>`_

- Fixed a bug which prevented handling special setup.cfg directives during dependency parsing.  `#150 <https://github.com/sarugaku/requirementslib/issues/150>`_

- Fixed an issue which caused the merging of markers to inadvertently use ``or`` to merge even different variables.  `#153 <https://github.com/sarugaku/requirementslib/issues/153>`_


1.4.2 (2019-03-04)
==================

Bug Fixes
---------

- Fixed a bug which prevented successful parsing of VCS urls with dashes.  `#138 <https://github.com/sarugaku/requirementslib/issues/138>`_

- Fixed a bug which caused significant degradation in performance while loading requirements.  `#140 <https://github.com/sarugaku/requirementslib/issues/140>`_


1.4.1 (2019-03-03)
==================

Features
--------

- Added full support for parsing PEP-508 compliant direct URL dependencies.

  Fully implemented pep517 dependency mapping for VCS, URL, and file-type requirements.

  Expanded type-checking coverage.  `#108 <https://github.com/sarugaku/requirementslib/issues/108>`_


Bug Fixes
---------

- Fixed a parsing  bug which incorrectly represented local VCS uris with progressively fewer forward slashes in the ``scheme``, causing dependency resolution to fail.  `#135 <https://github.com/sarugaku/requirementslib/issues/135>`_


1.4.0 (2019-01-21)
==================

Features
--------

- Added ``is_pep517`` and ``build_backend`` properties to the top level ``Requirement`` object to help determine how to build the requirement.  #125


Bug Fixes
---------

- Suppressed output written to ``stdout`` by pip during clones of repositories to non-base branches.  #124

- Fixed a bug which caused local file and VCS requirements to be discovered in a depth-first, inexact search, which sometimes caused incorrect matches to be returned.  #128

- Fixed a bug with link generation on VCS requirements without URI schemes.  #132

- ``VCSRequirement.get_checkout_dir`` will now properly respect the ``src_dir`` argument.  #133


1.3.3 (2018-11-22)
==================

Bug Fixes
---------

- Fixed a bug which caused runtime monkeypatching of plette validation to fail.  #120


1.3.2 (2018-11-22)
==================

Features
--------

- Enhanced parsing of dependency and extras detail from ``setup.cfg`` files.  #118


Bug Fixes
---------

- Take the path passed in if it's valid when loading or creating the lockfile/pipfile.  #114

- Don't write redundant ``egg-info`` under project root when ``src`` is used as package base.  #115

- Fixed an issue which prevented parsing of extras and dependency information from local ``setup.py`` files and could cause irrecoverable errors.  #116


1.3.1 (2018-11-13)
==================

Bug Fixes
---------

- Fixed a bug with parsing branch names which contain slashes.  #112


1.3.0 (2018-11-12)
==================

Features
--------

- Added support for loading metadata from ``pyproject.toml``.  #102

- Local and remote archive ``FileRequirements`` will now be unpacked to a temporary directory for parsing.  #103

- Dependency information will now be parsed from local paths, including locally unpacked archives, via ``setup.py egg_info`` execution.  #104

- Additional metadata will now be gathered for ``Requirement`` objects which contain a ``setup.cfg`` on their base path.  #105

- Requirement names will now be harvested from all available sources, including from ``setup.py`` execution, ``setup.cfg`` files, and any metadata provided as input.  #107

- Added a flag for PEP508 style direct url requirements.  #99


Bug Fixes
---------

- Fixed a bug with ``Pipfile.load()`` which caused a false ``ValidationError`` to raise when parsing a valid ``Pipfile``.  #110


1.2.5 (2018-11-04)
==================

Features
--------

- Restructured library imports to improve performance.  #95


1.2.4 (2018-11-02)
==================

Bug Fixes
---------

- Fixed an issue which caused failures when determining the path to ``setup.py`` files.  #93


1.2.3 (2018-10-30)
==================

Bug Fixes
---------

- Fixed a bug which prevented installation of editable vcs requirements with subdirectory specifiers.  #91


1.2.2 (2018-10-29)
==================

Bug Fixes
---------

- Fixed a bug which prevented mercurial repositories from acquiring commit hashes successfully.  #89


1.2.1 (2018-10-26)
==================

Bug Fixes
---------

- Fixed an issue which caused accidental leakage of open ``requests.session`` instances.  #87


1.2.0 (2018-10-24)
==================

Features
--------

- ``Pipfile`` and ``Lockfile`` models will now properly perform import and export operations with fully data serialization.  #83

- Added a new interface for merging ``dev`` and ``default`` sections in both ``Pipfile`` and ``Lockfile`` objects using ``get_deps(dev=True, only=False)``.  #85


Bug Fixes
---------

- ``Requirement.as_line()`` now provides an argument to make the inclusion of markers optional by passing ``include_markers=False``.  #82

- ``Pipfile`` and ``Lockfile`` models are now able to successfully perform creation operations on projects which currently do not have existing files if supplied ``create=True``.  #84


1.1.9 (2018-10-10)
==================

Bug Fixes
---------

- Fixed a bug in named requirement normalization which caused querying the index to fail when looking up requirements with dots in their names.  #79


1.1.8 (2018-10-08)
==================

Bug Fixes
---------

- Fixed a bug which caused VCS URIs to build incorrectly when calling ``VCSRequirement.as_line()`` in some cases.  #73

- Fixed bug that editable package with ref by @ is not supported correctly  #74


1.1.7 (2018-10-06)
==================

Bug Fixes
---------

- Add space before environment markers ; to make editable packages can be installed by pip  #70


1.1.6 (2018-09-04)
==================

Features
--------

- ``Requirement.get_commit_hash`` and ``Requirement.update_repo`` will no longer clone local repositories to temporary directories or local src directories in order to determine commit hashes.  #60

- Added ``Requirement.lock_vcs_ref()`` api for locking the VCS commit hash to the current commit (and obtaining it and determining it if necessary).  #64

- ``Requirement.as_line()`` now offers the parameter ``as_list`` to return requirements more suited for passing directly to ``subprocess.run`` and ``subprocess.Popen`` calls.  #67


Bug Fixes
---------

- Fixed a bug error formatting of the path validator method of local requirements.  #57

- Fixed an issue which prevented successful loads of ``Pipfile`` objects missing entries in some sections.  #59

- Fixed an issue which caused ``Requirement.get_commit_hash()`` to fail for local requirements.  #67


1.1.5 (2018-08-26)
==================

Bug Fixes
---------

- Fixed an issue which caused local file uri based VCS requirements to fail when parsed from the ``Pipfile`` format.  #53


1.1.4 (2018-08-26)
==================

Features
--------

- Improved ``Pipfile.lock`` loading time by lazily loading requirements in favor of quicker access to metadata and text.  #51


1.1.3 (2018-08-25)
==================

Bug Fixes
---------

- Fixed a bug which caused wheel requirements to include specifiers in ``Requirement.as_line()`` output, preventing installation when passing this output to pip.  #49


1.1.2 (2018-08-25)
==================

Features
--------

- Allow locking of specific vcs references using a new api: ``Requirement.req.get_commit_hash()`` and ``Requirement.commit_hash`` and updates via ``Requirement.req.update_repo()``.  #47


1.1.1 (2018-08-20)
==================

Bug Fixes
---------

- Fixed a bug which sometimes caused extras to be dropped when parsing named requirements using constraint-style specifiers.  #44

- Fix parsing error in `Requirement.as_ireq()` if requirement contains hashes.  #45


1.1.0 (2018-08-19)
==================

Features
--------

- Added support for ``Requirement.get_dependencies()`` to return unpinned dependencies.
- Implemented full support for both parsing and writing lockfiles.
- Introduced lazy imports to enhance runtime performance.
- Switch to ``packaging.canonicalize_name()`` instead of custom canonicalization function.
- Added ``Requirement.copy()`` to the api to copy a requirement.  #33

- Add pep423 formatting to package names when generating ``as_line()`` output.
- Sort extras when building lines.
- Improve local editable requirement name resolution.  #36


Bug Fixes
---------

- Fixed a bug which prevented dependency resolution using pip >= 18.0.

- Fix pipfile parser bug which mishandled missing ``requires`` section.  #33

- Fixed a bug which caused extras to be excluded from VCS urls generated from pipfiles.  #41


Vendored Libraries
------------------

- Unvendored ``pipfile`` in favor of ``plette``.  #33


Removals and Deprecations
-------------------------

- Unvendored ``pipfile`` in favor of ``plette``.  #33

- Moved pipfile and lockfile models to ``plette`` and added api wrappers for compatibility.  #43


1.0.11 (2018-07-20)
===================

Bug Fixes
---------

- If a package is stored on a network share drive, we now resolve it in a way that gets the correct relative path (#29)
- Properly handle malformed urls and avoid referencing unbound variables. (#32)


1.0.10 (2018-07-11)
===================

Bug Fixes
---------

- Fixed a bug which prevented the inclusion of all markers when parsing requirements from existing pipfile entries.  `pypa/pipenv#2520 <https://github.com/pypa/pipenv/issues/2520>`_ (#26)
- requirementslib will now correctly handle subdirectory fragments on output and input for both pipfile and pip-style requirements. (#27)


1.0.9 (2018-06-30)
==================

Features
--------

- Move slow imports to improve import times. (#23)

Bug Fixes
---------

- Use ``hostname`` instead of ``netloc`` to format urls to avoid dropping usernames when they are included. (#22)


1.0.8 (2018-06-27)
==================

Bug Fixes
---------

- Requirementslib will no longer incorrectly write absolute paths or uris where relative paths were provided as inputs.
- Fixed a bug with formatting VCS requirements when translating implicit SSH URIs to ssh URLs. (#20)


1.0.7 (2018-06-27)
==================

Bug Fixes
---------

- Fixed an issue with resolving certain packages which imported and executed other libraries (such as ``versioneer``) during ``setup.py`` execution. (#18)


1.0.6 (2018-06-25)
==================

Bug Fixes
---------

- Fixed a quotation error when passing markers to ``Requirement.constraint_line`` and ``Requirement.markers_as_pip``. (#17)


1.0.5 (2018-06-24)
==================

Features
--------

- Cleaned up relative path conversions to ensure they are always handled in
  posix style. (#15)


1.0.4 (2018-06-24)
==================

Bug Fixes
---------

- Fixed a bug which caused converting relative paths to return ``None``. (#14)


1.0.3 (2018-06-23)
==================

Bug Fixes
---------

- Fixed a bug which caused the base relative path to be listed as ``./.``
  instead of ``.``. (#12)
- Fixed a bug that caused egg fragments to be added to
  ``Requirement.as_line()`` output for file requirements. (#13)


1.0.2 (2018-06-22)
==================

Bug Fixes
---------

- Fixed a problem with loading relative paths in pipfiles with windows-style
  slashes. (#11)
- Fixed a bug with default values used during lockfile generation. (#9)

Improved Documentation
----------------------

- Fixed usage documentation. (#9)


1.0.1 (2018-06-15)
==================

Features
--------

- Updated automation scripts to add release scripts and tagging scripts.
  (1-d0479c0a)

Bug Fixes
---------

- Fix parsing bug with local VCS uris (1-22283f73)
- Fix bug which kept vcs refs in local relative paths (2-34b712ee)

Removals and Deprecations
-------------------------

- Cleanup unused imports and migrate history file to changelog. (1-1cddf326)


1.0.0 (2018-06-14)
==================

Features
--------

- Add pipfile parser to parse all requirements from pipfile to requirement
  format and generate pipfile hashes.
- Add towncrier.
- Reorganize and reformat codebase, refactor.
- Implement lockfile parser and allow it to output to requirements.txt format.
- Better parsing of named requirements with extras.
- Add constraint_line property for pip constraintfile input.
- Rewrite parser logic for cleanliness and consistency.
- Add lockfile parser and allow it to output to requirements format.
- Reorganize and format codebase, refactor code.
- Normalize windows paths for local non-vcs requirements.

Bug Fixes
---------

- Normalize windows paths for local non-vcs requirements.
- Fixed a bug which mixed posix-style and windows-style path separators for
  relative paths.
- Raise an explicit error when handling the current directory as a requirement
  if it isn't installable.
- Bugfix for local file requirements which had their URIs inappropriately
  truncated.
- Requirement line output will now properly match the URI scheme supplied at
  creation time.
- Fixed a bug with path resolution related to ramdisks on windows.
- Fix a bug which caused parsing to fail by adding extra whitespace to
  requirements.

Vendored Libraries
------------------

- Vendored patched pipfile


0.1.1 (2018-06-05)
==================

Updates
-------
 - Fix editable URI naming on windows.
 - Fixed a bug causing failures on `-e .` paths with extras.


0.1.0 (2018-06-05)
==================

Updates
-------
 - Fall back to pip/setuptools as a parser for setup.py files and project names.


0.0.9 (2018-06-03)
==================

Updates
-------
 - Bugfix for parsing setup.py file paths.


0.0.8 (2018-06-xx)
==================

Updates
-------
 - Resolve names in setup.py files if available.
 - Fix a bug with populating Link objects when there is no URI.
 - Properly unquote URIs which have been urlencoded.


0.0.7 (2018-05-26)
==================

Updates
-------
 - Parse wheel names.


0.0.6 (2018-05-26)
==================

Updates
-------
 - Fix windows relative path generation.
 - Add InstallRequirement generation.


0.0.5 (2018-05-25)
==================

Updates
-------
 - Bugfix for parsing editable local paths (they were being parsed as named requirements.)


0.0.4 (2018-05-25)
==================

Updates
-------
 - Bugfix.


0.0.3 (2018-05-10)
==================

Updates
-------
 - Bugfix for including egg fragments in non-vcs urls.


0.0.2 (2018-05-10)
==================

Updates
-------
 - Fix import bug.


0.0.1 (2018-05-10)
==================

Updates
-------
 - Bugfixes for remote files and zipfiles, extras on urls.
 - Initial commit
