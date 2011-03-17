"""
Tests for L{xquotient.popout}.
"""

from twisted.trial.unittest import TestCase
from twisted.internet.defer import maybeDeferred, Deferred, AlreadyCalledError
from twisted.python.failure import Failure
from twisted.internet.error import ConnectionDone
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ICredentialsChecker

from twisted.test.proto_helpers import StringTransport

from twisted.mail.pop3client import POP3Client

from twisted.test.iosim import connectedServerAndClient

from axiom.store import Store
from axiom.userbase import LoginSystem, LoginAccount, LoginMethod
from axiom.test.util import getPristineStore, QueryCounter
from axiom.dependency import installOn

from xquotient.mail import DeliveryAgent
from xquotient.popout import POP3Up, POP3ServerFactory, _ndchain, MessageInfo
from xquotient.exmess import Message

def createStore(testCase):
    location = testCase.mktemp()
    s = Store(location)
    da = DeliveryAgent(store=s)
    installOn(da, s)
    makeSomeMessages(testCase, da, location)
    installOn(POP3Up(store=s), s)
    ls = LoginSystem(store=s)
    installOn(ls, s)

    # Engage in some trickery to allow this to be used as its own user.
    la = LoginAccount(store=s, password=u'asdfjkl;', avatars=s, disabled=False)
    LoginMethod(store=s, account=la,
                localpart=u'user', domain=u'example.com',
                protocol=u'email', internal=True, verified=True)
    return s

def makeSomeMessages(testCase, da, location):
    for msgText in testCase.messageTexts:
        receiver = da.createMIMEReceiver(u'test://' + location)
        receiver.feedStringNow(msgText)

