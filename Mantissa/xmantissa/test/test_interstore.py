
"""

Tests for inter-store messaging module, L{xmantissa.messaging}.

This module contains tests for persistent messaging between different accounts.

"""

import gc
from datetime import timedelta

from zope.interface import implements

from twisted.trial.unittest import TestCase
from twisted.internet.defer import Deferred

from twisted.protocols.amp import Box, Command, Integer, String

from epsilon.extime import Time

from axiom.iaxiom import IScheduler
from axiom.store import Store
from axiom.errors import UnsatisfiedRequirement
from axiom.item import Item, POWERUP_BEFORE
from axiom.attributes import text, bytes, integer, boolean, inmemory

from axiom.userbase import LoginSystem, LoginMethod, LoginAccount

from axiom.dependency import installOn

from axiom.scheduler import TimedEvent

from xmantissa.interstore import (
    # Public Names
    MessageQueue, AMPMessenger, LocalMessageRouter, Value,
    AMPReceiver, commandMethod, answerMethod, errorMethod,
    SenderArgument, TargetArgument,

    # Constants
    AMP_MESSAGE_TYPE, AMP_ANSWER_TYPE, DELIVERY_ERROR,

    # Error Types
    ERROR_REMOTE_EXCEPTION, ERROR_NO_SHARE, ERROR_NO_USER, ERROR_BAD_SENDER,

    # Private Names
    _RETRANSMIT_DELAY, _QueuedMessage, _AlreadyAnswered, _FailedAnswer,
    _AMPExposer, _AMPErrorExposer)

from xmantissa.sharing import getEveryoneRole, Identifier
from xmantissa.error import (
    MessageTransportError, BadSender, UnknownMessageType, RevertAndRespond,
    MalformedMessage)
from xmantissa.ixmantissa import IMessageReceiver, IMessageRouter

class SampleException(Exception):
    """
    Something didn't happen because of a problem.
    """



class StubReceiver(Item):
    """
    This is a message receiver that will store a message sent to it for
    inspection by tests.
    """
    implements(IMessageReceiver)

    messageType = text(
        doc="""
        The message type which C{messageReceived} should put into its return
        value.
        """)
    messageData = bytes(
        doc="""
        The message data which C{messageReceived} should put into its return
        value.
        """)
    inconsistent = boolean(
        doc="""
        This value is set to True during the execution of C{messageReceived},
        but False afterwards.  If everything is properly transactional it
        should never be observably false by other code.
        """)

    buggy = boolean(allowNone=False, default=False,
                    doc="""
                    C{messageReceived} should raise a L{SampleException}.
                    """)

    badReturn = boolean(allowNone=False, default=False,
                        doc="""
                        C{messageReceived} should return L{None}.
                        """)

    receivedCount = integer(default=0,
                            doc="""
                            This is a counter of the number of messages
                            received by C{messageReceived}.
                            """)

    reciprocate = boolean(allowNone=False, default=False,
                          doc="""
                          C{messageReceived} should respond to its C{sender}
                          parameter with a symmetric message in addition to
                          answering.
                          """)

    revertType = text(allowNone=True,
                      doc="""
                      If set, this specifies the type of the
                      L{RevertAndRespond} exception that C{messageReceived}
                      should raise.
                      """)

    revertData = bytes(allowNone=True,
                       doc="""
                       If C{revertType} is set, this specifies the data of the
                       L{RevertAndRespond} exception that C{messageReceived}
                       should raise.
                       """)


    def messageQueue(self):
        """
        This is a temporary workaround; see ticket #2640 for details on the way
        this method should be implemented in the future.
        """
        return self.store.findUnique(MessageQueue)


    def messageReceived(self, value, sender, receiver):
        """
        A message was received.  Increase the message counter and store its
        contents.
        """
        self.receivedCount += 1
        self.messageType = value.type
        self.messageData = value.data
        self.inconsistent = True
        if self.buggy:
            raise SampleException("Sample Message")
        if self.revertType is not None:
            raise RevertAndRespond(Value(self.revertType,
                                            self.revertData))
        self.inconsistent = False
        if self.badReturn:
            return None
        if self.reciprocate:
            self.messageQueue().queueMessage(
                receiver, sender, Value(value.type + u'.response',
                                           value.data + ' response'))
        return Value(u"custom.message.type", "canned response")



class StubSlowRouter(Item):
    """
    Like L{LocalMessageRouter}, but don't actually deliver the messages until
    the test forces them to be delivered.

    By way of several parameters to `flushMessages`, this stub implementation
    allows for all of the arbitrary ways in which a potential networked
    implementation is allowed to behave - dropping messages, repeating
    messages, and even failing in buggy ways.

    Note: this must be kept in memory for the duration of any test using it.

    @ivar messages: a list of (sender, target, value, messageID) tuples
    received by routeMessage.

    @ivar acks: a list of (deferred, (sender, target, value, messageID))
    tuples, representing an answer received by routeAnswer and the deferred
    that was returned to indicate its delivery.
    """

    dummy = integer(
        doc="""
        No state on this item is persistent; this is just to satisfy Axiom's schema
        requirement.
        """)

    messages = inmemory()
    acks = inmemory()

    def localRouter(self):
        """
        Return a L{LocalMessageRouter} for this slow router's store.
        """
        return LocalMessageRouter(self.store.findUnique(LoginSystem))


    def activate(self):
        """
        Initialize temporary list to queue messages.
        """
        self.messages = []
        self.acks = []


    def routeMessage(self, sender, target, value, messageID):
        """
        Stub implementation of L{IMessageRouter.routeMessage} that just appends
        to a list in memory, and later delegates from that list to the local
        router.
        """
        self.messages.append((sender, target, value, messageID))


    def routeAnswer(self, originalSender, originalTarget, value, messageID):
        """
        Stub implementation of L{IMessageRouter.routeAnswer} that just
        appends to a list in memory.
        """
        D = Deferred()
        self.acks.append((D, (originalSender, originalTarget, value,
                              messageID)))
        return D


    def flushMessages(self, dropAcks=False,
                      dropAckErrorType=MessageTransportError,
                      stallAcks=False,
                      repeatAcks=False):
        """
        Delegate all messages queued in memory with routeMessage to the
        specified local router.

        @param dropAcks: a boolean, indicating whether to drop the answers
        queued by routeAnswer.

        @param dropAckErrorType: an exception type, indicating what exception
        to errback the Deferreds returned by routeAnswer with.

        @param stallAcks: a boolean, indicating whether to keep, but not act,
        on the answers queued by routeAnswer.

        @param repeatAcks: a boolean, indicating whether to repeat all of the
        acks the next time flushMessages is called.
        """
        m = self.messages[:]
        self.messages = []
        for message in m:
            self.localRouter().routeMessage(*message)
        if dropAcks:
            for D, ack in self.acks:
                D.errback(dropAckErrorType())
            self.acks = []
        if not stallAcks:
            for D, ack in self.acks:
                self.localRouter().routeAnswer(*ack).chainDeferred(D)
            if repeatAcks:
                # the Deferreds are used up, so we need a fresh batch for the
                # next run-through (although these will be ignored)
                self.acks = [(Deferred(), ack) for (D, ack) in self.acks]
            else:
                self.acks = []


    def spuriousDeliveries(self):
        """
        Simulate a faulty transport, and deliver all the currently pending
        messages without paying attention to their results.
        """
        for message in self.messages:
            self.localRouter().routeMessage(*message)



