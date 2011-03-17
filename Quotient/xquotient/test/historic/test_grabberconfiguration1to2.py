from axiom.test.historic import stubloader
from xquotient.grabber import GrabberConfiguration
from xmantissa.webapp import PrivateApplication
from xquotient.mail import DeliveryAgent

class GCTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        """
        Ensure upgraded fields refer to correct items.
        """
        gc = self.store.findUnique(GrabberConfiguration)
        self.assertEqual(gc.privateApplication, self.store.findUnique(PrivateApplication))
        self.assertEqual(gc.deliveryAgent, self.store.findUnique(DeliveryAgent))
