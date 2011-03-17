# -*- test-case-name: xmantissa.test.test_interstore -*-

"""
This module provides an implementation-agnostic mechanism for routing messages
between users.  Mantissa requires such a mechanism for any truly multi-user
application, because Axiom partitions each user's account into its own store.
For more detail on specifics of that separation, see the module documentation
for L{axiom.userbase}.

Let's say we wanted to write an application which allowed Alice
<alice@somewhere.example.com> to make an appointment with Bob
<bob@elsewhere.example.com>.  We'll call it 'Example App'.

    - Write the code for your Calendar item.  It should implement
      L{IMessageReceiver} such that it can receive appointment requests.

    - Create these hypothetical calendar items in both Bob and Alice's stores.
      These should also be shared - specifically its IMessageReceiver interface
      must be shared, at least from Alice to Bob and from Bob to Alice.  Give
      it a shareID qualified with the name of the application - for example,
      "exampleapp.root.calendar" - to avoid conflicts with other applications.

    - Install a L{MessageQueue} powerup for both alice and bob.

    - Now, Alice wants to request a meeting with bob.  She should send a
      message to a target like C{Identifier(u'exampleapp.root.calendar',
      u'bob', u'elsewhere.example.com')}, and of course the sender should be
      C{Identifier(u'exampleapp.root.calendar', u'alice',
      u'somewhere.example.com')}, using her L{MessageQueue} powerup's
      L{queueMessage} method.  Most applications will want to call this
      indirectly, via the high-level interface in
      L{AMPMessenger.messageRemote}.

    - Bob's Calendar item will receive this message.  It parses the contents of
      the message into a structured meeting request and performs the
      appropriate transaction.  You can use AMP formatting and argument parsing
      to format and parse message bodies by using the L{AMPMessenger} and
      L{AMPReceiver} classes provided here, respectively.

    - If Bob's calendar needs to respond to Alice's calendar to confirm, it can
      use the queueMessage function to reply.

This model of inter-user communciation is a bit more work than simply
manipulating a shared database, but the loose coupling it enforces provides a
long list of advantages.  System upgrades, for example, can be performed
incrementally, one account at a time, and newer versions can talk to older
versions using a compatible protocol.  The message routing mechanism is
pluggable, and it is possible to implement versions which talk to multiple
Mantissa processes to take advantage of multiple CPU cores, multiple mounted
disks, different Mantissa deployments across the internet, or multiple Mantissa
nodes of the same application within a cluster.  Although these things don't
come "out of the box", the programming model here allows all of these changes
to be made without changing any of your application code, just the high-level
routing glue.
"""

from datetime import timedelta

from zope.interface import implements

from twisted.python import log
from twisted.python.failure import Failure
from twisted.internet import defer
from twisted.protocols.amp import COMMAND, ERROR, Argument, Box, parseString

from epsilon.structlike import record

from epsilon.expose import Exposer

from axiom.iaxiom import IScheduler
from axiom.item import Item, declareLegacyItem
from axiom.errors import UnsatisfiedRequirement
from axiom.attributes import text, bytes, integer, AND, reference, inmemory
from axiom.dependency import dependsOn, requiresFromSite
from axiom.userbase import LoginSystem, LoginMethod
from axiom.upgrade import registerUpgrader

from xmantissa.ixmantissa import (
    IMessageRouter, IDeliveryConsequence, IMessageReceiver)

from xmantissa.error import (
    MessageTransportError, BadSender, UnknownMessageType, RevertAndRespond,
    MalformedMessage)

from xmantissa.sharing import getPrimaryRole, NoSuchShare, Identifier
from xmantissa._recordattr import RecordAttribute, WithRecordAttributes

DELIVERY_ERROR = u'mantissa.delivery.error'

ERROR_NO_SHARE = 'no-share'
ERROR_NO_USER = 'no-user'
ERROR_REMOTE_EXCEPTION = 'remote-exception'
ERROR_BAD_SENDER = 'bad-sender'

_RETRANSMIT_DELAY = 120



