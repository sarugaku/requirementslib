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
