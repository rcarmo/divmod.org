
"""
Tests for the upgrade of L{MessageQueue} from version 1 to 2, in which its
C{scheduler} attribute was removed.
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.ixmantissa import IMessageRouter
from xmantissa.interstore import MessageQueue

from xmantissa.test.historic.stub_messagequeue1to2 import MESSAGE_COUNT


class MessageQueueUpgradeTests(StubbedTest):
    def test_attributes(self):
        """
        The value of the C{messageCounter} attribute is preserved by the
        upgrade.
        """
        self.assertEquals(
            self.store.findUnique(MessageQueue).messageCounter,
            MESSAGE_COUNT)

    def test_powerup(self):
        """
        The L{MessageQueue} is still a L{IMessageRouter} powerup on its store
        after the upgrade.
        """
        self.assertEquals(
            [self.store.findUnique(MessageQueue)],
            list(self.store.powerupsFor(IMessageRouter)))

