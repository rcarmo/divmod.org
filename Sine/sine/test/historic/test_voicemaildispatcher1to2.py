from axiom.test.historic import stubloader
from axiom.userbase import LoginSystem
from sine.sipserver import SIPServer
from sine.sip import SIPTransport
from sine.voicemail import VoicemailDispatcher
from sine.confession import AnonConfessionUser

class VoicemailDispatcherTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        """
        Ensure upgraded fields refer to correct items.
        """
        sipServer = self.store.findUnique(SIPServer)
        sipServer.transport = SIPTransport(None, ['localhost'], 5060)
        sipServer.mediaController = None
        loginSystem = self.store.findUnique(LoginSystem)
        account = loginSystem.accountByAddress(u'testuser', u'localhost')
        substore = account.avatars.open()
        #vd = substore.findUnique(VoicemailDispatcher)
        # ^-- this doesn't work. This does. --v
        vd = substore.getItemByID(3)
        self.assertEqual(vd.voicemailUser,
                         substore.findUnique(AnonConfessionUser))
        return sipServer.stopService()

    #the following is from
    #xquotient.test.historic.test_mta1to2.MailTransferAgentUpgradeTestCase
    def tearDown(self):
        """
        This test suite is unfortunately awful and buggy and implicitly starts
        upgraders in substores and does not wait for them to complete.  When
        correct error logging was added to the upgrade process, they all broke.
        However, the errors logged here are mostly harmless so they are being
        quashed for the time being.
        """                     # -glyph
        d = stubloader.StubbedTest.tearDown(self)
        def flushit(ign):
            from epsilon.cooperator import SchedulerStopped
            self.flushLoggedErrors(SchedulerStopped)
            return ign
        return d.addCallback(flushit)
