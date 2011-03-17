from axiom.test.historic import stubloader
from xmantissa.signup import FreeTicketSignup

class FreeTicketSignupTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        fts = self.store.findUnique(FreeTicketSignup)
        self.assertEqual(len(fts.product.types), 6)
