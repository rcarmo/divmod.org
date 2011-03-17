
"""
Tests for L{GrabberConfiguration} schema upgrading.
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.webapp import PrivateApplication

from xquotient.grabber import GrabberConfiguration
from xquotient.mail import DeliveryAgent
from xquotient.test.historic.stub_grabberconfiguration2to3 import PAUSED


class GrabberConfigurationUpgradeTests(StubbedTest):
    """
    Tests for L{GrabberConfiguration} schema upgrading.
    """
    def test_attributes(self):
        """
        The upgrade preserves the values of all the remaining attributes.
        """
        grabber = self.store.findUnique(GrabberConfiguration)
        self.assertEquals(grabber.paused, PAUSED)
        self.assertTrue(isinstance(grabber.privateApplication, PrivateApplication))
        self.assertTrue(isinstance(grabber.deliveryAgent, DeliveryAgent))
