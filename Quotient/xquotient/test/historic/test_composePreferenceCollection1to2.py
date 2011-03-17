"""
Test that new attributes are introduced in version 2 of
ComposePreferenceCollection.
"""

from axiom.test.historic.stubloader import StubbedTest

from xquotient.compose import ComposePreferenceCollection

class ComposePreferenceCollectionUpgradeTestCase(StubbedTest):
    def testUpgrade(self):
        cpc = self.store.findUnique(ComposePreferenceCollection)
