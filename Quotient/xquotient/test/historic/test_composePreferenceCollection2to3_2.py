"""
Test that a ComposePreferenceCollection without smarthost attributes doesn't
turn into a FromAddress item
"""

from axiom.test.historic.stubloader import StubbedTest

from xquotient.compose import ComposePreferenceCollection, Composer
from xquotient.smtpout import FromAddress


class ComposePreferenceCollectionUpgradeTestCase(StubbedTest):
    def testUpgrade(self):
        composer = self.store.findUnique(Composer)

        # foo/bar are the localpart/domain of the LoginMethod
        newFrom = FromAddress.findByAddress(self.store, u'foo@bar')

        self.assertEqual(newFrom.smtpHost, None)
        self.assertEqual(newFrom.smtpUsername, None)
        self.assertEqual(newFrom.smtpPassword, None)
