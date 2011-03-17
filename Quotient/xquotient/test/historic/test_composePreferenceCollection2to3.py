"""
Test that a ComposePreferenceCollection with smarthost attributes set turns
into a FromAddress item, and doesn't overwrite the FromAddress created from
the user's login credentials
"""

from axiom.test.historic.stubloader import StubbedTest

from xquotient.compose import ComposePreferenceCollection, Composer
from xquotient.smtpout import FromAddress


class ComposePreferenceCollectionUpgradeTestCase(StubbedTest):
    def testUpgrade(self):
        composer = self.store.findUnique(Composer)

        # this was the value of ComposePreferenceCollection.smarthostAddress in the database
        newFrom = FromAddress.findByAddress(self.store, u'foo2@bar')

        # these were the values of the smarthost* attributes on the in-database
        # ComposePreferenceCollection
        self.assertEqual(newFrom.smtpHost, u'localhost')
        self.assertEqual(newFrom.smtpPort, 23)
        self.assertEqual(newFrom.smtpUsername, u'foo2')
        self.assertEqual(newFrom.smtpPassword, u'secret')

        FromAddress.findByAddress(self.store, u'foo@bar')
