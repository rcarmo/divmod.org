# -*- test-case-name: xquotient.test.historic.test_composer5to6 -*-

"""
Create stub database for upgrade of L{xquotient.compose.Composer} from version 5
to version 6.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn
from axiom.userbase import LoginMethod

from xquotient.compose import Composer

LOCAL = u'foo'
DOMAIN = u'bar'
VERIFIED = True
PROTOCOL = u'*'
INTERNAL = False

def createDatabase(store):
    LoginMethod(
        store=store, localpart=LOCAL, domain=DOMAIN, verified=VERIFIED,
        protocol=PROTOCOL, account=store, internal=INTERNAL)
    installOn(Composer(store=store), store)


if __name__ == '__main__':
    saveStub(createDatabase, 17729)
