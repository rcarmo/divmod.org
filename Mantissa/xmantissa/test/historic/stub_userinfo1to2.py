# -*- test-case-name: xmantissa.test.historic.test_userinfo1to2 -*-

"""
Create the stub database for the test for the UserInfo schema version 1 to 2
upgrader.
"""

from axiom.test.historic.stubloader import saveStub

from xmantissa.signup import UserInfo

FIRST = u'Alice'
LAST = u'Smith'

def createDatabase(store):
    """
    Create a version 1 L{UserInfo} item in the given store.
    """
    UserInfo(store=store, firstName=FIRST, lastName=LAST)


if __name__ == '__main__':
    saveStub(createDatabase, 13447)
