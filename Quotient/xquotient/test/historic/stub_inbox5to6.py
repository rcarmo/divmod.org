# -*- test-case-name: xquotient.test.historic.test_inbox5to6 -*-

"""
Create a stub database for upgrade of L{xquotient.inbox.Inbox} from version 5
to version 6, which removes the C{scheduler} attribute.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn

from xquotient.inbox import Inbox

UI_COMPLEXITY = 2
SHOW_MORE_DETAIL = True

def createDatabase(store):
    installOn(
        Inbox(store=store, uiComplexity=UI_COMPLEXITY,
              showMoreDetail=SHOW_MORE_DETAIL),
        store)

if __name__ == '__main__':
    saveStub(createDatabase, 17729)
