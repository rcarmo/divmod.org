from twisted.python.filepath import FilePath

from datetime import datetime, timedelta
import time

from nevow.livetrial import testcase
from nevow.athena import LiveFragment, expose
from nevow import inevow

from epsilon.extime import Time

from axiom.store import Store
from axiom.item import Item
from axiom import attributes
from axiom.tags import Catalog
from axiom.userbase import LoginMethod
from axiom.dependency import installOn

from xmantissa.webtheme import getLoader
from xmantissa.webapp import PrivateApplication
from xmantissa.people import Organizer, Person, EmailAddress

from xquotient.inbox import Inbox, InboxScreen, MailboxScrollingFragment
from xquotient import equotient

from xquotient.exmess import MessageDetail, ActionlessMessageDetail
from xquotient.exmess import _UndeferTask as UndeferTask
from xquotient.exmess import (ARCHIVE_STATUS, TRASH_STATUS, SPAM_STATUS,
                              DEFERRED_STATUS, TRAINED_STATUS)

from xquotient.compose import Composer, ComposeFragment
from xquotient.qpeople import MessageLister


from xquotient.test.test_inbox import testMessageFactory



class ThrobberTestCase(testcase.TestCase):
    """
    Tests for the inbox activity indicator.
    """
    jsClass = u'Quotient.Test.ThrobberTestCase'



class ScrollingWidgetTestCase(testcase.TestCase):
    """
    More tests for the inbox-specific ScrollingWidget subclass.
    """
    jsClass = u'Quotient.Test.ScrollingWidgetTestCase'

    def getScrollingWidget(self, howManyElements=0):
        store = Store()
        installOn(PrivateApplication(store=store), store)
        for n in xrange(howManyElements):
            testMessageFactory(store, spam=False)
        f = MailboxScrollingFragment(store)
        f.docFactory = getLoader(f.fragmentName)
        f.setFragmentParent(self)
        return f
    expose(getScrollingWidget)



class ScrollTableTestCase(ScrollingWidgetTestCase):
    """
    Tests for the inbox-specific ScrollingWidget subclass.
    """
    jsClass = u'Quotient.Test.ScrollTableTestCase'

    def getWidgetDocument(self):
        return self.getScrollingWidget()

    def getTimestamp(self):
        return Time.fromDatetime(datetime.now().replace(hour=0,
                                                        minute=0, second=0)
                                 ).asPOSIXTimestamp()
    expose(getTimestamp)

class _Part(Item):
    typeName = 'mock_part_item'
    schemaVersion = 1

    junk = attributes.text()
    source = property(lambda s: FilePath(__file__.rstrip('c')))

    def walkMessage(self, *z):
        return ()
    walkAttachments = walkMessage

    def getHeader(self, *z):
        return u'hi!\N{WHITE SMILING FACE}<>'

    def getParam(self, param, default=None, header=None, un_quote=None):
        if default is not None:
            return default
        raise equotient.NoSuchHeader()

    def associateWithMessage(self, message):
        pass

    def relatedAddresses(self):
        return []

    def guessSentTime(self, default):
        return Time()

    def getAllReplyAddresses(self):
        return {}

    def getReplyAddresses(self):
        return []

