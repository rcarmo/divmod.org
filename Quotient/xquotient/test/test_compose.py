import quopri
from StringIO import StringIO

from twisted.trial import unittest
from twisted.python.filepath import FilePath

from email import Parser

from axiom import store
from axiom import item
from axiom import attributes
from axiom.dependency import installOn
from axiom.plugins.axiom_plugins import Create
from axiom.plugins.mantissacmd import Mantissa

from xmantissa.ixmantissa import IWebTranslator

from xquotient import compose, mail, mimeutil, exmess, equotient, smtpout
from xquotient.test.util import PartMaker
from xquotient.mimebakery import createMessage, sendMail
from xquotient.mimepart import Header, MIMEPart

class CompositionTestMixin(object):
    """
    A mixin for setting up an appropriately-factored composition
    environment.

    * Set up a L{store.Store}, optionally on-disk with the 'dbdir'
      argument to setUp.
    * Sets up a C{reactor} attribute on your test case to a
      L{Reactor} that will collect data about connectTCP calls (made
      by the ESMTP-sending code in compose.py; FIXME: make it work
      for the non-smarthost case too).
    * Set up a composer object
    * Set up 2 from addresses
    """

    def setUp(self, dbdir=None):
        self.reactor = Reactor()
        self._originalSendmail = smtpout._esmtpSendmail
        self.patch(smtpout, '_esmtpSendmail', self._esmtpSendmail)

        self.dbdir = self.mktemp()
        self.siteStore = store.Store(self.dbdir)
        Mantissa().installSite(self.siteStore, u"example.org", u"", False)

        self.userAccount = Create().addAccount(
            self.siteStore, u'testuser', u'example.org', u'password')
        self.userStore = self.userAccount.avatars.open()

        self.composer = compose.Composer(store=self.userStore)
        installOn(self.composer, self.userStore)

        self.defaultFromAddr = smtpout.FromAddress(
                                store=self.userStore,
                                smtpHost=u'mail.example.com',
                                smtpUsername=u'radix',
                                smtpPassword=u'secret',
                                address=u'radix@example.com')
        self.defaultFromAddr.setAsDefault()


    def _esmtpSendmail(self, *args, **kwargs):
        kwargs['reactor'] = self.reactor
        return self._originalSendmail(*args, **kwargs)



class StubStoredMessageAndImplAndSource(item.Item):
    """
    Mock several objects at once:

    1. An L{exmess.Message}

    2. The 'impl' attribute of that message, typically a L{mimestore.Part}

    3. The message file returned from the C{open} method of C{impl}.
       XXX: This returns something that doesn't conform to the file protocol,
       but the code that triggers the usage of that protocol isn't triggered
       by the following tests.
    """

    calledStartedSending = attributes.boolean(default=False)
    impl = property(lambda s: s)
    source = property(lambda self: self._source or FilePath(__file__))
    _source = None
    headers = attributes.inmemory()
    statuses = attributes.inmemory()
    def open(self):
        return "HI DUDE"

    def startedSending(self):
        self.calledStartedSending = True

    def addStatus(self, status):
        if not hasattr(self, 'statuses'):
            self.statuses = [status]
        else:
            self.statuses.append(status)

class Reactor(object):
    """
    Act as a reactor that collects connectTCP call data.
    """
    def connectTCP(self, host, port, factory):
        self.host = host
        self.port = port
        self.factory = factory



class ComposeFromTest(CompositionTestMixin, unittest.TestCase):

    def test_sendmailSendsToAppropriatePort(self):
        """
        Sending a message should deliver to the smarthost on the
        configured port.
        """
        self.defaultFromAddr.smtpPort = 26
        message = StubStoredMessageAndImplAndSource(store=self.userStore)
        self.composer.sendMessage(
            self.defaultFromAddr, [u'testuser@example.com'], message)
        self.assertEquals(self.reactor.port, 26)


    def test_sendmailSendsFromAppropriateAddress(self):
        """
        If there are smarthost preferences, the from address that they
        specify should be used.
        """
        message = StubStoredMessageAndImplAndSource(store=self.userStore)
        self.composer.sendMessage(
            self.defaultFromAddr, [u'targetuser@example.com'], message)
        self.failUnless(message.calledStartedSending)
        self.assertEquals(str(self.reactor.factory.fromEmail),
                          self.defaultFromAddr.address)



