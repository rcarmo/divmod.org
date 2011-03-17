from axiom.test.historic import stubloader
from sine.sipserver import SIPServer
from axiom.userbase import LoginSystem
class SIPServerTest(stubloader.StubbedTest):
    def testUpgrade(self):
        ss = self.store.findUnique(SIPServer)
        self.failUnless(isinstance(ss.userbase, LoginSystem))
