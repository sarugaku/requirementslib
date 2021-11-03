Contributing to requirementslib
===============================

To work on requirementslib itself, fork the repository and clone your fork to your local
system.

Now, install the development requirements::

    cd requirementslib
    git submodule sync && git submodule update --init --recursive
    pip install -e .[dev]


To run the test suite locally::

    nox -s tests

To run the test coverage::

    nox -s coverage

To generate the docs locally::

    nox -s docs
