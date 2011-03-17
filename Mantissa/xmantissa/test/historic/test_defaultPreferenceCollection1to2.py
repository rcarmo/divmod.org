
from axiom.test.historic import stubloader
from xmantissa.prefs import DefaultPreferenceCollection

class DefaultPreferenceCollectionTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        pc = self.store.findUnique(DefaultPreferenceCollection)
        self.assertEqual(pc.timezone, 'US/Eastern')
