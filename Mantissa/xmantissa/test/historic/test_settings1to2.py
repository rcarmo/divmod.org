from axiom.test.historic import stubloader
from xmantissa.settings import Settings

class SettingsTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        self.assertEquals(self.store.count(Settings), 0)
