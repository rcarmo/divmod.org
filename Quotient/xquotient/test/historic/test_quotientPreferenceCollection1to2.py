from axiom.test.historic import stubloader

from xquotient.quotientapp import QuotientPreferenceCollection

class PrefsUpgradeTest(stubloader.StubbedTest):
    def testUpgrade(self):
        pc = self.store.findUnique(QuotientPreferenceCollection)
        # in version 3, all the prefs have either moved to a different
        # preference collection or been removed entirely, so there isn't
        # much to test.