class Value(record('type data')):
    """
    A L{Value} is a combination of a data type and some data of that type.
    It is the content of a message.

    @ivar type: A short string describing the type of the data.  Possible
    values include L{DELIVERY_ERROR}, L{AMP_MESSAGE_TYPE}, or
    L{AMP_ANSWER_TYPE}.
    @type type: L{unicode}

    @ivar data: The payload of the value, parsed according to rules identified
    by C{self.type}.
    @type data: L{str}
    """



class _QueuedMessage(Item, WithRecordAttributes):
    """
    This is a message, queued in the sender's store, awaiting delivery to the
    target.
    """

    senderUsername = text(
        """
        This is the username of the user who is sending the message.
        """,
        allowNone=False)

    senderDomain = text(
        """
        This is the domain name of the user who is sending the message.
        """,
        allowNone=False)

    senderShareID = text(
        """
        This is the shareID of the shared item which is sending the message.
        """)

    sender = RecordAttribute(Identifier,
                             [senderShareID, senderUsername, senderDomain])

    targetUsername = text(
        """
        This is the username of the user which is intended to receive the
        message.
        """,
        allowNone=False)

    targetDomain = text(
        """
        This is the domain name fo the user which is intended to receive the
        message.
        """,
        allowNone=False)

    targetShareID = text(
        """
        This is the target shareID object that the message will be delivered to
        in the foreign store.
        """,
        allowNone=False)

    target = RecordAttribute(Identifier,
                             [targetShareID, targetUsername, targetDomain])

    messageType = text(
        """
        The content-type of the data stored in my L{messageData} attribute.
        """,
        allowNone=False)

    messageData = bytes(
        """
        The data of the message.
        """, allowNone=False)

    value = RecordAttribute(Value,
                               [messageType, messageData])

    messageID = integer(
        """
        An identifier for this message, unique to this store.
        """, allowNone=False)

    consequence = reference(
        """
        A provider of L{IDeliveryConsequence} which will be invoked when the
        answer to this message is received.
        """, allowNone=True)



class _FailedAnswer(Item, WithRecordAttributes):
    """
    A record of an L{answerReceived} method raising an exception.

    There is no way for the system to report the failed processing of an answer
    to its peer (nor should there be), so this class allows a buggy answer
    receiver to remember the answer for later.
    """

    consequence = reference(
        """
        A provider of L{IDeliveryConsequence} which will be invoked when this
        _FailedAnswer is redelivered.
        """,
        allowNone=False)

    messageType = text(
        """
        The content-type of the data stored in my L{messageData} attribute.
        """,
        allowNone=False)

    messageData = bytes(
        """
        The data of the message.
        """, allowNone=False)

    messageValue = RecordAttribute(Value,
                                   [messageType, messageData])
    answerType = text(
        """
        The content-type of the data stored in my L{answerData} attribute.
        """,
        allowNone=False)

    answerData = bytes(
        """
        The data of the answer.
        """, allowNone=False)

    answerValue = RecordAttribute(Value,
                                  [answerType, answerData])

    senderUsername = text(
        """
        This is the username of the user who is sending the message.
        """,
        allowNone=False)

    senderDomain = text(
        """
        This is the domain name of the user who is sending the message.
        """,
        allowNone=False)

    senderShareID = text(
        """
        This is the shareID of the shared item which is sending the message.
        """)

    sender = RecordAttribute(Identifier,
                             [senderShareID, senderUsername, senderDomain])

    targetUsername = text(
        """
        This is the username of the user which is intended to receive the
        message.
        """,
        allowNone=False)

    targetDomain = text(
        """
        This is the domain name fo the user which is intended to receive the
        message.
        """,
        allowNone=False)

    targetShareID = text(
        """
        This is the target shareID object that the message will be delivered to
        in the foreign store.
        """,
        allowNone=False)

    target = RecordAttribute(Identifier,
                             [targetShareID, targetUsername, targetDomain])


    def redeliver(self):
        """
        Re-deliver the answer to the consequence which previously handled it
        by raising an exception.

        This method is intended to be invoked after the code in question has
        been upgraded.  Since there are no buggy answer receivers in
        production, nothing calls it yet.
        """
        self.consequence.answerReceived(self.answerValue,
                                        self.messageValue,
                                        self.sender,
                                        self.target)
        self.deleteFromStore()



