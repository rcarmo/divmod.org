# -*- test-case-name: xquotient.test.historic.test_inbox4to5 -*-

"""
Create a stub database for upgrade of L{xquotient.inbox.Inbox} from version 4
to version 5, which adds the C{focus} attribute.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn

from xquotient.inbox import Inbox

def createDatabase(s):
    installOn(Inbox(store=s, uiComplexity=2, showMoreDetail=True), s)

if __name__ == '__main__':
    saveStub(createDatabase, 11145)
