from axiom.test.historic.stubloader import StubbedTest
from xquotient.popout import POP3Listener
from axiom.userbase import LoginSystem

class POP3ListenerUpgraderTest(StubbedTest):
    def testUpgrade(self):
        p3l = self.store.findUnique(POP3Listener)
        self.assertIdentical(p3l.userbase,
                             self.store.findUnique(LoginSystem))
