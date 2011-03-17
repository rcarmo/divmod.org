from axiom.test.historic import stubloader
from xmantissa.signup import FreeTicketSignup

class FreeTicketSignupTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        fts = self.store.findUnique(FreeTicketSignup)
        ae = self.assertEqual

        ae(fts.prefixURL, '/a/b')
        ae(fts.booth, self.store)
        ae(fts.emailTemplate, 'TEMPLATE!')
        ae(fts.prompt, 'Sign Up')