class StubDeliveryConsequence(Item):
    """
    This implements a delivery consequence.

    @ivar responses: a tuple of (answer-type, answer-data, message-type,
    message-data, sender, target), listing all the answers received by
    answerReceived.

    @ivar bucket: a list which will have this L{StubDeliveryConsequence}
    appended to it when a successful message is processed.
    """

    responses = inmemory()
    bucket = inmemory()

    invocations = integer(
        """
        Counter, keeping track of how many times this consequence has been
        invoked.
        """,
        default=0, allowNone=False)

    succeeded = boolean(
        """
        Did the action succeed?  None if it hasn't completed, True if yes,
        False if no.
        """)

    inconsistent = boolean(
        """
        This should never be set to True.  It's set to None by default, False
        when the callback fully succeeds.
        """)

    buggy = boolean(
        """
        Set this to cause 'success' to raise an exception.
        """,
        default=False,
        allowNone=False)

    def activate(self):
        """
        Initialize the list of received responses.
        """
        self.responses = []
        self.bucket = []


    def success(self):
        """
        A response was received to the message.  This will be executed in a
        transaction.  Raise an exception if this consequence is buggy.
        """
        self.bucket.append(self)
        self.inconsistent = True
        self.invocations += 1
        self.succeeded = True
        if self.buggy:
            raise SampleException()
        self.inconsistent = False


    def failure(self):
        """
        The message could not be delivered for some reason.  This will be
        executed in a transaction.  Raise an exception if this consequence is
        buggy.

        @param reason: an exception.
        """
        self.invocations += 1
        self.succeeded = False


    def answerReceived(self, answerValue, originalValue,
                       originalSender, originalTarget):
        """
        An answer was received.
        """
        if answerValue.type == DELIVERY_ERROR:
            self.failure()
        else:
            self.success()
        # It's important that this happen after the "application" logic so that
        # the tests will not see this set if an exception has been raised.
        self.responses.append((answerValue.type, answerValue.data,
                               originalValue.type, originalValue.data,
                               originalSender, originalTarget))



class TimeFactory(object):
    """
    Make a fake time factory.
    """

    def __init__(self):
        """
        Create a time factory with some default values.
        """
        self.currentSeconds = 0.0


    def advance(self):
        """
        Advance the current time by one second.
        """
        self.currentSeconds += 1.0


    def next(self):
        """
        Produce the next time in the sequence, then advance.
        """
        self.advance()
        return Time.fromPOSIXTimestamp(self.currentSeconds)


    def peek(self):
        """
        Return the value that will come from the next call to 'next'.
        """
        return Time.fromPOSIXTimestamp(self.currentSeconds + 1)



