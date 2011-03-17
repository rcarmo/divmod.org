from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from epsilon.extime import Time

from nevow import loaders, rend
from nevow.testutil import renderPage, renderLivePage

from axiom.store import Store
from axiom.dependency import installOn

from xmantissa.people import Person, EmailAddress

from xquotient.exmess import Message, MessageDetail, PartDisplayer
from xquotient.inbox import Inbox, InboxScreen
from xquotient import compose
from xquotient.test.util import MIMEReceiverMixin, PartMaker, ThemedFragmentWrapper
from xquotient.qpeople import MessageList, MessageLister

from xquotient.test.util import DummyMessageImplementation
from xquotient.test.test_inbox import testMessageFactory

def makeMessage(receiver, parts, impl):
    """
    Create a new L{exmess.Message}, either by parsing C{parts} or by wrapping
    one around C{impl}.
    """
    if impl is None:
        return receiver.feedStringNow(parts)
    else:
        return testMessageFactory(store=impl.store,
                                  receivedWhen=Time(),
                                  sentWhen=Time(),
                                  spam=False,
                                  subject=u'',
                                  impl=impl)



class RenderingTestCase(TestCase, MIMEReceiverMixin):
    aBunchOfRelatedParts = PartMaker(
        'multipart/related', 'related',
        *(list(PartMaker('text/html', '<p>html-' + str(i) + '</p>')
               for i in xrange(100)) +
          list(PartMaker('image/gif', '')
               for i in xrange(100)))).make()


    def setUp(self):
        """
        Make a copy of the very minimal database for a single test method to
        mangle.
        """
        receiver = self.setUpMailStuff()
        makeMessage(receiver, self.aBunchOfRelatedParts, None)


    def test_messageRendering(self):
        """
        Test rendering of message detail for an extremely complex message.
        """
        msg = self.substore.findUnique(Message)
        msg.classifyClean()
        return renderLivePage(
                   ThemedFragmentWrapper(
                       MessageDetail(msg)))


    def test_inboxRendering(self):
        """
        Test rendering of the inbox with a handful of extremely complex
        messages in it.
        """
        def deliverMessages():
            for i in xrange(5):
                makeMessage(
                    self.createMIMEReceiver(), self.aBunchOfRelatedParts, None)
        self.substore.transact(deliverMessages)

        inbox = self.substore.findUnique(Inbox)

        composer = compose.Composer(store=self.substore)
        installOn(composer, self.substore)

        return renderLivePage(
                   ThemedFragmentWrapper(
                       InboxScreen(inbox)))


    def test_inboxComposeFragmentRendering(self):
        """
        Test rendering of the L{xquotient.compose.ComposeFragment} returned
        from L{xquotient.inbox.InboxScreen.getComposer}
        """
        installOn(compose.Composer(store=self.substore), self.substore)

        inbox = self.substore.findUnique(Inbox)
        inboxScreen = InboxScreen(inbox)

        composeFrag = inboxScreen.getComposer()

        return renderLivePage(
            ThemedFragmentWrapper(composeFrag))


    def test_peopleMessageListRendering(self):
        mlister = MessageLister(store=self.substore)
        installOn(mlister, self.substore)

        p = Person(store=self.substore, name=u'Bob')

        EmailAddress(store=self.substore, person=p, address=u'bob@internet')

        for i in xrange(5):
            testMessageFactory(
                store=self.substore, subject=unicode(str(i)),
                receivedWhen=Time(), spam=False, sender=u'bob@internet')


        self.assertEqual(len(list(mlister.mostRecentMessages(p))), 5)
        return renderPage(
            rend.Page(docFactory=loaders.stan(MessageList(mlister, p))))



class MockPart(object):
    """
    A mock L{xquotient.mimestorage.Part} which implements enough functionality
    to satisfy L{xquotient.exmess.PartDisplayer}
    """
    def __init__(self, unicodeBody, contentType='text/plain'):
        """
        @param unicodeBody: the body of the part
        @type unicodeBody: C{unicode}

        @param contentType: the content type of the part.  defaults to
        text/plain
        @type contentType: C{str}
        """
        self.unicodeBody = unicodeBody
        self.contentType = contentType


    def getUnicodeBody(self):
        return self.unicodeBody


    def getBody(self, decode=False):
        return str(self.unicodeBody)


    def getContentType(self):
        return self.contentType



class PartDisplayerTestCase(TestCase):
    """
    Tests for L{xquotient.exmess.PartDisplayer}
    """
    def setUp(self):
        self.partDisplayer = PartDisplayer(None)


    def test_scrubbingInvalidDocument(self):
        """
        Pass a completely malformed document to L{PartDisplayer.scrubbedHTML}
        and assert that it returns C{None} instead of raising an exception.
        """
        self.assertIdentical(None, self.partDisplayer.scrubbedHTML(''))


    def test_scrubbingSimpleDocument(self):
        """
        Pass a trivial document to L{PartDisplayer.scrubbedHMTL} and make sure
        it comes out the other side in-tact.
        """
        self.assertEquals('<div></div>', self.partDisplayer.scrubbedHTML('<div></div>'))


    def test_renderablePartReplacesInvalidCharsinHTML(self):
        """
        Test that L{xquotient.exmess.PartDisplayer.renderablePart} replaces
        XML-illegal characters in the body of the text/html part it is passed
        """
        part = MockPart(u'<div>\x00 hi \x01</div>', 'text/html')
        tag = self.partDisplayer.renderablePart(part)
        self.assertEquals(tag.content, '<div>0x0 hi 0x1</div>')

    def test_renderablePartDoesntReplaceInvalidCharsElsewhere(self):
        """
        Test that L{xquotient.exmess.PartDisplayer.renderablePart} doesn't
        replace XML-illegal characters if the content-type of the part isn't
        text/html
        """
        part = MockPart(u'\x00', 'text/plain')
        tag = self.partDisplayer.renderablePart(part)
        self.assertEquals(tag.content, '\x00')