class _AlreadyAnswered(Item, WithRecordAttributes):
    """
    An L{AlreadyAnswered} is a persistent record of an answer to a message
    delivered via L{queueMessage}.  This stays in the database until the
    original sender has sent a definitive acknowledgement to this answer, so
    that duplicate L{routeMessage} invocations do not cause duplicate
    application-level processing of the message.

    @ivar deliveryDeferred: a L{Deferred} in memory, representing a currently
    pending delivery attempt.  This is L{None} if no delivery attempt is
    currently pending.
    """

    deliveryDeferred = inmemory()


    def activate(self):
        """
        Initialize in-memory state.
        """
        self.deliveryDeferred = None


    originalSenderShareID = text(
        """
        This is the shareID of the item which originally sent the message that
        this answer is in response to; the one that the answer is being
        delivered to.
        """,
        allowNone=True)

    originalSenderUsername = text(
        """
        This is the localpart of the user's account which originally sent the
        message that this answer is in response to; the one that the answer is
        being delivered to.
        """,
        allowNone=False)

    originalSenderDomain = text(
        """
        This is the domain name of the user's account which originally sent the
        message that this answer is in response to; the one that the answer is
        being delivered to.
        """,
        allowNone=False)


    originalSender = RecordAttribute(Identifier,
                                     [originalSenderShareID,
                                      originalSenderUsername,
                                      originalSenderDomain])

    originalTargetShareID = text(
        """
        This is the shareID of the original item which received the message
        that this answer in response to.  This is the item that the response is
        being sent from.
        """,
        allowNone=False)

    originalTargetUsername = text(
        """
        This is the localpart of the original account which received the
        message that this answer in response to.  This is the user that the
        response is being sent from.
        """,
        allowNone=False)

    originalTargetDomain = text(
        """
        This is the domain name of the original account which received the
        message that this answer in response to.  This is the user that the
        response is being sent from.
        """,
        allowNone=False)

    originalTarget = RecordAttribute(Identifier,
                                     [originalTargetShareID,
                                      originalTargetUsername,
                                      originalTargetDomain])

    messageID = integer(
        """
        An identifier, unique to the original sender account name
        (username@domain) for this message.
        """, allowNone=False)

    answerType = text(
        """
        Some text, identifying the type of the answer.  This refers to the data
        in L{answerData} - this attribute will be set to L{DELIVERY_ERROR} if
        the answer could not be delivered.
        """,
        allowNone=False)

    answerData = bytes(
        """
        The data returned from the original receiver of this answer.
        """,
        allowNone=False)

    value = RecordAttribute(Value,
                               [answerType, answerData])



class _NullRouter(object):
    """
    A null L{IMessageRouter} implementation, which drops messages on the floor.
    This is only used in the case where an L{IMessageRouter} powerup cannot be
    found on the site store to route messages to their recipients.
    """

    implements(IMessageRouter)

    def routeAnswer(self, *a):
        """
        Route an answer, but drop it on the floor.
        """
        return defer.fail(MessageTransportError())


    def routeMessage(self, *a):
        """
        Route a message by dropping it on the floor.
        """