class SingleSiteMessagingTests(TestCase):
    """
    These are tests for messaging within a single configured site store.
    """

    def setUp(self):
        """
        Create a site store with two users that can send messages to each
        other.
        """
        self.siteStore = Store()
        self.time = TimeFactory()
        self.loginSystem = LoginSystem(store=self.siteStore)
        installOn(self.loginSystem, self.siteStore)

        self.aliceAccount = self.loginSystem.addAccount(
            u"alice", u"example.com", u"asdf", internal=True)
        self.bobAccount = self.loginSystem.addAccount(
            u"bob", u"example.com", u"asdf", internal=True)

        self.aliceStore, self.aliceQueue = self.accountify(
            self.aliceAccount.avatars.open())
        self.bobStore, self.bobQueue = self.accountify(
            self.bobAccount.avatars.open())

        # I need to make a target object with a message receiver installed on
        # it.  Then I need to share that object.
        self.receiver = StubReceiver(store=self.bobStore)
        getEveryoneRole(self.bobStore).shareItem(self.receiver, u"suitcase")

        self.retransmitDelta = timedelta(seconds=_RETRANSMIT_DELAY)


    def accountify(self, userStore):
        """
        Add a MessageQueue to the given user store and stub out its scheduler's
        time function.
        """
        queue = MessageQueue(store=userStore)
        installOn(queue, userStore)
        IScheduler(userStore).now = self.time.peek
        return userStore, queue


    def runQueue(self, queue):
        """
        Advance the current time and run the given message queue.
        """
        self.time.advance()
        return queue.run()


    def test_bogusConfiguration(self):
        """
        Delivering a message on a site without a L{LoginSystem} should cause an
        L{UnsatisfiedRequirement} exception to be logged, and the message not
        to be delivered.
        """
        self.loginSystem.deleteFromStore()
        self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        [err] = self.flushLoggedErrors(UnsatisfiedRequirement)
        # The message should still be queued.
        self.assertEqual(len(list(self.aliceStore.query(_QueuedMessage))),
                         1)


    def unattachedUserStore(self):
        """
        Create a store that is structured as if it was a user-store with
        messaging enabled, but was opened un-attached from its parent store.

        @return: a 2-tuple of (store, queue).
        """
        carolStore, carolQueue = self.accountify(Store())
        acct = LoginAccount(store=carolStore, password=u'asdf')
        lm = LoginMethod(store=carolStore, localpart=u'carol',
                         domain=u'example.com', internal=True, protocol=u'*',
                         account=acct, verified=True)
        return carolStore, carolQueue


    def test_accidentallyOpenAsSite(self):
        """
        If a message delivery is somehow attempted with a user store
        accidentally opened as a site store, delivery should fail.

        Normally this will not happen, since the current implementation (as of
        when this test was written) of the scheduler will not allow timed
        events to run with a L{SubScheduler} installed rather than a
        L{Scheduler}.  However, eliminating this distinction is a long-term
        goal, so this test is a defense against both future modifications and
        other code which may emulate scheduler APIs.
        """
        carolStore, carolQueue = self.unattachedUserStore()
        sdc = StubDeliveryConsequence(store=carolStore)
        carolQueue.queueMessage(
            Identifier(u"nothing", u"carol", u"example.com"),
            Identifier(u"suitcase", u"bob", u"example.com"),
            Value(u'custom.message.type', "Some message contents"), sdc)
        self.runQueue(carolQueue)
        [err] = self.flushLoggedErrors(UnsatisfiedRequirement)
        # The message should still be queued.
        self.assertEqual(len(list(carolStore.query(_QueuedMessage))), 1)


    def test_accidentallyAnswerAsSite(self):
        """
        If an answer delivery is somehow attempted with a user store
        accidentally opened as a site store, the delivery should result in a
        transient failure.

        This is even less likely than the case described in
        L{test_accidentallyOpenAsSite}, but in the unlikely event that the
        scheduler is manually run, it still shouldn't result in any errors
        being logged or state being lost.
        """
        carolStore, carolQueue = self.unattachedUserStore()
        carolReceiver = StubReceiver(store=carolStore)
        getEveryoneRole(carolStore).shareItem(carolReceiver, u'some-share-id')
        bogusID = Identifier(u'nothing', u'nobody', u'nowhere')
        carolID = Identifier(u'some-share-id', u'carol', u'example.com')
        carolQueue.routeMessage(bogusID, carolID, Value(u'no.type', 'contents'), 1)
        [err] = self.flushLoggedErrors(UnsatisfiedRequirement)
        # The answer should still be queued.
        self.assertEqual(len(list(carolStore.query(_AlreadyAnswered))), 1)


    def test_queueMessageSimple(self):
        """
        Queuing a message should create a _QueuedMessage object and schedule it
        for delivery to its intended recipient.
        """

        # Maybe I should do this by sharing an object in Alice's store and then
        # wrapping a SharingView-type thing around it?  it seems like there
        # ought to be a purely model-level API for this, though.
        self.aliceQueue.queueMessage(
            Identifier(u"nothing", u"alice", u"example.com"),
            Identifier(u"suitcase", u"bob", u"example.com"),
            Value(u"custom.message.type", "This is an important message."))

        # OK now let's find the message that was queued.
        qm = self.aliceStore.findUnique(_QueuedMessage)
        self.assertEqual(qm.senderUsername, u'alice')
        self.assertEqual(qm.senderDomain, u'example.com')

        # Can you do this?  It seems like it might be inconvenient to always
        # determine a resolvable "return address" - the test case here is a
        # simulation of reasonable behavior; alice hasn't shared anything.
        # self.assertEqual(qm.senderShareID, None)
        self.assertEqual(qm.targetUsername, u"bob")
        self.assertEqual(qm.targetDomain, u"example.com")
        self.assertEqual(qm.targetShareID, u"suitcase")
        self.assertEqual(qm.value.type, u"custom.message.type")
        self.assertEqual(qm.value.data, "This is an important message.")

        # It should be scheduled.  Is there a timed event?
        te = self.aliceStore.findUnique(
            TimedEvent,
            TimedEvent.runnable == self.aliceQueue)

        # It should be scheduled immediately.  This uses the real clock, but in
        # a predictable way (i.e. if time does not go backwards, then this will
        # work).  If this test ever fails intermittently there _is_ a real
        # problem.
        self.assertNotIdentical(te.time, None)
        self.failUnless(te.time <= Time())
        runresult = self.runQueue(self.aliceQueue)

        # It should succeed, it should not reschedule itself; the scheduler
        # will delete things that return None from run().  It would be nice to
        # integrate with the scheduler here, but that would potentially drag in
        # dependencies on other systems not scheduling stuff.
        self.assertEqual(runresult, None)

        self.assertEqual(self.receiver.messageData,
                         "This is an important message.")
        self.assertEqual(self.receiver.messageType, u"custom.message.type")
        self.assertEqual(list(self.aliceStore.query(_QueuedMessage)), [])


    def aliceToBobWithConsequence(self, buggy=False):
        """
        Queue a message from Alice to Bob with a supplied
        L{StubDeliveryConsequence} and return it.
        """
        sdc = StubDeliveryConsequence(store=self.aliceStore,
                                      buggy=buggy)
        self.aliceQueue.queueMessage(
            Identifier(u"nothing", u"alice", u"example.com"),
            Identifier(u"suitcase", u"bob", u"example.com"),
            Value(u'custom.message.type', "Some message contents"), sdc)
        return sdc


    def checkOneResponse(self, sdc,
                         expectedType=u"custom.message.type",
                         expectedData="canned response",
                         originalSender=
                         Identifier(u"nothing", u"alice", u"example.com"),
                         originalTarget=
                         Identifier(u"suitcase", u"bob", u"example.com"),
                         succeeded=None):
        """
        This checks that the response received has the expected type and data,
        and corresponds to the sender and target specified by
        L{SingleSiteMessagingTests.aliceToBobWithConsequence}.
        """
        if succeeded is None:
            if expectedType == DELIVERY_ERROR:
                succeeded = False
            else:
                succeeded = True
        # First, let's make sure that transaction committed.
        self.assertEqual(sdc.succeeded, succeeded)
        self.assertEqual(sdc.responses,
                         [(expectedType, expectedData,
                           u'custom.message.type', # type
                           "Some message contents", # data
                           originalSender, originalTarget
                           )])


    def test_queueMessageSuccessNotification(self):
        """
        Queueing a message should emit a success notification to the supplied
        'consequence' object.
        """
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        self.assertEqual(sdc.succeeded, True)
        self.checkOneResponse(sdc)


    def test_queueMessageSuccessErrorHandling(self):
        """
        If the supplied 'consequence' object is buggy, the error should be
        logged so that the answer can be processed later, but not propagated to
        the network layer.
        """
        sdc = self.aliceToBobWithConsequence(True)
        self.runQueue(self.aliceQueue)
        # It should be run in a transaction so none of the stuff set by
        # 'success' should be set
        self.assertEqual(sdc.succeeded, None)
        self.assertEqual(sdc.inconsistent, None)
        self.assertEqual(sdc.invocations, 0)
        [err] = self.flushLoggedErrors(SampleException)

        # Make sure that no messages are queued.
        self.assertEqual(list(self.aliceStore.query(_QueuedMessage)), [])
        failures = list(self.aliceStore.query(_FailedAnswer))
        self.assertEqual(len(failures), 1)

        # Fix the bug.  In normal operation this would require a code upgrade.
        sdc.buggy = False
        failures[0].redeliver()
        self.checkOneResponse(sdc)


    def test_alreadyAnsweredRemoval(self):
        """
        L{_AlreadyAnswered} records should be removed after the deferred from
        L{routeAnswer} is fired.
        """
        slowRouter = self.stubSlowRouter()
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        slowRouter.flushMessages(stallAcks=True)
        self.assertEqual(len(slowRouter.acks), 1)
        # sanity check
        self.assertEqual(self.bobStore.query(_AlreadyAnswered).count(), 1)
        slowRouter.flushMessages()
        self.assertEqual(self.bobStore.query(_AlreadyAnswered).count(), 0)


    def test_repeatedAnswer(self):
        """
        If answers are repeated, they should only be processed once.
        """
        slowRouter = self.stubSlowRouter()
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        slowRouter.flushMessages(repeatAcks=True)
        slowRouter.flushMessages()
        self.assertEqual(sdc.invocations, 1)


    def _reschedulingTest(self, errorType):
        """
        Test for rescheduling of L{_AlreadyAnswered} results in the presence of
        the given error from the router.
        """
        slowRouter = self.stubSlowRouter()
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        slowRouter.flushMessages(dropAcks=True, dropAckErrorType=errorType)
        # It should be scheduled.
        self.assertEqual(
            len(list(IScheduler(self.bobQueue.store).scheduledTimes(self.bobQueue))),
            1)
        # Now let's run it and see if the ack gets redelivered.
        self.runQueue(self.bobQueue)
        slowRouter.flushMessages()
        self.assertEqual(sdc.succeeded, True)


    def test_alreadyAnsweredReschedule(self):
        """
        L{_AlreadyAnswered} records should be scheduled for retransmission if
        the L{Deferred} from L{routeAnswer} is errbacked with a
        L{MessageTransportError}.  No message should be logged, since this is a
        transient and potentially expected error.
        """
        self._reschedulingTest(MessageTransportError)


    def test_alreadyAnsweredRescheduleAndLog(self):
        """
        L{_AlreadyAnswered} records should be scheduled for retransmission if
        the L{Deferred} from L{routeAnswer} is errbacked with an unknown
        exception type, and the exception should be logged.
        """
        self._reschedulingTest(SampleException)
        [err] = self.flushLoggedErrors(SampleException)


    def test_alreadyAnsweredRescheduleCrash(self):
        """
        L{_AlreadyAnswered} records should be scheduled for retransmission if
        the L{Deferred} from L{routeAnswer} dies without being callbacked or
        errbacked (such as if the store were to crash).
        """
        slowRouter = self.stubSlowRouter()
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        slowRouter.flushMessages(stallAcks=True)
        self.assertEqual(sdc.invocations, 0)
        slowRouter.acks = []
        gc.collect()
        # Make sure the Deferred is well and truly gone.
        self.assertIdentical(
            self.bobStore.findUnique(_AlreadyAnswered).deliveryDeferred,
            None)
        self.runQueue(self.bobQueue)
        slowRouter.flushMessages()
        self.assertEqual(sdc.invocations, 1)


    def test_noRemoteUser(self):
        """
        What if the target user we're trying to talk to doesn't actually exist
        in the system?  The message delivery should fail.
        """
        sdc = StubDeliveryConsequence(store=self.aliceStore)
        self.aliceQueue.queueMessage(
            Identifier(u"nothing", u"alice", u"example.com"),
            Identifier(u"suitcase", u"bohb", u"example.com"),
            Value(u"custom.message.type", "Some message contents"), sdc)
        self.runQueue(self.aliceQueue)
        self.assertEqual(sdc.succeeded, False)
        self.checkOneResponse(
            sdc, DELIVERY_ERROR, ERROR_NO_USER,
            originalTarget=Identifier(u"suitcase", u"bohb", u"example.com"))
        self.assertEqual(sdc.invocations, 1)


    def test_noRemoteShare(self):
        """
        Similarly, if there's nothing identified by the shareID specified, the
        message delivery should fail.
        """
        sdc = StubDeliveryConsequence(store=self.aliceStore)
        self.aliceQueue.queueMessage(
            Identifier(u"nothing", u"alice", u"example.com"),
            Identifier(u"nothing", u"bob", u"example.com"),
            Value(u"custom.message.type", "Some message contents"), sdc)
        self.runQueue(self.aliceQueue)
        self.assertEqual(sdc.succeeded, False)
        self.checkOneResponse(
            sdc, DELIVERY_ERROR, ERROR_NO_SHARE,
            originalTarget=Identifier(u"nothing", u"bob", u"example.com"))
        self.assertEqual(sdc.invocations, 1)


    def buggyReceiverTest(self, exceptionType):
        """
        Run a test expecting the receiver to fail.
        """
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        self.assertEqual(sdc.succeeded, False)
        self.checkOneResponse(sdc, DELIVERY_ERROR, ERROR_REMOTE_EXCEPTION)
        [err] = self.flushLoggedErrors(exceptionType)
        self.assertEqual(sdc.invocations, 1)
        self.assertEqual(self.receiver.inconsistent, None)


    def test_messageReceivedBadReturn(self):
        """
        When L{messageReceived} does not properly return a 2-tuple, that
        resulting exception should be reported to the delivery consequence of
        the message.  The target database should not be left in an inconsistent
        state.
        """
        self.receiver.badReturn = True
        self.buggyReceiverTest(TypeError)


    def test_messageReceivedException(self):
        """
        When L{messageReceived} raises an exception, that exception should be
        reported to the delivery consequence of the message.  The target
        database should not be left in an inconsistent state.
        """
        self.receiver.buggy = True
        self.buggyReceiverTest(SampleException)


    def test_revertAndRespond(self):
        """
        When L{messageReceived} raises the special L{RevertAndRespond}
        exception, the values passed to the exception should be used to
        generate the response, but the transaction should be reverted.
        """
        t = self.receiver.revertType = u'custom.reverted.type'
        d = self.receiver.revertData = "this is some data that I reverted"
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        self.assertEqual(sdc.succeeded, True)
        self.assertEqual(sdc.inconsistent, False)
        self.assertEqual(sdc.invocations, 1)
        self.assertEqual(self.receiver.inconsistent, None)
        self.checkOneResponse(sdc, t, d)


    def test_droppedException(self):
        """
        When L{messageReceived} raises an exception, that exception should be
        reported to the delivery consequence of the message, even if the
        initial transmission of the error report is lost.
        """
        slowRouter = self.stubSlowRouter()
        self.receiver.buggy = True
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        slowRouter.flushMessages(dropAcks=True)
        [err] = self.flushLoggedErrors(SampleException)
        self.runQueue(self.aliceQueue)
        slowRouter.flushMessages()
        self.assertEqual(sdc.invocations, 1)
        self.assertEqual(sdc.succeeded, False)
        self.checkOneResponse(sdc, DELIVERY_ERROR, ERROR_REMOTE_EXCEPTION)


    def test_senderNotVerified(self):
        """
        When the sender users name or domain do not match an internal, verified
        login method of the originating store, sending a message via
        queueMessage should resport an ERROR_BAD_SENDER.
        """
        sdc = StubDeliveryConsequence(store=self.aliceStore)
        self.aliceQueue.queueMessage(
            Identifier(u"nothing", u"fred", u"example.com"),
            Identifier(u"suitcase", u"bob", u"example.com"),
            Value(u"custom.message.type", "Some message contents"),
            sdc)
        self.assertEqual(sdc.invocations, 0)
        self.runQueue(self.aliceQueue)
        self.assertEqual(self.receiver.receivedCount, 0)
        self.assertEqual(sdc.succeeded, False)
        self.assertEqual(sdc.invocations, 1)
        self.checkOneResponse(sdc, DELIVERY_ERROR, ERROR_BAD_SENDER,
                              originalSender=Identifier(
                u"nothing", u"fred", u"example.com"))
        [err] = self.flushLoggedErrors(BadSender)
        bs = err.value
        self.assertEqual(bs.attemptedSender, u'fred@example.com')
        self.assertEqual(bs.allowedSenders, [u'alice@example.com'])
        self.assertEqual(str(bs),
                         "alice@example.com attempted to send message "
                         "as fred@example.com")


    def stubSlowRouter(self):
        """
        Replace this test's stub router with an artificially slowed-down
        router.
        """
        slowRouter = StubSlowRouter(store=self.siteStore)
        self.siteStore.powerUp(slowRouter, IMessageRouter, POWERUP_BEFORE)
        return slowRouter


    def test_slowDelivery(self):
        """
        If the site message-deliverer powerup returns a Deferred that takes a
        while to fire, the L{MessageQueue} should respond by rescheduling
        itself in the future.
        """
        slowRouter = self.stubSlowRouter()
        self.aliceQueue.queueMessage(
            Identifier(u"nothing", u"alice", u"example.com"),
            Identifier(u"suitcase", u"bob", u"example.com"),
            Value(u"custom.message.type", "Message2"))
        [time1] = IScheduler(self.aliceQueue.store).scheduledTimes(self.aliceQueue)
        time2 = self.runQueue(self.aliceQueue)
        self.assertEqual(time2 - self.time.peek(), self.retransmitDelta)
        self.assertEqual(self.receiver.receivedCount, 0)
        self.assertEqual(len(slowRouter.messages), 1)
        slowRouter.flushMessages()
        self.assertEqual(len(slowRouter.messages), 0)
        self.assertEqual(self.receiver.receivedCount, 1)


    def test_reallySlowDelivery(self):
        """
        If the Deferred takes so long to fire that another retransmission
        attempt takes place, the message should only be delivered once.  If it
        does fail, the next transmission attempt should actually transmit.
        """
        slowRouter = self.stubSlowRouter()
        c = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        self.runQueue(self.aliceQueue)
        slowRouter.flushMessages()
        self.assertEqual(len(slowRouter.messages), 0)
        self.assertEqual(self.receiver.receivedCount, 1)
        self.assertEqual(c.invocations, 1)
        self.assertEqual(c.succeeded, 1)


    def test_multipleMessages(self):
        """
        Sending multiple messages at the same time should result in the
        messages being processed immediately, with no delay, but in order.
        """
        slowRouter = self.stubSlowRouter()
        bucket = []
        c = self.aliceToBobWithConsequence()
        c.bucket = bucket
        c2 = self.aliceToBobWithConsequence()
        c2.bucket = bucket
        # Sanity check; make sure the message hasn't been processed yet.
        self.assertEqual(bucket, [])
        self.runQueue(self.aliceQueue)
        slowRouter.flushMessages()
        self.assertEqual(c.invocations, 1)
        self.assertEqual(c.succeeded, 1)
        self.assertEqual(c2.invocations, 1)
        self.assertEqual(c2.succeeded, 1)
        self.assertEqual(bucket, [c, c2])
        self.assertEqual(self.runQueue(self.aliceQueue), None)


    def test_multipleAnswers(self):
        """
        Sending multiple messages at the same time should result in the
        messages being processed immediately, with no delay, but in order.
        """
        slowRouter = self.stubSlowRouter()
        bucket = []
        c = self.aliceToBobWithConsequence()
        c.bucket = bucket
        c2 = self.aliceToBobWithConsequence()
        c2.bucket = bucket
        # Sanity check; make sure the message hasn't been processed yet.
        self.assertEqual(bucket, [])
        self.runQueue(self.aliceQueue)
        slowRouter.flushMessages(dropAcks=True)
        [time1] = IScheduler(self.bobQueue.store).scheduledTimes(self.bobQueue)
        time2 = self.runQueue(self.bobQueue)
        self.assertEqual(time2 - self.time.peek(), self.retransmitDelta)
        slowRouter.flushMessages()
        self.assertEqual(c.invocations, 1)
        self.assertEqual(c.succeeded, 1)
        self.assertEqual(c2.invocations, 1)
        self.assertEqual(c2.succeeded, 1)
        self.assertEqual(bucket, [c, c2])
        self.assertEqual(self.runQueue(self.aliceQueue), None)


    def test_deliveryIdempotence(self):
        """
        Delivering the same message to a substore twice should only result in
        it being delivered to application code once.
        """
        slowRouter = self.stubSlowRouter()
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        slowRouter.spuriousDeliveries()
        self.assertEqual(self.receiver.receivedCount, 1)
        self.assertEqual(sdc.invocations, 0)
        slowRouter.flushMessages()
        self.assertEqual(self.receiver.receivedCount, 1)
        self.assertEqual(sdc.invocations, 1)
        self.checkOneResponse(sdc, )


    def test_reciprocate(self):
        """
        In addition to responding to the message with a return value, the
        receiver should be able to remember the sender and emit reciprocal
        messages.
        """
        self.receiver.reciprocate = True
        receiver2 = StubReceiver(store=self.aliceStore)
        getEveryoneRole(self.aliceStore).shareItem(receiver2, u'nothing')
        sdc = self.aliceToBobWithConsequence()
        self.runQueue(self.aliceQueue)
        self.runQueue(self.bobQueue)
        self.assertEqual(receiver2.receivedCount, 1)
        self.assertEqual(receiver2.messageType, u'custom.message.type.response')
        self.assertEqual(receiver2.messageData,
                         'Some message contents response')


    def test_unhandledDeliveryError(self):
        """
        When a message cannot be delivered, but no consequence is supplied, the
        error should be logged.
        """
        self.receiver.buggy = True
        self.aliceQueue.queueMessage(
            Identifier(u"nothing", u"alice", u"example.com"),
            Identifier(u"nothing", u"bob", u"example.com"),
            Value(u'custom.message.type',
                     "Some message contents"))
        self.runQueue(self.aliceQueue)
        [err] = self.flushLoggedErrors(MessageTransportError)


    def test_messageRemoteItem(self):
        """
        When a message is sent to a shared item using
        L{AMPMessenger.messageRemote}, and received by an L{AMPReceiver}, its
        data should be delivered to an appropriately decorated method.

        This is an integration test of the functionality covered by this suite
        and the functionality covered by L{AMPMessagingTests}.
        """
        aliceAMP = RealAMPReceiver(store=self.aliceStore)
        getEveryoneRole(self.aliceStore).shareItem(aliceAMP, u'ally')
        bobAMP = RealAMPReceiver(store=self.bobStore)
        getEveryoneRole(self.bobStore).shareItem(bobAMP, u'bobby')
        msgr = AMPMessenger(self.aliceQueue,
                            Identifier(u'ally', u'alice', u'example.com'),
                            Identifier(u'bobby', u'bob', u'example.com'))
        msgr.messageRemote(SimpleCommand, int1=3, str2="hello")
        self.runQueue(self.aliceQueue)
        self.assertEqual(bobAMP.args, [(3, 'hello')])



