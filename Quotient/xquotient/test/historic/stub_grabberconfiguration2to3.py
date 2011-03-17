# -*- test-case-name: xquotient.test.historic.test_grabberconfiguration2to3 -*-

"""
Stub database generator for version 2 of L{GrabberConfiguration}.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn

from xquotient.grabber import GrabberConfiguration

PAUSED = True

def createDatabase(store):
    installOn(
        GrabberConfiguration(store=store, paused=PAUSED),
        store)


if __name__ == '__main__':
    saveStub(createDatabase, 17729)
