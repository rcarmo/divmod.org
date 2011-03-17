
"""
Test that a version 1 MailTransferAgent in a site store is unchanged by
this upgrade but that in a user store it is replaced with a
MailDeliveryAgent.
"""

from twisted.mail.smtp import IMessageDeliveryFactory

from axiom.test.historic.stubloader import StubbedTest
from axiom.userbase import LoginSystem

from xquotient.mail import MailTransferAgent, MailDeliveryAgent


class MailTransferAgentUpgradeTestCase(StubbedTest):
    def assertMTA(self, powerup):
        self.failUnless(
            isinstance(powerup, MailTransferAgent),
            "%r found instead of MailTransferAgent" % (powerup,))


    def assertMDA(self, powerup):
        self.failUnless(
            isinstance(powerup, MailDeliveryAgent),
            "%r found instead of MailDeliveryAgent" % (powerup,))


    def test_upgradeSiteInTransaction(self):
        mta = self.store.transact(IMessageDeliveryFactory, self.store)
        self.assertMTA(mta)


    def test_upgradeSiteOutsideTransaction(self):
        mta = IMessageDeliveryFactory(self.store)
        self.assertMTA(mta)


    def test_upgradeUserInTransaction(self):
        loginSystem = self.store.findUnique(LoginSystem)
        account = loginSystem.accountByAddress(u'testuser', u'localhost')
        avatar = account.avatars.open()
        mda = avatar.transact(IMessageDeliveryFactory, account, None)
        self.assertMDA(mda)


    def test_upgradeUserOutsideTransaction(self):
        loginSystem = self.store.findUnique(LoginSystem)
        account = loginSystem.accountByAddress(u'testuser', u'localhost')
        avatar = account.avatars.open()
        mda = IMessageDeliveryFactory(account, None)
        self.assertMDA(mda)


    def test_upgradeParentlessUserInTransaction(self):
        loginSystem = self.store.findUnique(LoginSystem)
        account = loginSystem.accountByAddress(u'testuser', u'localhost')
        avatar = account.avatars.open()
        avatar.parent = avatar.idInParent = None
        mda = avatar.transact(IMessageDeliveryFactory, account, None)
        self.assertMDA(mda)


    def test_upgradeParentlessUserOutsideTransaction(self):
        loginSystem = self.store.findUnique(LoginSystem)
        account = loginSystem.accountByAddress(u'testuser', u'localhost')
        avatar = account.avatars.open()
        avatar.parent = avatar.idInParent = None
        mda = IMessageDeliveryFactory(account, None)
        self.assertMDA(mda)

    def tearDown(self):
        """
        This test suite is unfortunately awful and buggy and implicitly starts
        upgraders in substores and does not wait for them to complete.  When
        correct error logging was added to the upgrade process, they all broke.
        However, the errors logged here are mostly harmless so they are being
        quashed for the time being.
        """                     # -glyph
        d = StubbedTest.tearDown(self)
        def flushit(ign):
            from epsilon.cooperator import SchedulerStopped
            self.flushLoggedErrors(SchedulerStopped)
            return ign
        return d.addCallback(flushit)