class LocalMessageRouter(record("loginSystem")):
    """
    This is an item installed on the site store to route messages to
    appropriate users.  This only routes messages between different stores that
    are referred to as accounts by a L{LoginSystem} on a single node.  In other
    words it implements only local delivery.
    """

    implements(IMessageRouter)


    def _routerForAccount(self, identifier):
        """
        Locate an avatar by the username and domain portions of an
        L{Identifier}, so that we can deliver a message to the appropriate
        user.
        """
        acct = self.loginSystem.accountByAddress(identifier.localpart,
                                                 identifier.domain)
        return IMessageRouter(acct, None)


    def routeMessage(self, sender, target, value, messageID):
        """
        Implement L{IMessageRouter.routeMessage} by synchronously locating an
        account via L{axiom.userbase.LoginSystem.accountByAddress}, and
        delivering a message to it by calling a method on it.
        """
        router = self._routerForAccount(target)
        if router is not None:
            router.routeMessage(sender, target, value, messageID)
        else:
            reverseRouter = self._routerForAccount(sender)
            reverseRouter.routeAnswer(sender, target,
                                      Value(DELIVERY_ERROR, ERROR_NO_USER),
                                      messageID)


    def routeAnswer(self, originalSender, originalTarget, value, messageID):
        """
        Implement L{IMessageRouter.routeMessage} by synchronously locating an
        account via L{axiom.userbase.LoginSystem.accountByAddress}, and
        delivering a response to it by calling a method on it and returning a
        deferred containing its answer.
        """
        router = self._routerForAccount(originalSender)
        return router.routeAnswer(originalSender, originalTarget,
                                  value, messageID)



def _accidentalSiteRouter(siteStore):
    """
    Create an L{IMessageRouter} provider for an item in a user store
    accidentally opened as a site store.
    """
    try:
        raise UnsatisfiedRequirement()
    except UnsatisfiedRequirement:
        log.err(Failure(),
                "You have opened a user's store as if it were a site store.  "
                "Message routing is disabled.")
    return _NullRouter()



def _createLocalRouter(siteStore):
    """
    Create an L{IMessageRouter} provider for the default case, where no
    L{IMessageRouter} powerup is installed on the top-level store.

    It wraps a L{LocalMessageRouter} around the L{LoginSystem} installed on the
    given site store.

    If no L{LoginSystem} is present, this returns a null router which will
    simply log an error but not deliver the message anywhere, until this
    configuration error can be corrected.

    @rtype: L{IMessageRouter}
    """
    ls = siteStore.findUnique(LoginSystem, default=None)
    if ls is None:
        try:
            raise UnsatisfiedRequirement()
        except UnsatisfiedRequirement:
            log.err(Failure(),
                    "You have opened a substore from a site store with no "
                    "LoginSystem.  Message routing is disabled.")
        return _NullRouter()
    return LocalMessageRouter(ls)



