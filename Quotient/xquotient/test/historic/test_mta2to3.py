from axiom.test.historic.stubloader import StubbedTest
from xquotient.mail import MailTransferAgent
from axiom.userbase import LoginSystem

class MTAUpgraderTest(StubbedTest):
    def testMTA2to3(self):
        """
        Make sure MailTransferAgent upgraded OK and that its
        "userbase" attribute refers to the store's userbase.
        """
        mta = self.store.findUnique(MailTransferAgent)
        self.assertIdentical(mta.userbase,
                             self.store.findUnique(LoginSystem))