class StubComposeFragment(LiveFragment):
    jsClass = ComposeFragment.jsClass
    fragmentName = ComposeFragment.fragmentName

    def __init__(self, composer, recipients, subject, messageBody, attachments, inline, parentMessage, parentAction):
        LiveFragment.__init__(self)
        self.composer = composer
        self.recipients = recipients
        self.subject = subject
        self.messageBody = messageBody
        self.attachments = attachments
        self.inline = inline
        self.invokeArguments = []
        self.parentMessage = parentMessage
        self.parentAction = parentAction

    def getInvokeArguments(self):
        """
        Return a list of form arguments which have been passed to
        C{self.invoke}.
        """
        return self.invokeArguments
    expose(getInvokeArguments)


    # These are the Athena methods required to be exposed
    def invoke(self, arguments):
        self.invokeArguments.append(arguments)
    expose(invoke)


    def getInitialArguments(self):
        return (self.inline, ())


    # Render stuff
    def rend(self, ctx, data):
        """
        Fill the slots the template requires to be filled in order to be
        rendered.
        """
        iq = inevow.IQ(self.docFactory)
        ctx.fillSlots('from', 'bob@example')
        ctx.fillSlots('to', 'alice@example.com')
        ctx.fillSlots('cc', 'bob@example.com')
        ctx.fillSlots('bcc', 'jane@example.com')
        ctx.fillSlots(
            'subject',
            iq.onePattern('subject').fillSlots('subject', 'Test Message'))
        ctx.fillSlots('attachments', '')
        ctx.fillSlots(
            'message-body',
            iq.onePattern('message-body').fillSlots(
                'body', 'message body text'))
        return LiveFragment.rend(self, ctx, data)


    # These are the renderers required by the template.
    def render_fileCabinet(self, ctx, data):
        return ctx.tag


    def render_compose(self, ctx, data):
        return ctx.tag


    def render_inboxLink(self, ctx, data):
        return ctx.tag


    def render_button(self, ctx, data):
        return ctx.tag


class ActionlessMsgDetailWithStubCompose(ActionlessMessageDetail):
    """
    L{xquotient.exmess.ActionlessMessageDetail} subclass which sets
    L{StubComposeFragment} as the factory for compose fragments
    """
    composeFragmentFactory = StubComposeFragment



class _ControllerMixin:
    aliceEmail = u'alice@example.com'
    bobEmail = u'bob@example.com'
    tzfactor = time.daylight and time.altzone or time.timezone
    sent = Time.fromDatetime(datetime(1999, 12, 13))
    sent2 = Time().oneDay() + timedelta(hours=16, minutes=5, seconds=tzfactor)

    def getInbox(self):
        """
        Return a newly created Inbox, in a newly created Store.
        """
        s = Store()
        LoginMethod(store=s,
            internal=False,
            protocol=u'email',
            localpart=u'default',
            domain=u'host',
            verified=True,
            account=s)

        installOn(Composer(store=s), s)
        installOn(Catalog(store=s), s)
        installOn(MessageLister(store=s), s)
        inbox = Inbox(store=s)
        installOn(inbox, s)
        return inbox


    def widgetFor(self, inbox):
        """
        Create and return an InboxScreen for the given inbox.
        """
        fragment = InboxScreen(inbox)
        fragment.messageDetailFragmentFactory = ActionlessMsgDetailWithStubCompose
        fragment.setFragmentParent(self)
        return fragment



