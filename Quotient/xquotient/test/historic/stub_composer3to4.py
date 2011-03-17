# -*- test-case-name xquotient.test.test_historic.test_composer2to3 -*-

"""
Create stub database for upgrade of L{xquotient.compose.Composer} from
version 3 to version 4.
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
    saveStub(createDatabase, 10556)
