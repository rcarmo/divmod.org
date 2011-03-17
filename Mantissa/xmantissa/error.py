# -*- test-case-name: xmantissa.test -*-

"""
Exception definitions for Mantissa.
"""

from nevow.errors import MissingDocumentFactory


class ArgumentError(Exception):
    """
    Base class for all exceptions raised by the address parser due to malformed
    input.
    """



class AddressTooLong(ArgumentError):
    """
    Exception raised when an address which exceeds the maximum allowed length
    is given to the parser.
    """



class InvalidAddress(ArgumentError):
    """
    Exception raised when an address is syntactically invalid.
    """



class InvalidTrailingBytes(ArgumentError):
    """
    Exception raised when there are extra bytes at the end of an address.
    """



class Unsortable(Exception):
    """
    This exception is raised when a client invalidly attempts to sort a table
    view by a column that is not available for sorting.
    """



class MessageTransportError(Exception):
    """
    A message transport failed in some unrecoverable way; the transmission
    needs to be retried.
    """



class BadSender(Exception):
    """
    A substore attempted to send a message for a username / domain pair for
    which it was not authorized.

    @ivar attemptedSender: A unicode string, formatted as user@host, that
    indicates the user ID that the system attempted to send a message from.

    @ivar allowedSenders: A list of unicode strings, formatted like
    C{attemptedSender}, indicating the senders that the system is allowed to
    send messages as.
    """
    def __init__(self, attemptedSender, allowedSenders):
        """
        Create a L{BadSender} exception with the list of attempted senders and
        the list of allowed senders.
        """
        self.attemptedSender = attemptedSender
        self.allowedSenders = allowedSenders
        Exception.__init__(self, allowedSenders[0].encode('utf-8') +
                           " attempted to send message as " +
                           self.attemptedSender.encode('utf-8'))



class UnknownMessageType(Exception):
    """
    A message of an unknown type was received.
    """



class MalformedMessage(Exception):
    """
    A message of the AMP message type was received, but its body could not be
    parsed as a single AMP box.
    """



class RevertAndRespond(Exception):
    """
    This special exception type allows an
    L{xmantissa.ixmantissa.IMessageReceiver.messageReceived} implementation to
    generate an answer, but revert the transaction where the application is
    processing the application logic.

    @ivar value: the L{Value} of the answer to be issued.
    """

    def __init__(self, value):
        """
        Create a L{RevertAndRespond} with an answer that will be provided to
        the message sender.
        """
        self.value = value



class CouldNotLoadFromThemes(MissingDocumentFactory):
    """
    An L{INavigableFragment} didn't have a C{docFactory}, and also didn't have
    a C{fragmentName} that could be used to load one from a theme.  This
    exception should help developers with debugging when they forget to give a
    docFactory or a fragmentName to an element.
    """

    def __init__(self, element, themes):
        """
        @param element: The L{INavigableFragment} that was being rendered.

        @param themes: A list of L{ITemplateNameResolver}s.
        """
        MissingDocumentFactory.__init__(self, element)
        self.themes = themes


    def __repr__(self):
        """
        A string representation including helpful information about the themes
        that were searched and the element which could not be themed.
        """
        return ("%s: %r (fragment name %r) has no docFactory. Searched these themes: %r"
                % (self.__class__.__name__, self.element,
                   self.element.fragmentName, self.themes))
