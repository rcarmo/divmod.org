from twisted.trial import unittest
from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from axiom import store
from axiom.store import Store
from axiom.dependency import installOn
from axiom.plugins.axiom_plugins import Create
from axiom.plugins.mantissacmd import Mantissa

from xquotient import filter, mimepart
from xquotient.mimestorage import Part
from xquotient.exmess import Message, FOCUS_STATUS
from xquotient.filter import Focus

from xquotient.test.test_workflow import DummyMessageImplementation


class HeaderRuleTest(unittest.TestCase):
    def setUp(self):
        self.storepath = self.mktemp()
        self.store = store.Store(self.storepath)
        self.headerRule = filter.HeaderRule(
            store=self.store,
            headerName=u"subject",
            value=u"subjval",
            operation=filter.EQUALS)


    def _testImpl(self, same, notsame, casenotsame):

        def act(on):
            return self.headerRule.applyToHeaders([on])[:2]

        self.assertEquals(act(same), (True, True))
        self.assertEquals(act(notsame), (False, True))

        self.headerRule.negate = True

        self.assertEquals(act(same), (False, True))
        self.assertEquals(act(notsame), (True, True))

        self.headerRule.negate = False
        self.headerRule.shortCircuit = True

        self.assertEquals(act(same), (True, False))
        self.assertEquals(act(notsame), (False, True))

        self.headerRule.negate = True

        self.assertEquals(act(same), (False, True))
        self.assertEquals(act(notsame), (True, False))

        self.headerRule.negate = False
        self.headerRule.shortCircuit = False
        self.headerRule.caseSensitive = True

        self.assertEquals(act(same), (True, True))
        self.assertEquals(act(casenotsame), (False, True))
        self.assertEquals(act(notsame), (False, True))


    def testEquals(self):
        same = mimepart.Header(u"subject", u"subjval")
        notsame = mimepart.Header(u"subject", u"different")
        casenotsame = mimepart.Header(u"subject", u"Subjval")
        return self._testImpl(same, notsame, casenotsame)


    def testStartswith(self):
        same = mimepart.Header(u"subject", u"subjval goes here")
        notsame = mimepart.Header(u"subject", u"something else lala")
        casenotsame = mimepart.Header(u"subject", u"SUBJVAL IS THIS")
        self.headerRule.operation = filter.STARTSWITH
        return self._testImpl(same, notsame, casenotsame)


    def testEndswith(self):
        same = mimepart.Header(u"subject", u"here goes subjval")
        notsame = mimepart.Header(u"subject", u"something else lala")
        casenotsame = mimepart.Header(u"subject", u"THIS IS SUBJVAL")
        self.headerRule.operation = filter.ENDSWITH
        return self._testImpl(same, notsame, casenotsame)


    def testContains(self):
        same = mimepart.Header(u"subject", u"here subjval goes")
        notsame = mimepart.Header(u"subject", u"something else lala")
        casenotsame = mimepart.Header(u"subject", u"IS SUBJVAL THIS?")
        self.headerRule.operation = filter.CONTAINS
        return self._testImpl(same, notsame, casenotsame)



class MailingListRuleTest(unittest.TestCase):

    def setUp(self):
        self.storepath = self.mktemp()
        self.store = store.Store(self.storepath)

        self.rfp = filter.RuleFilteringPowerup(store=self.store)
        installOn(self.rfp, self.store)
        self.tagcatalog = self.rfp.tagCatalog

        self.mlfp = filter.MailingListFilteringPowerup(store=self.store)
        installOn(self.mlfp, self.store)


    def testMailingListFilter(self):
        """
        Ensures that mailing list messages are not handled by
        RuleFilteringPowerup but are handled by MailingListFilteringPowerup.
        """

        part = Part()
        part.addHeader(u'X-Mailman-Version', u"2.1.5")
        part.addHeader(u'List-Id',
                       u"Some mailing list <some-list.example.com>")
        part.source = FilePath(self.storepath).child("files").child("x")
        msg = Message.createIncoming(self.store, part,
                                     u'test://test_mailing_list_filter')

        self.rfp.processItem(msg)
        self.assertEqual(list(self.tagcatalog.tagsOf(msg)), [])

        self.mlfp.processItem(msg)
        self.assertEqual(list(self.tagcatalog.tagsOf(msg)),
                         [u'some-list.example.com'])


    def testEZMLMFilter(self):
        """
        Ensure that match_EZMLM doesn't kerplode when presented with a
        header that doesn't parse well.
        """
        part = Part()
        part.addHeader(u'X-Mailman-Version', u"2.1.5")
        part.addHeader(u'List-Post',
                       u"Random bytes")
        part.source = FilePath(self.storepath).child("files").child("x")
        msg = Message.createIncoming(self.store, part,
                                     u'test://test_mailing_list_filter')

        self.mlfp.processItem(msg)
        self.assertEqual(list(self.tagcatalog.tagsOf(msg)),
                         [])



