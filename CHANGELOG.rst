1.0.0 (2018-06-14)
==================

Features
--------

- Add pipfile parser to parse all requirements from pipfile to requirement
  format and generate pipfile hashes (1-8626a21e)
- Add towncrier (2-67dc613c)
- Reorganize and reformat codebase, refactor (3-e75874b8)
- Implement lockfile parser and allow it to output to requirements.txt format
  (4-db40abee)
- Better parsing of named requirements with extras (5-29003d80)
- Add constraint_line property for pip constraintfile input (6-35545f43)
- Rewrite parser logic for cleanliness and consistency (7-86730a3b)

Bug Fixes
---------

- Normalize windows paths for local non-vcs requirements. (1-c0427444)
- Fixed a bug which mixed posix-style and windows-style path separators for
  relative paths (2-87c25f38)
- Raise an explicit error when handling the current directory as a requirement
  if it isn't installable (3-945eb36f)
- Bugfix for local file requirements which had their URIs inappropriately
  truncated (4-5db8d449)
- Requirement line output will now properly match the URI scheme supplied at
  creation time (5-fe297a9d)
- Fixed a bug with path resolution related to ramdisks on windows (6-47e8d4e6)
- Fix a bug which caused parsing to fail by adding extra whitespace to
  requirements (7-5e90adc8)

Vendored Libraries
------------------

- Vendored patched pipfile
