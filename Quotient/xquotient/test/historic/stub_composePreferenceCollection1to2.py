# -*- test-case-name xquotient.test.test_historic.test_composePreferenceCollection1to2 -*-

"""
Create stub database for upgrade of
L{xquotient.compose.ComposePreferenceCollection} from version 1 to
version 2.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.userbase import LoginMethod

from xquotient.compose import ComposePreferenceCollection

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

    ComposePreferenceCollection(store=s).installOn(s)



if __name__ == '__main__':
    saveStub(createDatabase, 8183)
