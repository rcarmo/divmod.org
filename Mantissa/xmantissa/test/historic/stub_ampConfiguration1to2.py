# -*- test-case-name: xmantissa.test.historic.test_ampConfiguration1to2 -*-
# Copyright 2008 Divmod, Inc. See LICENSE file for details

"""
Generate a stub for the tests for the upgrade from schema version 1 to 2 of the
AMPConfiguration item.
"""

from axiom.dependency import installOn
from axiom.test.historic.stubloader import saveStub

from xmantissa.ampserver import AMPConfiguration


def createDatabase(store):
    """
    Make an L{AMPConfiguration} in the given store.
    """
    installOn(AMPConfiguration(store=store), store)


if __name__ == '__main__':
    saveStub(createDatabase, 16892)
