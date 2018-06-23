from requirementslib import Lockfile


def test_lockfile():
    lockfile = Lockfile.create('.')

    requires = lockfile.as_requirements(dev=False)
    assert requires == []

    requires = lockfile.as_requirements(dev=True)
    assert 'attrs==18.1.0' in requires