class RedirectTestCase(CompositionTestMixin, unittest.TestCase):
    """
    Tests for mail redirection
    """
    def setUp(self):
        CompositionTestMixin.setUp(self)
        installOn(mail.DeliveryAgent(store=self.userStore), self.userStore)

    def test_createRedirectedMessage(self):
        """
        Test that L{compose.Composer.createRedirectedMessage} sets the right
        headers
        """
        message = StubStoredMessageAndImplAndSource(store=self.userStore)
        msg = self.composer.createRedirectedMessage(
                self.defaultFromAddr,
                [mimeutil.EmailAddress(
                    u'testuser@localhost',
                    mimeEncoded=False)],
                message)
        m = Parser.Parser().parse(msg.impl.source.open())
        self.assertEquals(m['Resent-To'], 'testuser@localhost')
        self.assertEquals(m['Resent-From'], self.defaultFromAddr.address)
        self.failIfEqual(m['Resent-Date'], None)
        self.failIfEqual(m['Resent-Message-ID'], None)

    def test_redirectHeaderOrdering(self):
        """
        Test that Resent headers get added after Received headers but
        before the rest.
        """
        msgtext = """\
Received: from bob by example.com with smtp (SuparMTA 9.99)
        id 1BfraZ-0001D0-QA
        for alice@example.com; Thu, 01 Jul 2004 02:46:15 +0000
received: from bob by example.com with smtp (SuparMTA 9.99)
        id 1BfraZ-0001D0-QA
        for alice@example.com; Thu, 01 Jul 2004 02:46:17 +0000
From: <bob@example.com>
To: <alice@example.com>
Subject: Hi

Hi
""".replace('\n','\r\n')
        class StubMsgFile:
            def open(self):
                return StringIO(msgtext)
        message = StubStoredMessageAndImplAndSource(store=self.userStore)
        message.__dict__['_source'] = StubMsgFile()
        msg = self.composer.createRedirectedMessage(
                self.defaultFromAddr,
                [mimeutil.EmailAddress(
                    u'testuser@localhost',
                    mimeEncoded=False)],
                message)
        m = Parser.Parser().parse(msg.impl.source.open())
        self.assertEqual(len(m._headers), 9)
        self.assertEqual(m._headers[0][0].lower(), "received")
        self.assertEqual(m._headers[6][0].lower(), "from")

    def test_redirect(self):
        """
        Test L{compose.Composer.redirect}
        """
        message = StubStoredMessageAndImplAndSource(store=self.userStore)
        msg = self.composer.redirect(
                self.defaultFromAddr,
                [mimeutil.EmailAddress(
                    u'testuser@localhost',
                    mimeEncoded=False)],
                message)

        self.assertEquals(
            str(self.reactor.factory.fromEmail),
            self.defaultFromAddr.address)

        self.assertEquals(
            list(self.reactor.factory.toEmail),
            ['testuser@localhost'])

        m = Parser.Parser().parse(
                self.userStore.findUnique(
                    exmess.Message).impl.source.open())

        self.assertEquals(m['Resent-From'], self.defaultFromAddr.address)
        self.assertEquals(m['Resent-To'], 'testuser@localhost')
        self.assertEquals(message.statuses, [exmess.REDIRECTED_STATUS])

    def test_redirectNameAddr(self):
        """
        Test that L{compose.Composer.redirect} removes the display name
        portion of an email address if present before trying to deliver
        directed mail to it
        """
        message = StubStoredMessageAndImplAndSource(store=self.userStore)
        msg = self.composer.redirect(
                self.defaultFromAddr,
                [mimeutil.EmailAddress(
                    u'Joe <joe@nowhere>',
                    mimeEncoded=False)],
                message)

        self.assertEquals(
            list(self.reactor.factory.toEmail),
            ['joe@nowhere'])


    def test_redirectRelatedAddresses(self):
        """
        Test that an outgoing redirected message has the resent from/to
        addresses stored
        """
        message = StubStoredMessageAndImplAndSource(store=self.userStore)

        RESENT_TO_ADDRESS = mimeutil.EmailAddress(
            u'Joe <joe@nowhere>', False)
        self.composer.redirect(
            self.defaultFromAddr,
            [RESENT_TO_ADDRESS],
            message)

        msg = self.userStore.findUnique(exmess.Message)

        def checkCorrespondents(relation, address):
            self.assertEquals(
                self.userStore.query(
                    exmess.Correspondent,
                    attributes.AND(
                        exmess.Correspondent.message == msg,
                        exmess.Correspondent.address == address,
                        exmess.Correspondent.relation == relation)).count(),
                1)

        checkCorrespondents(
            exmess.RESENT_FROM_RELATION, self.defaultFromAddr.address)
        checkCorrespondents(exmess.RESENT_TO_RELATION, RESENT_TO_ADDRESS.email)

