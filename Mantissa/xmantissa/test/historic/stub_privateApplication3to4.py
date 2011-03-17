# -*- test-case-name: xmantissa.test.historic.test_privateApplication3to4 -*-

"""
Generate a test database containing a L{PrivateApplication} installed on its
store without powering it up for L{ITemplateNameResolver}.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn
from axiom.userbase import LoginSystem

from xmantissa.webapp import PrivateApplication

USERNAME = u'testuser'
DOMAIN = u'localhost'
PREFERRED_THEME = u'theme-preference'
HIT_COUNT = 8765
PRIVATE_KEY = 123456


def createDatabase(store):
    """
    Instantiate a L{PrivateApplication} in C{store} and install it.
    """
    loginSystem = LoginSystem(store=store)
    installOn(loginSystem, store)
    account = loginSystem.addAccount(USERNAME, DOMAIN, None)
    subStore = account.avatars.open()

    app = PrivateApplication(
        store=subStore,
        preferredTheme=PREFERRED_THEME,
        hitCount=HIT_COUNT,
        privateKey=PRIVATE_KEY)
    installOn(app, subStore)


if __name__ == '__main__':
    saveStub(createDatabase, 12759)