class SimpleError(Exception):
    """
    A simple error that should be detectable by L{SimpleCommand}.
    """



class SimpleCommand(Command):
    """
    Sample simple command with a few arguments.
    """

    arguments = [("int1", Integer()),
                 ("str2", String())]

    response = [("int3", Integer())]

    errors = {SimpleError: "SIMPLE_ERROR"}



class SenderCommand(Command):
    arguments = [("sender", SenderArgument())]
    response = [("sender", SenderArgument())]



class TargetCommand(Command):
    arguments = [("target", TargetArgument())]
    response = [("target", TargetArgument())]



class TrivialCommand(Command):
    """
    Trivial no-argument AMP command.
    """

    errors = {SimpleError: "SIMPLE_ERROR"}



class RealAMPReceiver(Item, AMPReceiver):
    """
    This is an integration testing item for making sure that decorated methods
    on items receiving messages will work.
    """

    dummy = integer()
    args = inmemory()

    def activate(self):
        """
        Set up test state.
        """
        self.args = []

    @commandMethod.expose(SimpleCommand)
    def doit(self, int1, str2):
        """
        Simple responder for L{SimpleCommand}.
        """
        self.args.append((int1, str2))
        return dict(int3=int1+len(str2))



class MyAMPReceiver(AMPReceiver):
    """
    A simple L{AMPReceiver} subclass with a few exposed methods.
    """

    def __init__(self):
        """
        Create a L{MyAMPReceiver}.
        """
        self.commandArguments = []
        self.commandAnswers = []
        self.commandErrors = []
        self.senders = []
        self.targets = []


    @commandMethod.expose(SimpleCommand)
    def simpleCommand(self, int1, str2):
        """
        Responder for a simple command.
        """
        self.commandArguments.append((int1, str2))
        return dict(int3=4)


    @answerMethod.expose(SimpleCommand)
    def simpleAnswer(self, int3):
        """
        Responder for a simple answer.
        """
        self.commandAnswers.append(int3)


    @errorMethod.expose(SimpleCommand, SimpleError)
    def simpleError(self, failure):
        self.commandErrors.append(failure)


    @commandMethod.expose(SenderCommand)
    def commandWithSender(self, sender):
        self.senders.append(sender)
        return {}


    @commandMethod.expose(TargetCommand)
    def commandWithTarget(self, target):
        self.targets.append(target)
        return {}

    @answerMethod.expose(SenderCommand)
    def answerWithSender(self, sender):
        self.senders.append(sender)

    @answerMethod.expose(TargetCommand)
    def answerWithTarget(self, target):
        self.targets.append(target)


