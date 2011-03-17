
from axiom.test.historic import stubloader
from xmantissa.stats import StatBucket

class FreeTicketSignupTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        for bucket in self.store.query(StatBucket):
            self.assertEqual(bucket.type, "axiom_commits")
