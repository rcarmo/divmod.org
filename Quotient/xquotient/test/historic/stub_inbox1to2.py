# -*- test-case-name: xquotient.test.historic.test_inbox1to2 -*-

"""
Create a stub database for upgrade of L{xquotient.inbox.Inbox} from version 1
to version 2.
"""

from axiom.test.historic.stubloader import saveStub

from xquotient.exmess import Message
from xquotient.inbox import Inbox

def createDatabase(s):
    Inbox(store=s)
    Message(store=s, source=u'source one')
    Message(store=s, source=u'source one')
    Message(store=s, source=u'source two')

if __name__ == '__main__':
    saveStub(createDatabase, 7549)
