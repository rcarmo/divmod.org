
"""
Tests for L{Inbox} schema upgrading.
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.webapp import PrivateApplication

from xquotient.inbox import Inbox
from xquotient.mail import MessageSource, DeliveryAgent

from xquotient.spam import Filter
from xquotient.filter import Focus
from xquotient.quotientapp import QuotientPreferenceCollection
from xquotient.quotientapp import MessageDisplayPreferenceCollection
from xquotient.test.historic.stub_inbox5to6 import UI_COMPLEXITY, SHOW_MORE_DETAIL

class InboxUpgradeTests(StubbedTest):
    """
    Tests for L{Inbox} schema upgrading.
    """
    def test_attributes(self):
        """
        The upgrade preserves the values of all the remaining attributes.
        """
        inbox = self.store.findUnique(Inbox)
        self.assertEquals(inbox.uiComplexity, UI_COMPLEXITY)
        self.assertEquals(inbox.showMoreDetail, SHOW_MORE_DETAIL)
        self.assertTrue(isinstance(
                inbox.privateApplication, PrivateApplication))
        self.assertTrue(isinstance(inbox.messageSource, MessageSource))
        self.assertTrue(isinstance(
                inbox.quotientPrefs, QuotientPreferenceCollection))
        self.assertTrue(isinstance(
                inbox.messageDisplayPrefs, MessageDisplayPreferenceCollection))
        self.assertTrue(isinstance(inbox.deliveryAgent, DeliveryAgent))
        self.assertTrue(isinstance(inbox.filter, Filter))
        self.assertTrue(isinstance(inbox.focus, Focus))
