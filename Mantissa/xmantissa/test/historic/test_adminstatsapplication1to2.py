from axiom.test.historic import stubloader
from xmantissa.webadmin import AdminStatsApplication
from xmantissa.webapp import PrivateApplication

class ASATestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        """
        Ensure upgraded fields refer to correct items.
        """
        self.assertEqual(self.store.findUnique(AdminStatsApplication).privateApplication,
                         self.store.findUnique(PrivateApplication))
