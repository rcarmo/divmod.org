# -*- test-case-name xquotient.test.test_historic.test_compose1to2 -*-

"""
Create stub database for upgrade of L{xquotient.compose.Composer} from
version 1 to version 2.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.userbase import LoginMethod

from xquotient.compose import Composer

def createDatabase(s):
    """
    Install a Composer on the given store.
    """
    LoginMethod(store=s,
                localpart=u'foo',
                domain=u'bar',
                verified=True,
                protocol=u'*',
                account=s,
                internal=False)
    Composer(store=s).installOn(s)



if __name__ == '__main__':
    saveStub(createDatabase, 7485)
