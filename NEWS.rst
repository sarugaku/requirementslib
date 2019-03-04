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
