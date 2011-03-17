# -*- test-case-name: xquotient.test.historic.test_composer4to5 -*-

"""
Create stub database for upgrade of L{xquotient.compose.Composer} from version 4
to version 5.
"""


from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn
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
    installOn(Composer(store=s), s)


if __name__ == '__main__':
    saveStub(createDatabase, 10991)
