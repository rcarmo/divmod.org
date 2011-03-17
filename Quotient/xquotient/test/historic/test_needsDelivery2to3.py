from axiom.test.historic.stubloader import StubbedTest

from xquotient.compose import Composer
from xquotient.smtpout import DeliveryToAddress, MessageDelivery, UNSENT


class TestDeliveryToAddress(StubbedTest):
    """
    Test that the upgraded DeliveryToAddress (was _NeedsDelivery) has a
    MessageDelivery and that it is considered UNSENT (new status attribute)
    """

    def testUpgrade(self):
        nd = self.store.findUnique(DeliveryToAddress)
        self.assertIdentical(nd.delivery,
                             self.store.findUnique(MessageDelivery))
        self.assertIdentical(nd.delivery.composer,
                             self.store.findUnique(Composer))
        self.assertEqual(nd.tries, 21)
        self.assertEqual(nd.status, UNSENT)
