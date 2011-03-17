
"""
Test that when being upgraded to version 2, a version 1 Inbox copies enough
state from the various Message objects which exist into the source tracking
system so that L{xquotient.exmess.getMessageSources} work right.
"""

from axiom.test.historic.stubloader import StubbedTest

from xquotient.exmess import getMessageSources
from xquotient.inbox import Inbox


class InboxUpgradeTestCase(StubbedTest):
    def test_upgrade(self):
        inbox = self.store.findUnique(Inbox)
        self.assertEquals(
            list(getMessageSources(self.store)),
            [u'source one', u'source two'])
