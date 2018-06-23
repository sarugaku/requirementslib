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