class MailboxTestCase(TestCase):

    messageTexts = [
        "Message: value\n"
        "\n"
        "Bye\n",

        "Header: isn't it fun\n"
        "\n"
        "bye\n",

        "o/` They say every man must need protection o/`\n",
        "o/` They say every man must fall o/`\n",
        "o/` And I swear I see my reflection o/`\n",
        "o/` Someplace so high above the wall o/`\n",
        "o/` I see my light come shining, from the west down to the east o/`\n",
        "o/` Any day now, any day now, I shall be released o/`\n",

        'Third-Message: This One\n'
        '\n'
        'Okay\n',
        ]

    def setUp(self):
        self.store = getPristineStore(self, createStore)
        self.mailbox = self.store.findUnique(POP3Up)
        realm = IRealm(self.store)
        checker = ICredentialsChecker(self.store)
        self.portal = Portal(realm, [checker])


    def test_logoutClearsMailbox(self):
        """
        Verify that userbase's 'logout' mechanism will clear out the mailbox,
        allowing new instances to retrieve new UIDL lists.
        """
        # XXX: there are some problems here.  There is a race condition if you
        # log in with 2 POP clients, then one logs out: the other will be left
        # without a functional mailbox implementation.  Since there is no login
        # notification, we can't even figure out when the last login should
        # happen.  When #1854 is resolved, we should create separate POP server
        # instances for each connection, each with its own mailbox
        # implementation, and this will no longer be an issue.  I think this
        # test will also go away or morph when that happens.
        self.mailbox._deferOperation("listMessages")
        r1 = self.mailbox.actualMailbox
        self.mailbox._deferOperation("listMessages")
        r2 = self.mailbox.actualMailbox
        self.mailbox.logout()
        self.mailbox._deferOperation("listMessages")
        r3 = self.mailbox.actualMailbox
        self.failUnlessIdentical(r1, r2)
        self.failIfIdentical(r2, r3)


    def test_cooperativeLogin(self):
        """
        Verify that the mailbox will be loaded without hanging the server for
        an inordinate period of time.
        """
        qc = QueryCounter(self.store)
        n = []
        def m():
            n.append(self.mailbox._realize())
        self.assertEquals(qc.measure(m), 0)
        [actual] = n
        n[:] = []
        actual.coiterate = lambda x: n.append(x) or Deferred()
        actual.pagesize = 1
        da = self.store.findUnique(DeliveryAgent)
        location = u'extra'

        # this next line initializes the table for pop3, which accounts for a
        # fairly steep startup cost.  TODO: optimize axiom so this isn't as
        # steep.
        self.store.query(MessageInfo).deleteFromStore()
        # Spooky action-at-a-distance stuff: initialize transactional
        # bookkeeping for Message table, I think?  Otherwise there are a few
        # hundred extra bytecodes on the 'bootstrap' which we never see again
        # in subsequent runs of the exact same query.  This actually works
        # whether or not the query is in a transaction: all that is necessary
        # is thata a transaction take place in the store, and that the Message
        # table be queried in some way.  (As you can see, no results need be
        # gathered.)
        self.store.transact(list, self.store.query(Message, limit=0))
        # self.store.transact(lambda : None)

        self.assertEquals(qc.measure(actual.kickoff), 0)
        [tickit] = n
        n[:] = []
        bootstrapBaseline = qc.measure(tickit.next)
        baseline = qc.measure(tickit.next)
        for x in range(2):
            self.store.query(MessageInfo).deleteFromStore()
            # Eliminate all the previously-created message information
            self.assertEquals(qc.measure(actual.kickoff), 0)
            [tickit] = n
            n[:] = []
            self.assertEquals(qc.measure(tickit.next), bootstrapBaseline)
            self.store.transact(makeSomeMessages, self, da, location)
            self.assertEquals(qc.measure(tickit.next), baseline)
            # exhaust it so we can start again
            while True:
                try:
                    # "<=" because the _last_ iteration will be 1 less than all
                    # the previous, due to the successful comparison/exit
                    # instruction
                    self.failUnless(qc.measure(tickit.next) <= baseline)
                except StopIteration:
                    break


    def test_listMessagesAggregate(self):
        """
        Test that the listMessages method, when invoked with no argument,
        returns the sizes of the messages in the mailbox.
        """
        d = maybeDeferred(self.mailbox.listMessages)
        d.addCallback(self.assertEquals, map(len, self.messageTexts))
        return d


    def test_listMessagesOverflow(self):
        """
        Test that listMessages properly raises a ValueError when passed an
        integer which would index past the end of the mailbox.
        """
        d = maybeDeferred(self.mailbox.listMessages, len(self.messageTexts))
        return self.assertFailure(d, ValueError)


    def test_listMessagesDeleted(self):
        """
        Test that listMessages properly returns 0 for the size of a deleted
        message.
        """
        def deleted(ign):
            self.mailbox.deleteMessage(0)
            d = maybeDeferred(self.mailbox.listMessages, 0)
            d.addCallback(self.assertEquals, 0)
            return d
        return self.realize().addCallback(deleted)


    def test_listMessages(self):
        """
        Test that listMessages properly returns the size of a specific message.
        """
        d = maybeDeferred(self.mailbox.listMessages, 1)
        d.addCallback(self.assertEquals, len(self.messageTexts[1]))
        return d


    def test_getMessageOverflow(self):
        """
        Test that getMessage properly raises a ValueError when passed an index
        beyond the end of the mailbox.
        """
        d = maybeDeferred(self.mailbox.getMessage, len(self.messageTexts))
        return self.assertFailure(d, ValueError)


    def test_getMessageDeleted(self):
        """
        Test that getMessage properly raises a ValueError when asked for a
        message which has been deleted.
        """
        def deleted(ign):
            self.mailbox.deleteMessage(1)
            d = maybeDeferred(self.mailbox.getMessage, 1)
            return self.assertFailure(d, ValueError)
        return self.realize().addCallback(deleted)


    def test_getMessage(self):
        """
        Test that a file-like object for a valid message index can be retrieved
        through getMessage.
        """
        d = maybeDeferred(self.mailbox.getMessage, 0)
        d.addCallback(lambda fObj: fObj.read())
        d.addCallback(self.assertEquals, self.messageTexts[0])
        return d


    def realize(self):
        """
        Fully load mailbox.  Normally this would be done by listMessages, which
        will generally be the first thing called on the connection.
        """
        return self.mailbox._realize().whenReady()


    def test_getUidlOverflow(self):
        """
        Test that getUidl properly raises a ValueError when asked for a message
        which is beyond the end of the mailbox.
        """
        # See the note on test_getUidl
        def theTest(result):
            self.assertRaises(ValueError, self.mailbox.getUidl, len(self.messageTexts))
        return self.realize().addCallback(theTest)


    def test_getUidlDeleted(self):
        """
        Test that getUidl properly raises a ValueError when asked to retrieve
        information about a deleted message.
        """
        def deleted(ign):
            self.mailbox.deleteMessage(1)
            self.assertRaises(ValueError, self.mailbox.getUidl, 1)
        return self.realize().addCallback(deleted)


    def test_getUidl(self):
        """
        Test that getUidl returns a unique identifier for each message.
        """
        # Note: the implementation of this test as synchronous after forcibly
        # realizing the mailbox is, unfortunately, a requirement of Twisted's
        # POP3 implementation.  Currently it cannot accept Deferred results
        # from getUidl.  More importantly it's not clear if it _should_ accept
        # Deferred results from getUidl (although the documentation needs to be
        # updated), since the right time to load the mailbox is the login
        # deferred.  Practically speaking, this shouldn't actually matter in
        # production because listMessages must, for all practical purposes, be
        # called on the same connection before calling getUidl.  For a
        # description of how to work around this issue without overhauling all
        # of Twisted's POP3 support, see Divmod ticket #1854.
        def theTest(ignored):
            results = [self.mailbox.getUidl(i)
                       for i
                       in xrange(len(self.messageTexts))]
            uids = set()
            for res in results:
                if res in uids:
                    self.fail("Duplicate UID: %r" % (res,))
                uids.add(res)
        return self.realize().addCallback(theTest)


    def test_deleteMessageOverflow(self):
        """
        Test that deleteMessage properly raises a ValueError when asked to
        delete a message which is beyond the end of the mailbox.
        """
        def theTest(result):
            self.assertRaises(ValueError, self.mailbox.deleteMessage,
                              len(self.messageTexts))
        return self.realize().addCallback(theTest)


    def test_deleteMessageDeleted(self):
        """
        Test that deleteMessage properly raises a ValueError when asked to
        delete a message which has already been deleted.
        """
        def deleted(ign):
            self.mailbox.deleteMessage(0)
            self.assertRaises(ValueError, self.mailbox.deleteMessage, 0)
        return self.realize().addCallback(deleted)


    def test_undeleteMessages(self):
        """
        Test that messages which have previously been deleted once again become
        available after undeleteMessages is called.
        """
        def theTest(ign):
            self.mailbox.deleteMessage(0)
            self.mailbox.undeleteMessages()
            d = maybeDeferred(self.mailbox.listMessages, 0)
            d.addCallback(self.assertEquals, len(self.messageTexts[0]))
            return d
        return self.realize().addCallback(theTest)


    def test_sync(self):
        """
        Test that messages which have previously been deleted do not again
        become available after undeleteMessages is called if a call to sync is
        made in the intervening time.
        """
        def theTest(ign):
            self.mailbox.deleteMessage(0)
            self.mailbox.sync()
            # Sync needs to re-realize the mailbox before it's useful again.
            return self.realize()
        d = self.realize().addCallback(theTest)

        def undeleted(ign):
            self.mailbox.undeleteMessages()
            d = maybeDeferred(self.mailbox.listMessages)
            def retrieved(messages):
                self.assertEquals(len(messages), len(self.messageTexts) - 1)
                self.assertEquals(messages, map(len, self.messageTexts[1:]))
            d.addCallback(retrieved)
            return d
        return d.addCallback(undeleted)


    def test_basicProtocol(self):
        """
        This is an integration test which combines Twisted's pop3 client and server
        byte-level protocol logic and the server to verify that the protocol
        exposed to the client lists the same UIDs that the server
        implementation expects to export.
        """
        from twisted.internet.base import DelayedCall
        DelayedCall.debug = True
        c, s, p = connectedServerAndClient(
            ServerClass=lambda :
            POP3ServerFactory(self.portal).buildProtocol(None),
            ClientClass=POP3Client)
        s.callLater = lambda f, *a, **k: None # squelch timeouts
        r = self.mailbox._realize()
        L = []
        def doItSynchronously(iterator):
            inner = Deferred()
            ir = list(iterator)
            L.append((inner, ir))
            return inner
        def flushSync():
            for (inner, results) in L:
                inner.callback(results)
        s.schedule = doItSynchronously
        r.coiterate = doItSynchronously
        p.flush()
        d1 = c.login("user@example.com", "asdfjkl;")
        p.flush()
        d = c.listUID()
        p.flush()
        flushSync()
        p.flush()
        self.assertEquals(len(d.result), len(self.messageTexts))
        self.assertEquals(d.result,
                          [r.getUidl(n)
                           for n in range(len(self.messageTexts))])



