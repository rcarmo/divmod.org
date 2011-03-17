# -*- test-case-name xquotient.test.test_historic.test_composePreferenceCollection2to3 -*-

"""
Create stub database for upgrade of
L{xquotient.compose.ComposePreferenceCollection} from version 2 to version 3.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.userbase import LoginMethod

from xquotient.compose import ComposePreferenceCollection, Composer

def createDatabase(s):
    """
    Install a Composer and ComposePreferenceCollection on the given store.
    """
    LoginMethod(store=s,
                localpart=u'foo',
                domain=u'bar',
                verified=True,
                protocol=u'*',
                account=s,
                internal=False)

    Composer(store=s).installOn(s)

    ComposePreferenceCollection(
        store=s,
        smarthostAddress=u'foo2@bar',
        smarthostUsername=u'foo2',
        smarthostPort=23,
        smarthostPassword=u'secret',
        preferredSmarthost=u'localhost').installOn(s)



if __name__ == '__main__':
    saveStub(createDatabase, 9097)
