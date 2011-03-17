# -*- test-case-name: xquotient.test -*-

from zope.interface import Interface

class IMessageSender(Interface):
    """
    B{The} way to send messages from a Quotient account.  Accounts which can
    send messages will have a powerup for this interface.  Adapt them to it
    and call the L{sendMessage} method.
    """
    def sendMessage(toAddresses, message):
        """
        Attempt to send the given message to each of the indicated recipients.

        @param toAddresses: A C{list} of C{unicode} strings representing
        RFC2822 addresses (note: this interface will change at some point
        and begin to require structured objects in this list, rather than
        strings, in order to support forms of message delivery other than
        SMTP).
        @param message: The L{exmess.Message} to send.
        """


class IMIMEDelivery(Interface):
    def createMIMEReceiver(source):
        """Create an object to accept a MIME message.

        @type source: C{unicode}
        @param source: A short string describing the means by which this
        Message came to exist. For example, u'mailto:alice@example.com' or
        u'pop3://bob@example.net'.

        @rtype: L{twisted.mail.smtp.IMessage}
        """


class IHamFilter(Interface):
    """
    Plugin for scoring messages based on their spaminess.
    """

    def classify(message):
        """
        Determine whether a mail is spam or not.
        Scores a message from [0.0..1.0]: lower is spammier.

        @type message: L{xquotient.exmess.Message}
        @param message: The message to score.

        @return: A 2-tuple containing a boolean indicating whether a message is spam or not, and the score.
        """


    def train(spam, message):
        """
        Learn.

        @type spam: C{bool}
        @param spam: A flag indicating whether to train the given message as
        spam or ham.

        @type message: L{xquotient.exmess.Message}
        @param message: The message to train.
        """


    def forgetTraining():
        """
        Lose all stored training information.
        """



class IFilteringRule(Interface):
    """
    Defines a particular rule which defines items as either belonging to a
    particular category or being excluded from it.
    """

    def applyTo(item):
        """
        Determine if the indicated item is matched by this rule or not.

        @rtype: three-tuple of C{bool, bool, object}
        @return: The return value represents three pieces of information.
        The first boolean in the tuple indicates whether this rule matched.
        If it did not, the remaining two items are ignored.  If it did: the
        second boolean is interpreted as an indication of whether to proceed
        to subsequent rules or to stop rule processing here; the third value
        is treated as opaque and passed on through to the action stage of
        filtering.
        """


    def getAction():
        """
        Return the L{IFilteringAction} to take when this rule matches.
        """



class IFilteringAction(Interface):
    """
    Perform some action on an item which was matched by a rule.
    """

    def actOn(filteringPowerup, rule, item, extraData):
        """
        Actually perform some action.

        @param filteringPowerup: The powerup which is ostensibly in charge
        of this action.

        @param rule: The L{IFilteringRule} which matched the item being
        processed.

        @param item: The Item which was matched.

        @param extraData: The third element of the tuple returned by
        C{rule.applyTo}.
        """


class IMessageData(Interface):
    """
    Representation-agnostic methods for uniform access to types of message data.
    """

    def relatedAddresses():
        """
        Get email addresses mentioned in the contents of the message.

        @return: a list of 2-tuples of (relation, L{EmailAddress}) objects
        corresponding to the sender and all the known recipients of this
        message.

        'relation' is a short string.

        Note: in the future the L{EmailAddress} specification of the second
        element of the tuple will likely be expanded to include other types of
        addresses for other types of messages.
        """

    def associateWithMessage(message):
        """
        Associate this message data with an L{xquotient.exmess.Message} object.

        This is a hook to provide a point where implementors may include things
        like: inserting this message data into the same store as the given
        message, or creating associated metadata for the message.

        @param message: the message to associate with.  This will be a
        L{Message} instance already inserted into its store (and thus with a
        storeID), but with no other fields yet filled out.
        """

    def guessSentTime(default=None):
        """
        Try to determine what time this message was sent by looking at its
        contents.

        @param default: the object to return if the sent time is not guessable.
        """

    def getAlternates():
        """
        Get alternate versions of the message body

        @return: a sequence of pairs, the first element holding a descriptive
        label, and the second an L{IMessageData}
        """

    def getAllReplyAddresses():
        """
        Figure out the address(es) that a reply to all people involved this
        message should go to

        @return: Mapping of header names to sequences of
        L{xquotient.mimeutil.EmailAddress} instances.  Keys are 'to', 'cc' and
        'bcc'.
        @rtype: C{dict}
        """


    def getReplyAddresses():
        """
        Figure out the address(es) that a reply to this message should be sent
        to.

        @rtype: sequence of L{xquotient.mimeutil.EmailAddress}
        """