class MessageQueue(Item):
    """
    A queue of outgoing L{QueuedMessage} objects.
    """
    schemaVersion = 2
    powerupInterfaces = (IMessageRouter,)

    siteRouter = requiresFromSite(IMessageRouter,
                                  _createLocalRouter,
                                  _accidentalSiteRouter)

    messageCounter = integer(
        """
        This counter generates identifiers for outgoing messages.
        """,
        default=0, allowNone=False)


    def _scheduleMePlease(self):
        """
        This queue needs to have its run() method invoked at some point in the
        future.  Tell the dependent scheduler to schedule it if it isn't
        already pending execution.
        """
        sched = IScheduler(self.store)
        if len(list(sched.scheduledTimes(self))) == 0:
            sched.schedule(self, sched.now())


    def routeMessage(self, sender, target, value, messageID):
        """
        Implement L{IMessageRouter.routeMessage} by locating a shared item
        which provides L{IMessageReceiver}, identified by L{target} in this
        L{MessageQueue}'s L{Store}, as shared to the specified C{sender}, then
        invoke its L{messageReceived} method.  Then, take the results of that
        L{messageReceived} invocation and deliver them as an answer to the
        object specified by L{sender}.

        If any of these steps fail such that no
        L{IMessageReceiver.messageReceived} method may be invoked, generate a
        L{DELIVERY_ERROR} response instead.
        """
        avatarName = sender.localpart + u"@" + sender.domain
        # Look for the sender.
        answer = self.store.findUnique(
            _AlreadyAnswered,
            AND(_AlreadyAnswered.originalSender == sender,
                _AlreadyAnswered.messageID == messageID),
            default=None)
        if answer is None:
            role = getPrimaryRole(self.store, avatarName)
            try:
                receiver = role.getShare(target.shareID)
            except NoSuchShare:
                response = Value(DELIVERY_ERROR,  ERROR_NO_SHARE)
            else:
                try:
                    def txn():
                        output = receiver.messageReceived(value, sender,
                                                          target)
                        if not isinstance(output, Value):
                            raise TypeError("%r returned non-Value %r" %
                                            (receiver, output))
                        return output
                    response = self.store.transact(txn)
                except RevertAndRespond, rar:
                    response = rar.value
                except:
                    log.err(Failure(),
                            "An error occurred during inter-store "
                            "message delivery.")
                    response = Value(DELIVERY_ERROR, ERROR_REMOTE_EXCEPTION)
            answer = _AlreadyAnswered.create(store=self.store,
                                             originalSender=sender,
                                             originalTarget=target,
                                             messageID=messageID,
                                             value=response)
        self._deliverAnswer(answer)
        self._scheduleMePlease()


    def _deliverAnswer(self, answer):
        """
        Attempt to deliver an answer to a message sent to this store, via my
        store's parent's L{IMessageRouter} powerup.

        @param answer: an L{AlreadyAnswered} that contains an answer to a
        message sent to this store.
        """
        router = self.siteRouter
        if answer.deliveryDeferred is None:
            d = answer.deliveryDeferred = router.routeAnswer(
                answer.originalSender, answer.originalTarget, answer.value,
                answer.messageID)
            def destroyAnswer(result):
                answer.deleteFromStore()
            def transportErrorCheck(f):
                answer.deliveryDeferred = None
                f.trap(MessageTransportError)
            d.addCallbacks(destroyAnswer, transportErrorCheck)
            d.addErrback(log.err)


    def routeAnswer(self, originalSender, originalTarget, value, messageID):
        """
        Route an incoming answer to a message originally sent by this queue.
        """
        def txn():
            qm = self._messageFromSender(originalSender, messageID)
            if qm is None:
                return
            c = qm.consequence
            if c is not None:
                c.answerReceived(value, qm.value,
                                 qm.sender, qm.target)
            elif value.type == DELIVERY_ERROR:
                try:
                    raise MessageTransportError(value.data)
                except MessageTransportError:
                    log.err(Failure(),
                            "An unhandled delivery error occurred on a message"
                            " with no consequence.")
            qm.deleteFromStore()
        try:
            self.store.transact(txn)
        except:
            log.err(Failure(),
                    "An unhandled error occurred while handling a response to "
                    "an inter-store message.")
            def answerProcessingFailure():
                qm = self._messageFromSender(originalSender, messageID)
                _FailedAnswer.create(store=qm.store,
                                     consequence=qm.consequence,
                                     sender=originalSender,
                                     target=originalTarget,
                                     messageValue=qm.value,
                                     answerValue=value)
                qm.deleteFromStore()
            self.store.transact(answerProcessingFailure)
        return defer.succeed(None)


    def _messageFromSender(self, sender, messageID):
        """
        Locate a previously queued message by a given sender and messageID.
        """
        return self.store.findUnique(
            _QueuedMessage,
            AND(_QueuedMessage.senderUsername == sender.localpart,
                _QueuedMessage.senderDomain == sender.domain,
                _QueuedMessage.messageID == messageID),
            default=None)


    def _verifySender(self, sender):
        """
        Verify that this sender is valid.
        """
        if self.store.findFirst(
            LoginMethod,
            AND(LoginMethod.localpart == sender.localpart,
                LoginMethod.domain == sender.domain,
                LoginMethod.internal == True)) is None:
            raise BadSender(sender.localpart + u'@' + sender.domain,
                            [lm.localpart + u'@' + lm.domain
                             for lm in self.store.query(
                        LoginMethod, LoginMethod.internal == True)])


    def queueMessage(self, sender, target, value,
                     consequence=None):
        """
        Queue a persistent outgoing message.

        @param sender: The a description of the shared item that is the sender
        of the message.
        @type sender: L{xmantissa.sharing.Identifier}

        @param target: The a description of the shared item that is the target
        of the message.
        @type target: L{xmantissa.sharing.Identifier}

        @param consequence: an item stored in the same database as this
        L{MessageQueue} implementing L{IDeliveryConsequence}.
        """
        self.messageCounter += 1
        _QueuedMessage.create(store=self.store,
                              sender=sender,
                              target=target,
                              value=value,
                              messageID=self.messageCounter,
                              consequence=consequence)
        self._scheduleMePlease()


    def run(self):
        """
        Attmept to deliver the first outgoing L{QueuedMessage}; return a time
        to reschedule if there are still more retries or outgoing messages to
        send.
        """
        delay = None
        router = self.siteRouter
        for qmsg in self.store.query(_QueuedMessage,
                                     sort=_QueuedMessage.storeID.ascending):
            try:
                self._verifySender(qmsg.sender)
            except:
                self.routeAnswer(qmsg.sender, qmsg.target,
                                 Value(DELIVERY_ERROR, ERROR_BAD_SENDER),
                                 qmsg.messageID)
                log.err(Failure(),
                        "Could not verify sender for sending message.")
            else:
                router.routeMessage(qmsg.sender, qmsg.target,
                                    qmsg.value, qmsg.messageID)

        for answer in self.store.query(_AlreadyAnswered,
                                       sort=_AlreadyAnswered.storeID.ascending):
            self._deliverAnswer(answer)
        nextmsg = self.store.findFirst(_QueuedMessage, default=None)
        if nextmsg is not None:
            delay = _RETRANSMIT_DELAY
        else:
            nextanswer = self.store.findFirst(_AlreadyAnswered, default=None)
            if nextanswer is not None:
                delay = _RETRANSMIT_DELAY
        if delay is not None:
            return IScheduler(self.store).now() + timedelta(seconds=delay)


