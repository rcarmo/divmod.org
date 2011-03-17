
"""
Tests for L{Composer} schema upgrading.
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.webapp import PrivateApplication

from xquotient.mail import MailDeliveryAgent, DeliveryAgent
from xquotient.compose import Composer, ComposePreferenceCollection


class ComposerUpgradeTests(StubbedTest):
    """
    Tests for L{Composer} schema upgrading.
    """
    def test_attributes(self):
        """
        The upgrade preserves the values of all the remaining attributes.
        """
        composer = self.store.findUnique(Composer)
        self.assertTrue(isinstance(composer.privateApplication, PrivateApplication))
        self.assertTrue(isinstance(composer.mda, MailDeliveryAgent))
        self.assertTrue(isinstance(composer.deliveryAgent, DeliveryAgent))
        self.assertTrue(isinstance(composer.prefs, ComposePreferenceCollection))