class ControllerTestCase(testcase.TestCase, _ControllerMixin):
    jsClass = u'Quotient.Test.ControllerTestCase'

    def getControllerWidget(self):
        """
        Retrieve the Controller widget for a mailbox in a particular
        configuration.

        The particulars of the email in this configuration are::

            There are 5 messages total.

            The inbox contains 2 unread messages.

            The archive contains 2 read messages.

            The spam folder contains 1 unread message.

            The sent folter contains 1 read message.

            The trash folder contains 2 read messages.

        There are also some people.  They are::

            Alice - alice@example.com

            Bob - bob@example.com

        The 1st message in the inbox is tagged "foo".
        The 2nd message in the inbox is tagged "bar".
        """
        inbox = self.getInbox()
        organizer = inbox.store.findUnique(Organizer)
        application = inbox.store.findUnique(PrivateApplication)
        catalog = inbox.store.findUnique(Catalog)

        offset = timedelta(seconds=30)

        impl = _Part(store=inbox.store)

        # Inbox messages
        m1 = testMessageFactory(
            store=inbox.store, sender=self.aliceEmail, subject=u'1st message',
            receivedWhen=self.sent + offset * 8, sentWhen=self.sent2, spam=False,
            archived=False, read=False, impl=impl)
        catalog.tag(m1, u"foo")

        m2 = testMessageFactory(
            store=inbox.store, sender=self.aliceEmail, subject=u'2nd message',
            receivedWhen=self.sent + offset * 7, sentWhen=self.sent,
            spam=False, archived=False, read=False, impl=impl)
        catalog.tag(m2, u"bar")

        # Archive messages
        m3 = testMessageFactory(
            store=inbox.store, sender=self.aliceEmail, subject=u'3rd message',
            receivedWhen=self.sent + offset * 6, sentWhen=self.sent,
            spam=False, archived=True, read=True, impl=impl)

        m4 = testMessageFactory(
            store=inbox.store, sender=self.aliceEmail, subject=u'4th message',
            receivedWhen=self.sent + offset * 5, sentWhen=self.sent,
            spam=False, archived=True, read=True, impl=impl)

        # Spam message
        m5 = testMessageFactory(
            store=inbox.store, sender=self.bobEmail, subject=u'5th message',
            receivedWhen=self.sent + offset * 4, sentWhen=self.sent,
            spam=True, archived=False, read=False, impl=impl)

        # Sent message
        m6 = testMessageFactory(
            store=inbox.store, sender=self.bobEmail, subject=u'6th message',
            receivedWhen=self.sent + offset * 3, sentWhen=self.sent,
            spam=False, archived=False, read=True, outgoing=True,
            recipient=self.aliceEmail, impl=impl)

        # Trash messages
        m7 = testMessageFactory(
            store=inbox.store, sender=self.bobEmail, subject=u'7th message',
            receivedWhen=self.sent + offset * 2, sentWhen=self.sent,
            spam=False, archived=False, read=True, outgoing=False,
            trash=True, impl=impl)

        m8 = testMessageFactory(
            store=inbox.store, sender=self.bobEmail, subject=u'8th message',
            receivedWhen=self.sent + offset, sentWhen=self.sent,
            spam=False, archived=False, read=True, outgoing=False,
            trash=True, impl=impl)

        m9 = testMessageFactory(
            store=inbox.store, sender=self.aliceEmail, subject=u'9th message',
            receivedWhen=self.sent, sentWhen=self.sent,
            spam=False, archived=False, read=True, outgoing=False,
            trash=True, impl=impl)

        # Alice
        alice = Person(store=inbox.store, organizer=organizer, name=u"Alice")
        EmailAddress(store=inbox.store, person=alice, address=self.aliceEmail)

        # Bob
        bob = Person(store=inbox.store, organizer=organizer, name=u"Bob")
        EmailAddress(store=inbox.store, person=bob, address=self.bobEmail)

        self.names = {
            application.toWebID(alice): u'Alice',
            application.toWebID(bob): u'Bob'}

        self.messages = dict(
            (application.toWebID(m), m)
            for m
            in [m1, m2, m3, m4, m5, m6, m7, m8])

        return self.widgetFor(inbox)
    expose(getControllerWidget)


    def getMessageDetail(self, key):
        """
        Return the MessageDetail widget with the given webID.
        """
        detail = MessageDetail(self.messages[key])
        detail.setFragmentParent(self)
        return detail
    expose(getMessageDetail)


    def personNamesByKeys(self, *keys):
        """
        Return the names of the people with the given webIDs.
        """
        return [self.names[k] for k in keys]
    expose(personNamesByKeys)


    def deletedFlagsByWebIDs(self, *ids):
        """
        Return the deleted flag of the messages with the given webIDs.
        """
        return [self.messages[id].hasStatus(TRASH_STATUS) for id in ids]
    expose(deletedFlagsByWebIDs)


    def archivedFlagsByWebIDs(self, *ids):
        """
        Return the archived flag of the messages with the given webIDs.

        XXX: This is a gross hack, as there is no longer a public 'archived'
        flag.
        """
        return [self.messages[id].hasStatus(ARCHIVE_STATUS) for id in ids]
    expose(archivedFlagsByWebIDs)


    def trainedStateByWebIDs(self, *ids):
        """
        Return a dictionary describing the spam training state of the messages
        with the given webID.
        """
        return [{u'trained': self.messages[id].hasStatus(TRAINED_STATUS),
                 u'spam': self.messages[id].hasStatus(SPAM_STATUS)}
                for id in ids]
    expose(trainedStateByWebIDs)


    def _getDeferredState(self, msg):
        if msg.hasStatus(DEFERRED_STATUS):
            # XXX UndeferTask should remember the amount of time, not just the
            # ultimate undefer time.
            t = msg.store.findUnique(UndeferTask, UndeferTask.message == msg)
            return t.deferredUntil.asPOSIXTimestamp()
        return None


    def deferredStateByWebIDs(self, *ids):
        """
        Return the deferred flag of the messages with the given webIDs.
        """
        return [self._getDeferredState(self.messages[id]) for id in ids]
    expose(deferredStateByWebIDs)