declareLegacyItem(
    MessageQueue.typeName, 1,
    dict(messageCounter=integer(default=0, allowNone=False),
         scheduler=reference()))

def upgradeMessageQueue1to2(old):
    """
    Copy the C{messageCounter} attribute to the upgraded MessageQueue.
    """
    return old.upgradeVersion(
        MessageQueue.typeName, 1, 2, messageCounter=old.messageCounter)

registerUpgrader(upgradeMessageQueue1to2, MessageQueue.typeName, 1, 2)


#### High-level convenience API ####

AMP_MESSAGE_TYPE = u'mantissa.amp.message'
AMP_ANSWER_TYPE = u'mantissa.amp.answer'


class _ProtoAttributeArgument(Argument):
    """
    Common factoring of L{TargetArgument} and L{SenderArgument}, for reading an
    attribute from the 'proto' attribute.

    @ivar attr: the name of the attribute to retrieve from the C{proto}
    argument to L{_ProtoAttributeArgument.fromBox}.
    """

    def fromBox(self, name, strings, objects, proto):
        """
        Retreive an attribute from the C{proto} parameter.
        """
        objects[name] = getattr(proto, self.attr)


    def toBox(self, name, strings, objects, proto):
        """
        Do nothing; these argument types are for specifying out-of-band
        information not in the message body, so leave the message body alone
        when sending.
        """


class TargetArgument(_ProtoAttributeArgument):
    """
    An AMP L{Argument} which places an L{Identifier} for the target (for
    commands) or original target (for answers) of the message being processed
    into the argument list.
    """
    attr = "target"



class SenderArgument(_ProtoAttributeArgument):
    """
    An AMP L{Argument} which places an L{Identifier} for the sender (for
    commands) or original sender (for answers) of the message being processed
    into the argument list.
    """
    attr = "sender"



class _ProtocolPlaceholder(record("sender target")):
    """
    This placeholder object is passed as the 'proto' object to AMP parsing
    methods, and has the two out-of-band attributes required to support
    L{SenderArgument} and L{TargetArgument}, which are about all you can use it
    for.
    """



