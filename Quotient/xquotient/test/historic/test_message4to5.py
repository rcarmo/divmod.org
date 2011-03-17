
"""
Tests for the upgrader from version 4 to version 5 of quotient's Message
item.
"""

from epsilon.extime import Time

from axiom.test.historic.stubloader import StubbedTest

from xquotient.exmess import (Message, MailboxSelector,
                              INBOX_STATUS,
                              ARCHIVE_STATUS,
                              UNREAD_STATUS,
                              READ_STATUS,
                              DEFERRED_STATUS,
                              DRAFT_STATUS,
                              CLEAN_STATUS,
                              SENT_STATUS,
                              SPAM_STATUS,
                              TRASH_STATUS)

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


    def test_statusesStayTheSame(self):
        """
        Verify that messages upgraded from the stub have appropriate statuses.
        """
        self.assertMessages([INBOX_STATUS], [0])
        self.assertMessages([ARCHIVE_STATUS], [1])
        self.assertMessages([UNREAD_STATUS], [0, 1, 3, 4, 5, 6, 7])
        self.assertMessages([READ_STATUS], [2])
        self.assertMessages([DEFERRED_STATUS], [2])
        self.assertMessages([DRAFT_STATUS], [4])
        # this next check here verifies that the 'CLEAN_STATUS' was unfrozen by
        # the upgrader.
        self.assertMessages([CLEAN_STATUS], [0, 1, 2])
        # Really tested by workflow tests, but sanity check:
        self.assertMessages([UNREAD_STATUS, CLEAN_STATUS], [0, 1])
        self.assertMessages([SENT_STATUS], [3])
        self.assertMessages([TRASH_STATUS], [5, 6])
        self.assertMessages([SPAM_STATUS], [7])


    def test_attributes(self):
        """
        Verify all the attributes directly on the Message class are preserved
        by the upgrade function.
        """

        for i, msg in enumerate(self.messageList):
            # The code at the revision which this stub requires randomly
            # mangles the sentWhen of the 3rd and 4th message (because they're
            # drafts), so we can't reasonably test them, except to make sure
            # they're not none.
            if i == 3 or i == 4:
                self.assertNotEqual(msg.sentWhen, None)
            else:
                self.assertEqual(
                    msg.sentWhen,
                    Time.fromRFC2822("Thu, 26 Apr 2001 22:01:%d GMT" % (i,)))

            # Received when is set to the time the stub is generated!  So we
            # can only test for non-Noneness.
            self.assertNotEqual(msg.receivedWhen, None)

            self.assertEqual(msg.sender, u"bob@b.example.com")
            self.assertEqual(msg.senderDisplay, u"bob@b.example.com")
            self.assertEqual(msg.recipient, u"alice@a.example.com")
            self.assertEqual(msg.subject, u"message number %d" % (i,))
            self.assertEqual(msg.attachments, i * 2)
            self.assertEqual(msg.read, i == 2)
            self.assertEqual(msg.everDeferred, i == 1 or i == 2)

            if i == 0 or i == 1 or i == 2 or i == 5:
                _spam = False
            elif i == 3 or i == 4:
                _spam = None
            elif i == 6 or i == 7:
                _spam = True
            self.assertEqual(msg._spam, _spam)

            self.assertEqual(msg.shouldBeClassified, not (i == 3 or i == 4 or i == 7))

            self.assertEqual(msg.impl.getHeader(u"subject"), msg.subject)

            if i == 7:
                frozenWith = SPAM_STATUS
            elif i == 5 or i == 6:
                frozenWith = TRASH_STATUS
            else:
                frozenWith = None

            self.assertEqual(msg._frozenWith, frozenWith)

