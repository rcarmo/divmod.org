"""
Test that when being upgraded to version 4, a version 3 Inbox has the 'filter'
attribute set to a new L{xquotient.spam.Filter}, and that the other attributes
are copied over
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.webapp import PrivateApplication

from xquotient.spam import Filter
from xquotient.filter import Focus
from xquotient.inbox import Inbox



class InboxUpgradeTestCase(StubbedTest):
    def test_focusAttributeSet(self):
        """
        Test that L{xquotient.inbox.Inbox.focus} is set to the only Focus
        powerup in the store.
        """
        inbox = self.store.findUnique(Inbox)
        focus = self.store.findUnique(Focus)
        self.assertIdentical(focus, inbox.focus)


    def test_focusInstalled(self):
        """
        Test that the L{xquotient.filter.Focus} looks like it was properly
        installed, by looking at its dependencies
        """
        focus = self.store.findUnique(Focus)
        self.failIf(
            focus.messageSource is None,
            'xquotient.filter.Focus was not installed properly')


    def test_inboxAttributesCopied(self):
        """
        Test that the attributes of the L{xquotient.inbox.Inbox} were copied
        over from the previous version
        """
        inbox = self.store.findUnique(Inbox)
        self.assertEqual(inbox.uiComplexity, 2)
        self.assertEqual(inbox.showMoreDetail, True)

        self.assertIdentical(
            inbox.privateApplication,
            self.store.findUnique(PrivateApplication))

        self.assertIdentical(
            inbox.filter,
            self.store.findUnique(Filter))
