Added support for ``Requirement.get_dependencies()`` to return unpinned dependencies.
Implemented full support for both parsing and writing lockfiles.
Introduced lazy imports to enhance runtime performance.
Switch to ``packaging.canonicalize_name()`` instead of custom canonicalization function.
Added ``Requirement.copy()`` to the api to copy a requirement.
