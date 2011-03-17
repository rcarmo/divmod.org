"""
Test that when being upgraded to version 4, a version 3 Inbox has the 'filter'
attribute set to a new L{xquotient.spam.Filter}, and that the other attributes
are copied over
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.webapp import PrivateApplication

from xquotient import spam
from xquotient.inbox import Inbox



class InboxUpgradeTestCase(StubbedTest):
    def setUp(self):
        D = StubbedTest.setUp(self)
        def setUpFinished():
            self.inbox = self.store.findUnique(Inbox)
        D.addCallback(lambda _: setUpFinished())
        return D


    def test_filterAttributeSet(self):
        """
        Test that L{xquotient.inbox.Inbox.filter} is set to the only spam
        filter in the store
        """
        filter = self.store.findUnique(spam.Filter)
        self.assertIdentical(filter, self.inbox.filter)


    def test_filterInstalled(self):
        """
        Test that the L{xquotient.spam.Filter} looks like it was properly
        installed, by looking at its dependencies
        """
        filter = self.store.findUnique(spam.Filter)
        self.failIf(
            (filter.messageSource is None or filter.tiSource is None),
            'spam.Filter was not installed properly')


    def test_inboxAttributesCopied(self):
        """
        Test that the attributes of the L{xquotient.inbox.Inbox} were copied
        over from the previous version
        """
        self.assertEqual(self.inbox.uiComplexity, 2)
        self.assertEqual(self.inbox.showMoreDetail, True)

        # look at one of the dependency attributes
        self.assertIdentical(
            self.inbox.privateApplication,
            self.store.findUnique(PrivateApplication))


    def test_inboxAttributesDeleted(self):
        """
        Test that the 'installedOn' and 'catalog' attributes were deleted from
        the inbox
        """
        self.failIf(hasattr(self.inbox, 'installedOn'))
        self.failIf(hasattr(self.inbox, 'catalog'))
