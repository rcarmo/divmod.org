from axiom.test.historic import stubloader
from xmantissa.webadmin import DeveloperApplication
from xmantissa.webapp import PrivateApplication

class DATestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        """
        Ensure upgraded fields refer to correct items.
        """
        self.assertEqual(self.store.findUnique(DeveloperApplication).privateApplication,
                         self.store.findUnique(PrivateApplication))