class MsgStub:
    impl = MIMEPart()
    statuses = None
    def addStatus(self, status):
        if self.statuses is None:
            self.statuses = [status]
        else:
            self.statuses.append(status)


class ComposeFragmentTest(CompositionTestMixin, unittest.TestCase):
    """
    Test the L{ComposeFragment}.
    """

    def setUp(self):
        """
        Add a DeliveryAgent and a FileCabinet to the user created by
        CompositionTestMixin.setUp.
        """
        CompositionTestMixin.setUp(self)
        da = mail.DeliveryAgent(store=self.userStore)
        installOn(da, self.userStore)
        self.cabinet = compose.FileCabinet(store=self.userStore)
        self.cf = compose.ComposeFragment(self.composer)


    def test_invoke(self):
        """
        L{ComposeFragment.invoke} accepts a browser-generated structure
        representing the values in the compose form, coerces it according to
        the L{Parameters} it defines, and passes the result to the LiveForm
        callable.
        """
        # The from addresses are web ids for FromAddress items.
        fromAddr = IWebTranslator(self.userStore).toWebID(self.defaultFromAddr)

        # Override the callable to see what happens.
        sent = []
        expectedResult = object()
        def fakeSend(fromAddress, toAddresses, subject, messageBody, cc, bcc, files, draft):
            sent.append((fromAddress, toAddresses, subject, messageBody, cc, bcc, files, draft))
            return expectedResult
        self.cf.callable = fakeSend

        toAddresses = [mimeutil.EmailAddress(u'alice@example.com', False),
                       mimeutil.EmailAddress(u'bob@example.org', False)]
        subject = u'Hello World'
        body = u'How are you'
        cc = [mimeutil.EmailAddress(u'carol@example.net', False)]
        bcc = [mimeutil.EmailAddress(u'dennis@example.edu', False)]
        draft = True

        invokeDeferred = self.cf.invoke({
                u'fromAddress': [fromAddr],
                u'toAddresses': [mimeutil.flattenEmailAddresses(toAddresses)],
                u'subject': [subject],
                u'messageBody': [body],
                u'cc': [mimeutil.flattenEmailAddresses(cc)],
                u'bcc': [mimeutil.flattenEmailAddresses(bcc)],
                u'draft': [draft]})

        def cbInvoked(invokeResult):
            self.assertEquals(
                sent,
                [(self.defaultFromAddr, toAddresses, subject, body, cc, bcc, (), draft)])
            self.assertIdentical(invokeResult, expectedResult)
        invokeDeferred.addCallback(cbInvoked)
        return invokeDeferred


    def test_createReply(self):
        """
        Ensure that References and In-Reply-To headers are added to
        outgoing messages.
        """
        parent = MsgStub()
        parent.impl.headers = [Header("message-id", "<msg99@example.com>"),
                               Header("references", "<msg98@example.com>"),
                               Header("references", "<msg97@example.com>")]
        msg = createMessage(self.composer,
                            self.cabinet,
                            parent,
                            self.defaultFromAddr,
            [mimeutil.EmailAddress(
                    'testuser@example.com',
                    mimeEncoded=False)],
            u'Sup dood', u'A body', (), (), u'')
        self.assertEqual([h.value for h in msg.impl.getHeaders('References')],
                         ["<msg98@example.com>",
                          "<msg97@example.com>",
                         "<msg99@example.com>"])
        self.assertEqual(msg.impl.getHeader("In-Reply-To"),
                         "<msg99@example.com>")

    def test_createReplyNoMessageID(self):
        """
        Test replying to messages with no message ID.
        """
        parent = MsgStub()
        parent.impl.headers = []
        msg = createMessage(self.composer,
                            self.cabinet,
                            parent,
                            self.defaultFromAddr,
            [mimeutil.EmailAddress(
                    'testuser@example.com',
                    mimeEncoded=False)],
            u'Sup dood', u'A body', (), (), u'')
        self.assertEqual([h.value for h in msg.impl.getHeaders('References')],
                         [])

    def test_createMessageHonorsSmarthostFromAddress(self):
        """
        Sending a message through the Compose UI should honor the from
        address we give to it
        """
        self.defaultFromAddr.address = u'from@example.com'
        msg = createMessage(self.composer,
                            self.cabinet,
                            None,
                            self.defaultFromAddr,
            [mimeutil.EmailAddress(
                    'testuser@example.com',
                    mimeEncoded=False)],
            u'Sup dood', u'A body', (), (), u'')
        file = msg.impl.source.open()
        msg = Parser.Parser().parse(file)
        self.assertEquals(msg["from"], 'from@example.com')

    def test_createMessageHonorsBCC(self):
        """
        Sending a message through the compose UI should honor the BCC
        addresses we give to it
        """
        sendMail(self.cf._savedDraft,
                 self.composer,
                 self.cabinet,
                 None,
                 None,
                 self.defaultFromAddr,
            [mimeutil.EmailAddress(
                'to@example.com',
                mimeEncoded=False)],
            u'', u'', [],
            [mimeutil.EmailAddress(
                'bcc1@example.com',
                 mimeEncoded=False),
             mimeutil.EmailAddress(
                'bcc2@example.com',
                mimeEncoded=False)],
            u'')
        self.assertEquals(
            list(self.userStore.query(
                    smtpout.DeliveryToAddress).getColumn('toAddress')),
            ['to@example.com', 'bcc1@example.com', 'bcc2@example.com'])

    def _createMessage(self, cc=(), bcc=()):
        """
        Use L{xquotient.mimebakery.createMessage} to make a
        simple message, optionally with CC/BCC headers set

        @param cc: addresses to CC the message to.  defaults to no addresses
        @type cc: sequence of L{xquotient.mimeutils.EmailAddress}
        @param bcc: addresses to BCC the message to.  defaults to no addresses
        @type bcc: sequence of L{xquotient.mimeutils.EmailAddress}

        @return: L{xquotient.exmess.Message}
        """
        return createMessage(
            self.composer,
            self.cabinet,
            None,
            self.defaultFromAddr,
            [mimeutil.EmailAddress(
                'to@example.com',
                mimeEncoded=False)],
            u'', u'', cc, bcc, u'')


    def _createBCCMessage(self):
        """
        Use L{xquotient.mimebakery.createMessage} to make a
        message with a BCC
        """
        return self._createMessage(
            bcc=[mimeutil.EmailAddress(
                'bcc@example.com',
                 mimeEncoded=False)])


    def _createCCMessage(self):
        """
        Use L{xquotient.mimebakery.createMessage} to make a
        message with a BCC
        """
        return self._createMessage(
            cc=[mimeutil.EmailAddress(
                'cc@example.com',
                mimeEncoded=False)])


    def test_createMessageWrapsLines(self):
        """
        Ensure that the text of an outgoing message is wrapped to 78
        characters and that its MIME type is 'text/plain; format=flowed'.
        """
        self.cf._sendOrSave(
            fromAddress=self.defaultFromAddr,
            toAddresses=[mimeutil.EmailAddress(
            u'testuser@127.0.0.1',
                    mimeEncoded=False)],
        subject=u'The subject of the message.',
            messageBody=u' '.join([u'some words'] * 1000),
            cc=[],
            bcc=[],
            files=[],
            draft=False)

        msg = self.userStore.findUnique(smtpout.DeliveryToAddress
                                        )._getMessageSource()
        textPart = Parser.Parser().parse(msg)
        self.assertEqual(textPart.get_content_type(), "text/plain")
        self.assertEqual(textPart.get_param("format"), "flowed")
        body = textPart.get_payload().decode("quoted-printable")
        maxLineLength = max([len(line) for line in body.split("\n")])
        self.failIf(maxLineLength > 78)

    def test_noBCCInTo(self):
        """
        Test that L{xquotient.mimebakery.createMessage} doesn't
        stick the BCC address it's passed into the "To" header
        """
        msg = self._createBCCMessage()
        (addr,) = mimeutil.parseEmailAddresses(msg.impl.getHeader(u'To'))
        self.assertEquals(addr.email, 'to@example.com')

    def test_noBCCHeader(self):
        """
        Test that L{xquotient.mimebakery.createMessage} doesn't
        result in a BCC header on the message it makes, when it's passed a BCC
        address
        """
        msg = self._createBCCMessage()
        self.assertRaises(
            equotient.NoSuchHeader, lambda: msg.impl.getHeader(u'bcc'))


    def test_ccHeader(self):
        """
        Test that the message created by
        L{xquotient.mimebakery.createMessage} has the "cc" header
        set if the C{cc} argument contains an address
        """
        msg = self._createCCMessage()
        self.assertEquals(msg.impl.getHeader(u'cc'), 'cc@example.com')


    def _createMessageWithFiles(self, files):
        """
        Create a message with attachments corresponding to the
        L{xquotient.compose.File} items C{files}
        """
        return createMessage(self.composer,
                             self.cabinet,
                             None,
                             self.defaultFromAddr,
                                [mimeutil.EmailAddress(
                                    'testuser@example.com',
                                    mimeEncoded=False)],
                                u'subject', u'body', (), (),
                                files=list(f.storeID for f in files))

    def _assertFilenameParamEquals(self, part, filename):
        """
        Assert that the C{filename} parameter of the C{content-disposition}
        header of the L{xquotient.mimestorage.Part} C{part} is equal to
        C{filename}

        @type part: L{xquotient.mimestorage.Part}
        @type filename: C{unicode}
        """
        self.assertEquals(
            part.getParam(
                u'filename', header=u'content-disposition'),
                filename)


    def test_createMessageAttachment(self):
        """
        Test L{xquotient.mimebakery.createMessage} when there is an
        attachment
        """
        fileItem = self.cabinet.createFileItem(
                    u'the filename', u'text/plain', 'some text/plain')
        msg = self._createMessageWithFiles((fileItem,))
        (_, attachment) = msg.walkMessage()
        self.assertEquals(
            attachment.part.getBody(decode=True),
            'some text/plain\n')
        self.assertEquals(attachment.type, 'text/plain')
        self._assertFilenameParamEquals(attachment.part, 'the filename')

    def test_createMessageWithMessageAttachment(self):
        """
        Test L{xquotient.mimebakery.createMessage} when there is
        an attachment of type message/rfc822
        """
        fileItem = self.cabinet.createFileItem(
                    u'a message', u'message/rfc822',
                    PartMaker('text/plain', 'some text/plain').make())
        msg = self._createMessageWithFiles((fileItem,))
        rfc822part = list(msg.impl.walk())[-2]
        self.assertEquals(rfc822part.getContentType(), 'message/rfc822')
        self._assertFilenameParamEquals(rfc822part, 'a message')

        (_, textPlainPart) = rfc822part.walk()
        self.assertEquals(textPlainPart.getContentType(), 'text/plain')
        self.assertEquals(textPlainPart.getBody(), 'some text/plain\n')

    def test_createMessageWithMultipartAttachment(self):
        """
        Test L{xquotient.mimebakery.createMessage} when there is
        a multipart attachment
        """
        fileItem = self.cabinet.createFileItem(
                    u'a multipart', u'multipart/mixed',
                    PartMaker('multipart/mixed', 'mixed',
                        PartMaker('text/plain', 'text/plain #1'),
                        PartMaker('text/plain', 'text/plain #2')).make())
        msg = self._createMessageWithFiles((fileItem,))
        multipart = list(msg.impl.walk())[-3]
        self.assertEquals(multipart.getContentType(), 'multipart/mixed')
        self._assertFilenameParamEquals(multipart, 'a multipart')

        (_, textPlain1, textPlain2) = multipart.walk()
        self.assertEquals(textPlain1.getContentType(), 'text/plain')
        self.assertEquals(textPlain1.getBody(), 'text/plain #1\n')

        self.assertEquals(textPlain2.getContentType(), 'text/plain')
        self.assertEquals(textPlain2.getBody(), 'text/plain #2\n')


    def test_createMessageWithBinaryAttachment(self):
        """
        Test L{xquotient.mimebakery.createMessage} when there is
        a binary attachment.  The attachment's part should be encoded as
        base64, with the appropriate content-transfer-encoding header
        """
        fileItem = self.cabinet.createFileItem(
                        u'some stuff', u'application/octet-stream',
                        u'this is the body')
        msg = self._createMessageWithFiles((fileItem,))
        (binPart,) = msg.walkAttachments()
        self.assertEquals(
            binPart.part.getHeader(u'content-transfer-encoding'),
            'base64')
        self.assertEquals(
            binPart.part.getBody(),
            'this is the body'.encode('base64'))


    def test_createMessageWithTextAttachment(self):
        """
        Test L{xquotient.mimebakery.createMessage} when there is
        a text attachment.  The attachment's part should be encoded as
        quoted-printable, with the appropriate content-transfer-encoding
        header
        """
        fileItem = self.cabinet.createFileItem(
                        u'some stuff', u'text/plain',
                        u'this is the body\t')
        msg = self._createMessageWithFiles((fileItem,))
        (textPart,) = msg.walkAttachments()
        self.assertEquals(
            textPart.part.getHeader(u'content-transfer-encoding'),
            'quoted-printable')
        self.assertEquals(
            textPart.part.getBody(),
            quopri.encodestring(
                'this is the body\t', quotetabs=True) + '\n')


    def test_createMessageNotIncoming(self):
        """
        Verify that a message composed via the compose form does not deposit
        anything into the 'incoming' state, so the spam filter will not be
        triggered.
        """
        sq = exmess.MailboxSelector(self.userStore)
        msg = createMessage(
            self.composer,
            self.cabinet,
            None,
            self.defaultFromAddr,
            [mimeutil.EmailAddress(
                    'testuser@example.com',
                    mimeEncoded=False)],
            u'Sup dood', u'A body', u'', u'', u'')
        sq.refineByStatus(exmess.INCOMING_STATUS)
        self.assertEquals(list(sq), [])
        self.assertEquals(msg.hasStatus(exmess.CLEAN_STATUS), False)
        self.failIf(msg.shouldBeClassified)


    def test_clientFacingAPIDraft(self):
        """
        Verify that the client-facing '_sendOrSave' method, invoked by the
        liveform, generates a draft message when told to save the message.

        This is a white-box test.
        """
        self.cf._sendOrSave(
            fromAddress=self.defaultFromAddr,
            toAddresses=[mimeutil.EmailAddress(
                    u'testuser@127.0.0.1',
                    mimeEncoded=False)],
            subject=u'The subject of the message.',
            messageBody=u'The body of the message.',
            cc=[],
            bcc=[],
            files=[],
            draft=True)
        m = self.userStore.findUnique(exmess.Message)
        self.assertEquals(set(m.iterStatuses()),
                          set([exmess.UNREAD_STATUS, exmess.DRAFT_STATUS]))
        self.assertEquals(list(self.userStore.query(smtpout.DeliveryToAddress)),
                          [])


    def test_clientFacingAPISend(self):
        """
        Verify that the client-facing '_sendOrSave' method, invoked by the
        liveform, generates a sent message when told to send the message.

        This is a white-box test.
        """
        self.cf._sendOrSave(
            fromAddress=self.defaultFromAddr,
            toAddresses=[mimeutil.EmailAddress(
                    u'testuser@127.0.0.1',
                    mimeEncoded=False)],
            subject=u'The subject of the message.',
            messageBody=u'The body of the message.',
            cc=[],
            bcc=[],
            files=[],
            draft=False)
        m = self.userStore.findUnique(exmess.Message)
        self.assertEquals(set(m.iterStatuses()),
                          set([exmess.UNREAD_STATUS, exmess.OUTBOX_STATUS]))
        nd = self.userStore.findUnique(smtpout.DeliveryToAddress)
        self.assertIdentical(nd.message, m)



class CreateMessage(unittest.TestCase):
    """
    Tests for internal message-creation APIs.
    """

    def setUp(self):
        """
        Install a bunch of stuff expected by L{mimebakery.createMessage}.
        """
        self.dbdir = self.mktemp()
        self.store = store.Store(self.dbdir)
        self.composer = compose.Composer(store=self.store)
        self.defaultFromAddr = smtpout.FromAddress(
                                store=self.store,
                                smtpHost=u'mail.example.com',
                                smtpUsername=u'radix',
                                smtpPassword=u'secret',
                                address=u'radix@example.com')
        self.defaultFromAddr.setAsDefault()
        da = mail.DeliveryAgent(store=self.store)
        installOn(da, self.store)


    def test_createsPlaintextMessage(self):
        """
        Test that L{mimebakery.createMessage} produces a message of
        type text/plain.
        """

        msg = createMessage(
            self.composer,
            None, None,
            self.defaultFromAddr,
            [mimeutil.EmailAddress(
              'testuser@example.com',
               mimeEncoded=False)],
            u'Sup dood', u'A body', u'', u'', u'')

        self.assertEqual(msg.impl.getContentType(), 'text/plain')
