"""
Test that the L{xquotient.compose.FromAddress} item whose address attribute
matches the return value of L{xquotient.compose._getFromAddressFromStore} is
turned into the system address, and other FromAddress items survive intact
"""

from axiom.test.historic.stubloader import StubbedTest

from xquotient.smtpout import FromAddress, _getFromAddressFromStore


class FromAddressUpgradeTestCase(StubbedTest):
    def testUpgrade(self):
        sa = FromAddress.findSystemAddress(self.store)
        self.assertEqual(sa.address, 'foo@bar')
        self.assertEqual(sa.smtpHost, 'bar')
        self.assertEqual(sa.smtpPort, 26)
        self.assertEqual(sa.smtpUsername, 'foo')
        self.assertEqual(sa.smtpPassword, 'secret')

        other = FromAddress.findByAddress(self.store, u'foo2@bar')
        self.assertEqual(other.smtpHost, 'bar')
        self.assertEqual(other.smtpPort, 26)
        self.assertEqual(other.smtpUsername, 'foo2')
        self.assertEqual(other.smtpPassword, 'secret')