class ExpectedBuggyReceiver(AMPReceiver):
    """
    This AMP responder will raise an expected exception type.
    """

    @commandMethod.expose(TrivialCommand)
    def raiseSimpleError(self):
        raise SimpleError("simple description")



class UnexpectedBuggyReceiver(AMPReceiver):
    """
    This AMP responder will raise an unexpected exception type.
    """

    @commandMethod.expose(TrivialCommand)
    def raiseRuntimeError(self):
        raise RuntimeError()



class AMPMessagingTests(TestCase):
    """
    Test cases for high-level AMP message parsing and emitting API.
    """

    def setUp(self):
        """
        Initialize the list of messages which this can deliver as a
        pseudo-queue.
        """
        self.messages = []


    def queueMessage(self, sender, target, value,
                     consequence=None):
        """
        Emulate L{MessageQueue.queueMessage}.
        """
        self.messages.append((sender, target,
                              value.type, value.data, consequence))


    def test_messageRemote(self):
        """
        L{AMPMessenger.messageRemote} should queue a message with the provided
        queue, sender, and target, serializing its arguments according to the
        provided AMP command.
        """
        sender = Identifier(u'test-sender', u'bob', u'example.com')
        target = Identifier(u'test-target', u'alice', u'example.com')

        msgr = AMPMessenger(self, sender, target)
        msgr.messageRemote(SimpleCommand, int1=3, str2="hello")
        expectedConsequence = None
        self.assertEqual(self.messages,
                         [(sender, target, AMP_MESSAGE_TYPE,
                           Box(_command="SimpleCommand",
                               int1="3", str2="hello").serialize(),
                           expectedConsequence)])


    def test_messageReceived(self):
        """
        L{AMPReceiver.messageReceived} should dispatch commands to methods that
        were appropriately decorated.
        """
        amr = MyAMPReceiver()
        questionBox = Box(_command=SimpleCommand.commandName,
                          int1="7", str2="test")
        data = questionBox.serialize()
        response = amr.messageReceived(
            Value(AMP_MESSAGE_TYPE, data), None, None)
        self.assertEqual(response.type, AMP_ANSWER_TYPE)
        self.assertEqual(amr.commandArguments, [(7, "test")])
        self.assertEqual(response.data, Box(int3="4").serialize())


    def test_messageReceivedHandledError(self):
        """
        L{AMPReceiver.messageReceived} should emit a responseType and
        responseData of the appropriate type if the command in question has a
        translation of the raised error.
        """
        bug = ExpectedBuggyReceiver()
        questionBox = Box(_command=TrivialCommand.commandName)
        data = questionBox.serialize()
        rar = self.assertRaises(RevertAndRespond, bug.messageReceived,
                                Value(AMP_MESSAGE_TYPE, data),
                                None, None)
        self.assertEqual(rar.value.type, AMP_ANSWER_TYPE)
        self.assertEqual(rar.value.data,
                         Box(_error_code="SIMPLE_ERROR",
                             _error_description="simple description")
                         .serialize())


    def test_messageReceivedUnhandledError(self):
        """
        L{AMPReceiver.messageReceived} should allow error not defined by its
        command to be raised so that the normal L{ERROR_REMOTE_EXCEPTION}
        behavior takes over.
        """
        bug = UnexpectedBuggyReceiver()
        questionBox = Box(_command=TrivialCommand.commandName)
        data = questionBox.serialize()
        self.assertRaises(RuntimeError, bug.messageReceived,
                          Value(AMP_MESSAGE_TYPE, data),
                          None, None)


    def test_answerReceived(self):
        """
        L{AMPReceiver.answerReceived} should dispatch answers to methods that
        were appropriately decorated.
        """
        originalMessageData = Box(_command=SimpleCommand.commandName).serialize()
        amr = MyAMPReceiver()
        answerBox = Box(int3="4")
        data = answerBox.serialize()
        amr.answerReceived(Value(AMP_ANSWER_TYPE, data),
                           Value(None, originalMessageData),
                           None, None)
        self.assertEqual(amr.commandAnswers, [4])


    def test_errorReceived(self):
        """
        L{AMPReceiver.answerReceived} should dispatch answers that indicate an
        AMP error to methods decorated by the L{errorMethod} decorator, not to
        the L{answerMethod} decorator.
        """
        originalMessageData = Box(_command=SimpleCommand.commandName).serialize()
        amr = MyAMPReceiver()
        data = Box(_error="SIMPLE_ERROR").serialize()
        amr.answerReceived(Value(AMP_ANSWER_TYPE, data),
                           Value(None, originalMessageData),
                           None, None)
        self.assertEqual(amr.commandAnswers, [])
        amr.commandErrors.pop().trap(SimpleError)
        self.assertEqual(amr.commandErrors, [])


    def test_messageReceivedWrongType(self):
        """
        An L{UnknownMessageType} should be raised when a message of the wrong
        type is dispatched to an L{AMPReceiver}.
        """
        amr = MyAMPReceiver()
        questionBox = Box(_command=SimpleCommand.commandName,
                          int1="7", str2="test")
        data = questionBox.serialize()
        for badType in u'some.random.type', AMP_ANSWER_TYPE:
            self.assertRaises(UnknownMessageType, amr.messageReceived,
                              Value(badType, data), None, None)
        self.assertEqual(amr.commandArguments, [])


    def test_messageReceivedBadData(self):
        """
        A L{MalformedMessage} should be raised when a message that cannot be
        interpreted as a single AMP box is received.
        """

        amr = MyAMPReceiver()
        for badData in ["", Box().serialize() + Box().serialize()]:
            self.assertRaises(MalformedMessage, amr.messageReceived,
                              Value(AMP_MESSAGE_TYPE, badData), None, None)


    def test_answerReceivedBadData(self):
        """
        A L{MalformedMessage} should be raised when a message that cannot be
        interpreted as a single AMP box is received.
        """
        originalMessageData = Box(_command=SimpleCommand.commandName).serialize()
        amr = MyAMPReceiver()
        for badData in ["", Box().serialize() + Box().serialize()]:
            self.assertRaises(MalformedMessage, amr.answerReceived,
                              Value(AMP_ANSWER_TYPE, badData),
                              Value(None, originalMessageData),
                              None, None)


    def test_answerReceivedWrongType(self):
        """
        An L{UnknownMessageType} exception should be raised when a answer of
        the wrong type is dispatched to an L{AMPReceiver}.
        """
        originalMessageData = Box(_command=SimpleCommand.commandName).serialize()
        amr = MyAMPReceiver()
        answerBox = Box(int3="4")
        data = answerBox.serialize()
        for badType in u'some.random.type', AMP_MESSAGE_TYPE:
            self.assertRaises(UnknownMessageType, amr.answerReceived,
                              Value(badType, data),
                              Value(None, originalMessageData),
                              None, None)
        self.assertEqual(amr.commandAnswers, [])


    def test_messageReceivedSenderArgument(self):
        """
        The special argument L{TargetArgument} should cause the L{sender}
        argument to L{messageReceived} to be passed as an argument to the
        responder method.
        """
        amr = MyAMPReceiver()
        shareident = Identifier(u'abc', u'def', u'ghi')
        amr.messageReceived(
            Value(AMP_MESSAGE_TYPE,
                     Box(_command=SenderCommand.commandName).serialize()),
            shareident, None)
        self.assertEqual([shareident], amr.senders)


    def test_messageReceivedTargetArgument(self):
        """
        The special argument L{TargetArgument} should cause the L{sender}
        argument to L{messageReceived} to be passed as an argument to the
        responder method.
        """
        amr = MyAMPReceiver()
        shareident = Identifier(u'abc', u'def', u'ghi')
        amr.messageReceived(Value(AMP_MESSAGE_TYPE,
                                     Box(_command=TargetCommand.commandName).serialize()),
                            None, shareident)
        self.assertEqual([shareident], amr.targets)


    def test_answerReceivedSenderArgument(self):
        """
        The special argument L{SenderArgument} should cause the
        L{originalSender} argument to L{answerReceived} to be passed as an
        argument to the responder method.
        """
        amr = MyAMPReceiver()
        shareident = Identifier(u'abc', u'def', u'ghi')
        amr.answerReceived(
            Value(AMP_ANSWER_TYPE, Box().serialize()),
            Value(None,
                     Box(_command=SenderCommand.commandName).serialize()),
            shareident, None)
        self.assertEqual([shareident], amr.senders)


    def test_answerReceivedTargetArgument(self):
        """
        The special argument L{TargetArgument} should cause the
        L{originalTarget} argument to L{answerReceived} to be passed as an
        argument to the responder method.
        """
        amr = MyAMPReceiver()
        shareident = Identifier(u'abc', u'def', u'ghi')
        amr.answerReceived(
            Value(AMP_ANSWER_TYPE, Box().serialize()),
            Value(None,
                     Box(_command=TargetCommand.commandName).serialize()),
            None,
            shareident)
        self.assertEqual([shareident], amr.targets)



