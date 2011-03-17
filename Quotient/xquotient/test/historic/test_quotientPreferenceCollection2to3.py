from axiom.test.historic import stubloader

from xquotient.quotientapp import QuotientPreferenceCollection
from xquotient.exmess import MessageDisplayPreferenceCollection

class PrefsUpgradeTest(stubloader.StubbedTest):
    def testUpgrade(self):
        self.store.findUnique(QuotientPreferenceCollection)
        self.store.findUnique(MessageDisplayPreferenceCollection)