class EmptyInitialViewControllerTestCase(testcase.TestCase, _ControllerMixin):
    """
    Tests for behaviors where the mailbox loads and the initial view is empty,
    but other views contain messages.
    """
    jsClass = u'Quotient.Test.EmptyInitialViewControllerTestCase'

    def getControllerWidget(self):
        """
        Retrieve the Controller widget for a mailbox with no message in the
        inbox view but several messages in the archive view.
        """
        inbox = self.getInbox()


        offset = timedelta(seconds=30)

        impl = _Part(store=inbox.store)

        # Archive messages
        m1 = testMessageFactory(
            store=inbox.store, sender=self.aliceEmail, subject=u'1st message',
            receivedWhen=self.sent, sentWhen=self.sent, spam=False,
            archived=True, read=False, impl=impl)

        m2 = testMessageFactory(
            store=inbox.store, sender=self.aliceEmail, subject=u'2nd message',
            receivedWhen=self.sent + offset, sentWhen=self.sent,
            spam=False, archived=True, read=False, impl=impl)

        return self.widgetFor(inbox)
    expose(getControllerWidget)



class EmptyControllerTestCase(testcase.TestCase, _ControllerMixin):
    jsClass = u'Quotient.Test.EmptyControllerTestCase'

    def getEmptyControllerWidget(self):
        """
        Retrieve the Controller widget for a mailbox with no messages in it.
        """
        return self.widgetFor(self.getInbox())
    expose(getEmptyControllerWidget)


class FullControllerTestCase(testcase.TestCase, _ControllerMixin):
    jsClass = u'Quotient.Test.FullControllerTestCase'

    def getFullControllerWidget(self):
        """
        Retrieve the Controller widget for a mailbox with twenty messages in
        it.
        """
        inbox = self.getInbox()
        inbox.uiComplexity = 3
        catalog = inbox.store.findUnique(Catalog)

        impl = _Part(store=inbox.store)
        messages = [
            testMessageFactory(store=inbox.store, sender=self.aliceEmail,
                               subject=u'message %d' % (i,),
                               receivedWhen=self.sent,
                               sentWhen=self.sent2, spam=False, archived=False,
                               read=False, impl=impl)
            for i in range(20)]

        catalog.tag(messages[1], u'foo')

        return self.widgetFor(inbox)
    expose(getFullControllerWidget)



class MailboxStatusTestCase(testcase.TestCase):
    """
    Tests for Quotient.Mailbox.Status
    """
    jsClass = u'Quotient.Test.MailboxStatusTestCase'



class FocusControllerTestCase(testcase.TestCase, _ControllerMixin):
    jsClass = u'Quotient.Test.FocusControllerTestCase'

    def getFocusControllerWidget(self):
        """
        Retrieve the Controller widget for a mailbox with two messages, one
        focused and one not.
        """
        inbox = self.getInbox()
        inbox.uiComplexity = 3

        impl = _Part(store=inbox.store)

        # One focused message
        m = testMessageFactory(
            store=inbox.store,
            sender=self.aliceEmail,
            subject=u'focused message',
            receivedWhen=self.sent,
            sentWhen=self.sent2,
            spam=False,
            archived=False,
            read=True,
            impl=impl)
        m.focus()

        # One unfocused message in the inbox
        testMessageFactory(
            store=inbox.store,
            sender=self.aliceEmail,
            subject=u'unfocused message',
            receivedWhen=self.sent,
            sentWhen=self.sent2,
            spam=False,
            archived=False,
            read=True,
            impl=impl)

        return self.widgetFor(inbox)
    expose(getFocusControllerWidget)