class ExpositionTests(TestCase):
    """
    Tests for exposing methods with the L{_AMPExposer.expose} decorator, and
    retrieving them with the L{_AMPExposer.responderForName} lookup method.
    """

    def setUp(self):
        """
        Set up a local L{_AMPExposer} instance for testing.
        """
        self.ampExposer = _AMPExposer("amp exposer for testing")
        self.errorExposer = _AMPErrorExposer("lulz")


    def test_exposeCommand(self):
        """
        Exposing a method as a command object ought to make it accessible to
        L{responderForName}, and add a matching C{command} attribute to that
        result.
        """
        class TestClass(object):
            def __init__(self, x):
                self.num = x

            @self.ampExposer.expose(TrivialCommand)
            def thunk(self):
                return 'hi', self.num + 1

        tc = TestClass(3)
        callable = self.ampExposer.responderForName(tc, TrivialCommand.commandName)
        self.assertEqual(callable(), ("hi", 4))
        self.assertIdentical(callable.command, TrivialCommand)


    def test_exposeError(self):
        """
        A method exposed as an error handler for a particular type of error
        should be able to be looked up by the combination of the command and
        the error.
        """
        class TestClass(object):
            @self.errorExposer.expose(SimpleCommand, SimpleError)
            def thunk(self):
                raise SimpleError()
        tc = TestClass()
        thunk = self.errorExposer.errbackForName(tc, SimpleCommand.commandName, "SIMPLE_ERROR")
        self.assertEqual(thunk.exception, SimpleError)
        self.assertEqual(thunk.command, SimpleCommand)
        self.assertRaises(SimpleError, thunk)


    def test_exposeOnTwoTypes(self):
        """
        An integration test with L{epsilon.expose}; sanity checking to make
        sure that exposing different methods on different classes for the same
        command name yields the same results.
        """
        class TestClass(object):
            @self.ampExposer.expose(TrivialCommand)
            def thunk(self):
                return 1
        class TestClass2:
            @self.ampExposer.expose(TrivialCommand)
            def funk(self):
                return 2

        tc2 = TestClass2()
        callable = self.ampExposer.responderForName(tc2, TrivialCommand.commandName)
        self.assertEqual(callable(), 2)
        tc = TestClass()
        callable = self.ampExposer.responderForName(tc, TrivialCommand.commandName)
        self.assertEqual(callable(), 1)