class AMPMessenger(record("queue sender target")):
    """
    An L{AMPMessenger} is a conduit between an object sending a message
    (identified by the C{queue} and C{sender} arguments) and a recipient of
    that message (represented by the C{target}) argument.

    @ivar queue: a L{MessageQueue} that will be used to queue messages.

    @ivar sender: an L{Identifier} that will be used as the sender of the
    messages.

    @ivar target: an L{Identifier} that will be used as the target of messages.
    """

    def messageRemote(self, cmdObj, consequence=None, **args):
        """
        Send a message to the peer identified by the target, via the
        given L{Command} object and arguments.

        @param cmdObj: a L{twisted.protocols.amp.Command}, whose serialized
        form will be the message.

        @param consequence: an L{IDeliveryConsequence} provider which will
        handle the result of this message (or None, if no response processing
        is desired).

        @param args: keyword arguments which match the C{cmdObj}'s arguments
        list.

        @return: L{None}
        """
        messageBox = cmdObj.makeArguments(args, self)
        messageBox[COMMAND] = cmdObj.commandName
        messageData = messageBox.serialize()
        self.queue.queueMessage(self.sender, self.target,
                                Value(AMP_MESSAGE_TYPE, messageData),
                                consequence)



class _AMPExposer(Exposer):
    """
    An L{Exposer} whose purpose is to expose objects via L{Command} objects.
    """

    def expose(self, commandObject):
        """
        Declare a method as being related to the given command object.

        @param commandObject: a L{Command} subclass.
        """
        thunk = super(_AMPExposer, self).expose(commandObject.commandName)
        def thunkplus(function):
            result = thunk(function)
            result.command = commandObject
            return result
        return thunkplus


    def responderForName(self, instance, commandName):
        """
        When resolving a command to a method from the wire, the information
        available is the command's name; look up a command.

        @param instance: an instance of a class who has methods exposed via
        this exposer's L{_AMPExposer.expose} method.

        @param commandName: the C{commandName} attribute of a L{Command}
        exposed on the given instance.

        @return: a bound method with a C{command} attribute.
        """
        method = super(_AMPExposer, self).get(instance, commandName)
        return method



class _AMPErrorExposer(Exposer):
    """
    An L{Exposer} whose purpose is to expose objects via L{Command} objects and
    error identifiers.
    """

    def expose(self, commandObject, exceptionType):
        """
        Expose a function for processing a given AMP error.
        """
        thunk = super(_AMPErrorExposer, self).expose(
            (commandObject.commandName,
             commandObject.errors.get(exceptionType)))
        def thunkplus(function):
            result = thunk(function)
            result.command = commandObject
            result.exception = exceptionType
            return result
        return thunkplus


    def errbackForName(self, instance, commandName, errorName):
        """
        Retrieve an errback - a callable object that accepts a L{Failure} as an
        argument - that is exposed on the given instance, given an AMP
        commandName and a name in that command's error mapping.
        """
        return super(_AMPErrorExposer, self).get(instance, (commandName, errorName))



commandMethod = _AMPExposer("""
Use this exposer to expose methods on L{AMPReceiver} subclasses which can
respond to AMP commands.  Use like so::

    @commandMethod.expose(YourCommand)
    def yourMethod(self, yourCommandArgument, ...):
        ...
""")

answerMethod = _AMPExposer("""
Use this exposer to expose methods on L{AMPReceiver} subclasses which can
deal with AMP command responses.  Use like so::

    @answerMethod.expose(YourCommand)
    def yourMethod(self, yourCommandResponseArgument, ...):
        ...
""")

errorMethod = _AMPErrorExposer("""
Use this exposer to expose methods on L{AMPReceiver} subclasses which can
deal with AMP command error responses.  Use like so::

    @errorMethod.expose(YourCommand, YourCommandException)
    def yourMethod(self, failure):
        ...
""")