class ProtocolTestCase(TestCase):
    def setUp(self):
        """
        Create a store with a LoginSystem and a portal wrapped around it.
        """
        store = Store()
        installOn(LoginSystem(store=store), store)
        realm = IRealm(store)
        checker = ICredentialsChecker(store)
        self.portal = Portal(realm, [checker])


    def test_incompleteUsername(self):
        """
        Test that a login attempt using a username without a domain part
        results in a customized authentication failure message which points
        out that a domain part should be included in the username.
        """
        factory = POP3ServerFactory(self.portal)
        protocol = factory.buildProtocol(('192.168.1.1', 12345))
        transport = StringTransport()
        protocol.makeConnection(transport)
        protocol.dataReceived("USER testuser\r\n")
        transport.clear()
        protocol.dataReceived("PASS password\r\n")
        written = transport.value()
        protocol.connectionLost(Failure(ConnectionDone()))

        self.assertEquals(
            written,
            '-ERR Username without domain name (ie "yourname" instead of '
            '"yourname@yourdomain") not allowed; try with a domain name.\r\n')




class UtilityTestCase(TestCase):
    """
    Test utility functionality which is currently specific to the POP3 module.
    """

    def test_nonDestructiveDeferredCallback(self):
        """
        Verify the use of non-destructive deferred chaining: a chained deferred is
        created with a callback that returns nothing - verify that a second
        callback on the original deferred receives the original value.
        """
        x = Deferred()
        chained = []
        notchained = []
        def ccb(val):
            chained.append(val)
            return 3
        ndc =_ndchain(x).addCallback(ccb)
        def ucb(val):
            notchained.append(val)
            return 4
        x.addCallback(ucb)
        x.callback(2)
        self.assertEquals(notchained, [2])
        self.assertEquals(chained, [2])
        self.assertEquals(ndc.result, 3)
        self.assertEquals(x.result, 4)


    def test_nonDestructiveDeferredAbuse(self):
        """
        Verify that the non-destructive deferred will not break its callback,
        even if its result is (incorrectly) called back externally.
        """
        x = Deferred()
        boom = _ndchain(x)
        boom.callback(1)
        l = []
        x.addCallback(lambda n : (l.append(n) or 9))
        x.callback(7)
        self.assertEquals(l, [7])
        self.assertEquals(x.result, 9)
        self.assertEquals(len(self.flushLoggedErrors(AlreadyCalledError)), 1)
