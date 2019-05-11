Contributing to requirementslib
====================================

To work on requirementslib itself, fork the repository and clone your fork to your local
system.

Now, install the development requirements::

    cd requirementslib
    git submodule sync && git submodule update --init --recursive
    pipenv install --dev


To run the test suite locally::

    pipenv run pytest tests