class AMPReceiver(object):
    """
    This is a mixin for L{Item} objects which wish to implement
    L{IMessageReceiver} and/or L{IDeliveryConsequence} by parsing the bodies of
    arriving messages and answers as AMP boxes.

    To implement L{IMessageReceiver}, use the L{commandMethod} decorator.

    To implement L{IMessageRouter}, use the L{answerMethod} and L{errorMethod}
    decorators.

    For example::

        class MyCommand(Command):
            arguments = [('hello', Integer())]
            response = [('goodbye', Text())]
        class MyResponder(Item, AMPReceiver):
            ...
            @commandMethod.expose(MyCommand)
            def processCommand(self, hello):
                return dict(goodbye=u'goodbye!')
            @answerMethod.expose(MyCommand)
            def processAnswer(self, goodbye):
                # process 'goodbye' here.

    In this example, a L{MyResponder} object might be shared and used as a
    target for a call to L{AMPMessenger.messageRemote} with L{MyCommand}, or
    used as the L{consequence} argument to that same call.
    """
    implements(IMessageReceiver, IDeliveryConsequence)

    def _boxFromData(self, messageData):
        """
        A box.

        @param messageData: a serialized AMP box representing either a message
        or an error.
        @type messageData: L{str}

        @raise MalformedMessage: if the C{messageData} parameter does not parse
        to exactly one AMP box.
        """
        inputBoxes = parseString(messageData)
        if not len(inputBoxes) == 1:
            raise MalformedMessage()
        [inputBox] = inputBoxes
        return inputBox


    def messageReceived(self, value, sender, target):
        """
        An AMP-formatted message was received.  Dispatch to the appropriate
        command responder, i.e. a method on this object exposed with
        L{commandMethod.expose}.

        @see IMessageReceiver.messageReceived
        """
        if value.type != AMP_MESSAGE_TYPE:
            raise UnknownMessageType()
        inputBox = self._boxFromData(value.data)
        thunk = commandMethod.responderForName(self, inputBox[COMMAND])
        placeholder = _ProtocolPlaceholder(sender, target)
        arguments = thunk.command.parseArguments(inputBox, placeholder)
        try:
            result = thunk(**arguments)
        except tuple(thunk.command.errors.keys()), knownError:
            errorCode = thunk.command.errors[knownError.__class__]
            raise RevertAndRespond(
                Value(AMP_ANSWER_TYPE,
                         Box(_error_code=errorCode,
                             _error_description=str(knownError)).serialize()))
        else:
            response = thunk.command.makeResponse(result, None)
            return Value(AMP_ANSWER_TYPE, response.serialize())


    def answerReceived(self, value, originalValue,
                       originalSender, originalTarget):
        """
        An answer was received.  Dispatch to the appropriate answer responder,
        i.e. a method on this object exposed with L{answerMethod.expose}.

        @see IDeliveryConsequence.answerReceived
        """
        if value.type != AMP_ANSWER_TYPE:
            raise UnknownMessageType()
        commandName = self._boxFromData(originalValue.data)[COMMAND]
        rawArgs = self._boxFromData(value.data)
        placeholder = _ProtocolPlaceholder(originalSender, originalTarget)
        if ERROR in rawArgs:
            thunk = errorMethod.errbackForName(self, commandName, rawArgs[ERROR])
            thunk(Failure(thunk.exception()))
        else:
            thunk = answerMethod.responderForName(self, commandName)
            arguments = thunk.command.parseResponse(rawArgs, placeholder)
            thunk(**arguments)


__all__ = ['AMPMessenger', 'AMPReceiver', 'AMP_ANSWER_TYPE', 'AMP_MESSAGE_TYPE',
           'DELIVERY_ERROR', 'ERROR', 'ERROR_BAD_SENDER', 'ERROR_NO_SHARE',
           'ERROR_NO_USER', 'ERROR_REMOTE_EXCEPTION', 'LocalMessageRouter',
           'MessageQueue', 'SenderArgument', 'TargetArgument', 'Value',
           'answerMethod', 'commandMethod', 'errorMethod']
