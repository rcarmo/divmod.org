"""
Test that when being upgraded to version 4, a version 3 Inbox has the 'filter'
attribute set to a L{xquotient.spam.Filter} if one exists in the store
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.webapp import PrivateApplication

from xquotient import spam
from xquotient.inbox import Inbox



class InboxUpgradeTestCase(StubbedTest):
    def test_filterAttributeSet(self):
        """
        Test that L{xquotient.inbox.Inbox.filter} is set to the only spam
        filter in the store
        """
        filter = self.store.findUnique(spam.Filter)
        inbox = self.store.findUnique(Inbox)
        self.assertIdentical(filter, inbox.filter)
