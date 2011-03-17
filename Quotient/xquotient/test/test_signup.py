"""
Test installation of the Quotient offering, as well as testing
signup with different combinations of selected benefactor factories
"""

from time import time

from twisted.trial.unittest import TestCase
from twisted.python.reflect import qual

from axiom.scripts import axiomatic
from axiom.store import Store
from axiom import userbase
from axiom.test.util import getPristineStore

from xmantissa import offering, signup
from xmantissa.plugins.free_signup import freeTicket
from xmantissa.product import Product

from xquotient import exmess
from xquotient.compose import Composer
from xquotient.inbox import Inbox

def createStore(testCase):
    dbpath = testCase.mktemp()
    axiomatic.main(['-d', dbpath, 'mantissa', '--admin-password', 'password'])

    store = Store(dbpath)

    _userbase = store.findUnique(userbase.LoginSystem)
    adminAccount = _userbase.accountByAddress(u'admin', u'localhost')
    adminStore = adminAccount.avatars.open()

    conf = adminStore.findUnique(offering.OfferingConfiguration)
    conf.installOffering(getQuotientOffering(), None)
    return store

def getQuotientOffering():
    for off in offering.getOfferings():
        if off.name == 'Quotient':
            return off

def getFactories(*names):
    factories = []
    for factory in getQuotientOffering().benefactorFactories:
        name = factory.benefactorClass.__name__.lower()
        if name.endswith('benefactor'):
            name = name[:-len('benefactor')]
        if name in names:
            factories.append(factory)
    return factories

class InstallationTestCase(TestCase):
    """
    Tests to ensure we can at least get as far as installing the
    application and signing up.  We don't really care whether the
    right stuff was installed.
    """


    def setUp(self):
        self.store = getPristineStore(self, createStore)
        self.loginSystem = self.store.findUnique(userbase.LoginSystem)

        adminAvatar = self.loginSystem.accountByAddress(u'admin', u'localhost')
        adminStore = adminAvatar.avatars.open()

        self.signupConfig = adminStore.findUnique(signup.SignupConfiguration)

    def createSignupAndSignup(self, powerups):
        """
        Signup via a newly-created signup, using a unique email address.
        @return: substore, which will be endowed with C{product}
        """

        product = Product(store=self.store, types=[qual(p) for (name, desc, p) in powerups])
        qsignup = self.signupConfig.createSignup(
                    u'admin@localhost',
                    freeTicket.itemClass,
                    {'prefixURL': u'signup'},
                    product,
                    u'', u'')

        booth = qsignup.booth
        localpart = unicode(str(time()), 'ascii')
        ticket = booth.createTicket(
                    booth, localpart + '@localhost', product)
        ticket.claim()
        return self.loginSystem.accountByAddress(
                            localpart, u'localhost').avatars.open()

    def testBasic(self):
        """
        Test signup with the top-most Quotient powerup
        """
        self.createSignupAndSignup([(None, None, Inbox)])

    def testCompose(self):
        """
        Test signup with the compose benefactor (which
        depends on the top-most Quotient benefactor)
        """
        self.createSignupAndSignup([(None, None, Composer)])

    def testAll(self):
        """
        Test signup with all benefactors
        """
        self.createSignupAndSignup(
            getQuotientOffering().installablePowerups)

    def testDefaultMessageDisplayPrefs(self):
        """
        On signup, users' preferred message format should be HTML.
        """
        ss = self.createSignupAndSignup(
            getQuotientOffering().installablePowerups)
        self.assertEqual(ss.findUnique(
            exmess.MessageDisplayPreferenceCollection).preferredFormat, u"text/html")
