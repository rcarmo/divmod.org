"""
Test that attributes are preserved, and fromAddress is set to None for
_NeedsDelivery version 2
"""

from axiom.test.historic.stubloader import StubbedTest

from xquotient.smtpout import DeliveryToAddress
from xquotient.compose import Composer

class NeedsDeliveryUpgradeTestCase(StubbedTest):
    def testUpgrade(self):
        nd = self.store.findUnique(DeliveryToAddress)
        self.assertIdentical(nd.fromAddress, None)
        self.assertIdentical(nd.delivery.composer,
                             self.store.findUnique(Composer))
        self.assertEqual(nd.tries, 21)
        self.assertIdentical(nd.message, self.store)
        self.assertEqual(nd.toAddress, 'to@host')
