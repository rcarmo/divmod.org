from axiom.test.historic import stubloader
from xmantissa.signup import UserInfoSignup

class FreeTicketSignupTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        fts = self.store.findUnique(UserInfoSignup)
        self.assertEqual(len(fts.product.types), 6)
