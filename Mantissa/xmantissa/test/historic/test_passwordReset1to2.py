from axiom.test.historic import stubloader
from xmantissa.signup import PasswordReset

class PasswordResetTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        self.assertEqual(self.store.count(PasswordReset), 0)
