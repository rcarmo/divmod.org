
from axiom.test.historic.stubloader import StubbedTest

from xquotient.exmess import (Message, MailboxSelector,
                              INBOX_STATUS,
                              ARCHIVE_STATUS,
                              UNREAD_STATUS,
                              READ_STATUS,
                              DEFERRED_STATUS,
                              DRAFT_STATUS,
                              CLEAN_STATUS,
                              SENT_STATUS)

from xmantissa.people import Person, EmailAddress as PersonEmailAddress

class MessageUpgradeTest(StubbedTest):

    def assertMessages(self, statuses, messageIndexes):
        """
        Fail this test unless the result of a listing of given message statuses
        matches the given message indices.

        @param statuses: a list of unicode status strings.

        @param messageIndexes: a list of message indexes.
        """
        sq = MailboxSelector(self.store)
        for statusName in statuses:
            sq.refineByStatus(statusName)
        self.assertMessageQuery(sq, messageIndexes)

    def assertMessageQuery(self, ms, messageIndexes):
        """
        Fail this test unless the result of a given mailbox selector matches
        the given message indices.

        @param statuses: a list of unicode status strings.

        @param messageIndexes: a list of message indexes.
        """
        self.assertEquals(
            set(map(self.messageList.index, list(ms))),
            set(messageIndexes))

    def setUp(self):
        """
        Load stub as usual, then set up properly ordered list for
        assertMessages.
        """
        r = super(MessageUpgradeTest, self).setUp()
        def setupList(result):
            self.messageList = list(
                self.store.query(Message, sort=Message.storeID.ascending))

        return r.addCallback(setupList)


    def test_upgradeFlagsToStatuses(self):
        """
        Verify that messages upgraded from the stub have appropriate statuses.
        """
        self.assertMessages([INBOX_STATUS], [0])
        self.assertMessages([ARCHIVE_STATUS], [1])
        self.assertMessages([UNREAD_STATUS], [0, 1, 3, 4, 5, 6, 7])
        self.assertMessages([READ_STATUS], [2])
        self.assertMessages([DEFERRED_STATUS], [2])
        self.assertMessages([DRAFT_STATUS], [4])
        self.assertMessages([CLEAN_STATUS], [0, 1, 2])
        # Really tested by workflow tests, but sanity check:
        self.assertMessages([UNREAD_STATUS, CLEAN_STATUS], [0, 1])
        self.assertMessages([SENT_STATUS], [3])


    def test_upgradeCorrespondents(self):
        """
        Verify that Correspondent items are created for each incoming message,
        so that 'view from person' still works.
        """
        ms = MailboxSelector(self.store)
        newPerson = Person(store=self.store, name=u'test bob')
        PersonEmailAddress(store=self.store, person=newPerson,
                           address=u'bob@b.example.com')
        ms.refineByPerson(newPerson)
        # As it currently stands, outgoing and draft messages are both not
        # considered for the addition of Correspondent items.  This might not
        # be correct, but it is the current behavior and at the time of writing
        # this test the goal was to ensure that the behavior would not change
        # across this upgrade.  -glyph
        self.assertMessageQuery(ms, [0, 1, 2, 5, 6, 7])