class FocusTests(TestCase):
    """
    Tests for the code which determines if a message is focused or not.
    """
    def setUp(self):
        """
        Create a site store and a user store with the L{Focus} powerup.
        """
        # Make the site store within which the test user will be created.
        self.dbdir = self.mktemp()
        self.siteStore = Store(self.dbdir)
        Mantissa().installSite(self.siteStore, u'example.com', u"", False)

        # Create a store for the user which is set up appropriately.
        self.userAccount = Create().addAccount(
            self.siteStore, u'testuser', u'example.com', u'password')
        self.userStore = self.userAccount.avatars.open()
        self.focus = Focus(store=self.userStore)
        installOn(self.focus, self.userStore)


    def test_suspend(self):
        """
        Make sure the suspend method does nothing.
        """
        self.focus.suspend()


    def test_resume(self):
        """
        Make sure the resume method does nothing.
        """
        self.focus.resume()


    def test_nonPart(self):
        """
        Test that a message with an implementation which isn't a L{Part} that
        the Message doesn't get focused.

        This is primarily here for completeness at this point.  The only
        non-Part Messages which exist are probably created by the test suite.
        """
        impl = DummyMessageImplementation(store=self.userStore)
        message = Message.createIncoming(
            self.userStore, impl, u'test://test_nonPart')
        self.focus.processItem(message)
        statuses = set(message.iterStatuses())
        self.failIfIn(FOCUS_STATUS, statuses)


    def _focusedTest(self, part):
        message = Message.createIncoming(
            self.userStore, part, u'test://test_otherPrecedence')
        self.focus.processItem(message)
        statuses = set(message.iterStatuses())
        self.failUnlessIn(FOCUS_STATUS, statuses)


    def _unfocusedTest(self, part):
        message = Message.createIncoming(
            self.userStore, part, u'test://unfocused')
        self.focus.processItem(message)
        statuses = set(message.iterStatuses())
        self.failIfIn(FOCUS_STATUS, statuses)


    def test_bulkPrecedence(self):
        """
        Test that an email message with C{bulk} precedence is not focused.
        """
        impl = Part()
        impl.addHeader(u'Precedence', u'bulk')
        self._unfocusedTest(impl)

        impl = Part()
        impl.addHeader(u'Precedence', u'BuLK')
        self._unfocusedTest(impl)


    def test_listPrecedence(self):
        """
        Test that an email message with C{list} precedence is not focused.
        """
        impl = Part()
        impl.addHeader(u'Precedence', u'list')
        self._unfocusedTest(impl)

        impl = Part()
        impl.addHeader(u'Precedence', u'LIsT')
        self._unfocusedTest(impl)


    def test_otherPrecedence(self):
        """
        Test that an email message with some random other precedence header
        value is focused.
        """
        impl = Part()
        impl.addHeader(u'Precedence', u'made up random value')
        self._focusedTest(impl)


    def test_noPrecedence(self):
        """
        Test that an email message with no precedence header is focused.
        """
        impl = Part()
        self._focusedTest(impl)


    def test_draft(self):
        """
        Verify that a draft is not focused.
        """
        impl = Part()
        message = Message.createDraft(
            self.userStore, impl, u'test://test_draft')
        self.focus.processItem(message)
        statuses = set(message.iterStatuses())
        self.failIfIn(FOCUS_STATUS, statuses)


    def test_outbox(self):
        """
        Verify that a message in the outbox is not focused.
        """
        impl = Part()
        message = Message.createDraft(
            self.userStore, impl, u'test://test_outbox')
        message.startedSending()
        self.focus.processItem(message)
        statuses = set(message.iterStatuses())
        self.failIfIn(FOCUS_STATUS, statuses)


    def test_bounced(self):
        """
        Verify that a message which has bounced is not focused.
        """
        impl = Part()
        message = Message.createDraft(
            self.userStore, impl, u'test://test_bounced')
        message.startedSending()
        message.allBounced()
        self.focus.processItem(message)
        statuses = set(message.iterStatuses())
        self.failIfIn(FOCUS_STATUS, statuses)


    def test_partiallySent(self):
        """
        Verify that a message which has been sent to one recipient is not
        focused.
        """
        impl = Part()
        message = Message.createDraft(
            self.userStore, impl, u'test://test_partiallySent')
        message.startedSending()
        message.sent()
        self.focus.processItem(message)
        statuses = set(message.iterStatuses())
        self.failIfIn(FOCUS_STATUS, statuses)


    def test_finishedSending(self):
        """
        Verify that a message which has been sent to all recipients is not
        focused.
        """
        impl = Part()
        message = Message.createDraft(
            self.userStore, impl, u'test://test_finishedSending')
        message.startedSending()
        message.sent()
        message.finishedSending()
        self.focus.processItem(message)
        statuses = set(message.iterStatuses())
        self.failIfIn(FOCUS_STATUS, statuses)
