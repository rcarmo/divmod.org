from zope.interface import implements

from epsilon.extime import Time

from axiom.iaxiom import IScheduler
from axiom.item import Item
from axiom.attributes import text
from axiom.test.historic.stubloader import StubbedTest

from xquotient.exmess import _UndeferTask, Message, INBOX_STATUS, CLEAN_STATUS
from xquotient.test.historic.stub_undefertask1to2 import FakeScheduler
from xquotient.test.historic import stub_undefertask1to2
from xquotient.test.util import DummyMessageImplementationMixin


class DummyMessageImplementation(Item, DummyMessageImplementationMixin):
    """
    Satisfy the requirement imposed by this database to have an item with
    this type name.

    This is an extremely terrible hack necessitated by the use of "dummy"
    items in the test package which aren't actually stable.  This should be
    avoided as much as possible, since it can easily result in tests which
    have mutually exclusive requirements in order to pass, and at the very
    least impose an excessive maintenance burden as the codebase is updated.

    Do not copy this hack.  Do not define new schemas which might eventually
    require it.
    """
    typeName = 'xquotient_test_test_workflow_dummymessageimplementation'
    senderInfo = text(
        doc="""
        The sender as passed by the factory which created this implementation;
        used to provide a sensible implementation of relatedAddresses.
        """,
        default=None, allowNone=True)

    def walk(self):
        """
        Necessary for the tests for upgrading Message to version 6.
        """
        return ()

class UndeferTaskTest(StubbedTest):
    def setUp(self):
        stub_undefertask1to2.SCHEDULE_LOG = []
        return StubbedTest.setUp(self)


    def getStatuses(self):
        """
        @return: A C{set} of statuses for the deferred message.
        """
        return set(self.store.findFirst(Message).iterStatuses())


    def test_correctScheduling(self):
        """
        Check that the old task has been unscheduled and the new task has been
        scheduled.
        """
        task = self.store.findFirst(_UndeferTask)
        self.assertEqual(list(zip(*stub_undefertask1to2.SCHEDULE_LOG)[0]),
                          ['unschedule', 'schedule'])
        self.assertEqual(stub_undefertask1to2.SCHEDULE_LOG[-1][1], task)
        self.assertNotEqual(stub_undefertask1to2.SCHEDULE_LOG[0][1], task)


    def test_notInInbox(self):
        """
        Test that the deferred message is not in the inbox.
        """
        stats = self.getStatuses()
        self.failIfIn(INBOX_STATUS, stats)


    def test_inAll(self):
        """
        Test that the deferred message does appear in the "all" view.
        """
        stats = self.getStatuses()
        self.failUnlessIn(CLEAN_STATUS, stats)


    def test_notFrozen(self):
        """
        Test that the deferred message is not 'frozen' with
        L{Message.freezeStatus}.
        """
        # NOTE: This is added as documentation, not TDD -- it passes already.
        for status in self.getStatuses():
            self.failIf(status.startswith('.'))
