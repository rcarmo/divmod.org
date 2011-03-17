from xshtoom.sdp import SDP, MediaDescription
from xshtoom.rtp.formats import PT_PCMU
from sine.test.test_sip import  TaskQueue
from sine import sip, useragent, sipserver
from twisted.internet import reactor, defer, task
from twisted.trial import unittest
from twisted.test.proto_helpers import StringTransport
from twisted.cred.portal import Portal
from zope.interface import implements
from axiom import store, userbase, item, attributes
from axiom.dependency import installOn

from epsilon import juice, hotfix
hotfix.require("twisted", "proto_helpers_stringtransport")

exampleInvite = """INVITE sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9\r
Max-Forwards: 70\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
v=0\r
o=alice 2890844526 2890844526 IN IP4 server.com\r
s=-\r
c=IN IP4 10.0.0.1\r
t=0 0\r
m=audio 49172 RTP/AVP 0\r
a=rtpmap:0 PCMU/8000\r
"""


response180 = """\
SIP/2.0 180 Ringing\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1;received=10.0.0.1\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
Contact: <sip:bob@server.com>\r
CSeq: 1 INVITE\r
\r
"""

response200 = """SIP/2.0 200 OK\r
Via: SIP/2.0/UDP client.com:1234;branch=z9hG4bK74bf9;received=10.0.0.1\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
User-Agent: Divmod Sine\r
Content-Length: 123\r
Content-Type: application/sdp\r
Contact: sip:bob@127.0.0.2\r
\r
v=0\r
o=bob 69086 69086 IN IP4 127.0.0.2\r
s=shtoom\r
c=IN IP4 127.0.0.2\r
t=0 0\r
m=audio 17692 RTP/AVP 0\r
a=rtpmap:0 PCMU/8000\r

"""

ackRequest = """\
ACK sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74b76\r
Max-Forwards: 70\r
Route: sip:proxy2.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 ACK\r
\r
"""

byeRequest = """\
BYE sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7\r
Max-Forwards: 70\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 BYE\r
\r
"""

byeResponse = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7;received=10.0.0.2\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
User-Agent: Divmod Sine\r
CSeq: 1 BYE\r
Content-Length: 0\r
\r
"""

class FakeAvatar(item.Item):
    implements(sip.IVoiceSystem)

    attr = attributes.reference(doc="an attribute")
    powerupInterfaces = (sip.IVoiceSystem,)

    def localElementByName(self, name):
        return FakeCallRecipient()


class FakeCallRecipient:
    implements(useragent.ICallControllerFactory, useragent.ICallController)

    def acceptCall(self, dialog):
        pass

    def callBegan(self, dialog):
        pass
    def receivedDTMF(self, key):
        pass
    def callEnded(self, dialog):
        pass

    def receivedAudio(self, dialog, bytes):
        pass

    def buildCallController(self, dialog):
        return self

class FakeMediaController:
    def getProcess(self):
        class FakeRTP:
            transport=None
            def createRTPSocket(self, dialog, host):
                return defer.succeed(None)
            def getSDP(self, dialog, othersdp):
                s = SDP()
                m = MediaDescription()
                m.port = 54321
                s.addMediaDescription(m)
                m.addRtpMap(PT_PCMU)
                if othersdp:
                    s.intersect(othersdp)
                return s
            def sendBoxCommand(self, *args):
                return defer.succeed({'done': "True"})
        return defer.succeed(FakeRTP())

class TPCCTest(unittest.TestCase):

    def setUp(self):
        self.clock = sip.clock = task.Clock()
        self.dbdir = self.mktemp()
        self.store = store.Store(self.dbdir)
        self.login = userbase.LoginSystem(store=self.store)
        installOn(self.login, self.store)
        account = self.login.addAccount('bob', 'proxy2.org', None)
        account2 = self.login.addAccount('alice', 'proxy1.org', None)
        us = self.us = account.avatars.open()
        installOn(FakeAvatar(store=us), us)
        us2 = self.us2 = account2.avatars.open()
        installOn(FakeAvatar(store=us2), us2)
        self.tq = TaskQueue(self.clock)
        self.uas = useragent.UserAgent.server(sip.IVoiceSystem(us), "10.0.0.2", FakeMediaController())
        self.uas2 = useragent.UserAgent.server(sip.IVoiceSystem(us2), "10.0.0.1", FakeMediaController())
        self.sip1 = sip.SIPTransport(self.uas, ["server.com"], 5060)
        self.sip1.startProtocol()
        self.sip2 = sip.SIPTransport(self.uas2, ["client.com"], 5060)
        self.sip2.startProtocol()

        self.svc = sipserver.SIPServer(store=self.store)
        self.svc.mediaController = FakeMediaController()
        portal = Portal(self.login, [self.login])
        self.svc.dispatcher = sip.SIPDispatcher(portal, sip.Proxy(portal))
        self.svc.transport = sip.SIPTransport(self.svc.dispatcher, sipserver.getHostnames(self.store), 5060)
        self.svc.dispatcher.start(self.svc.transport)
        dests = {('10.0.0.2', 5060): self.uas, ('10.0.0.1', 5060): self.uas2,
                 ('127.0.0.1', 5060): self.svc}
        self.messages = []
        self.sip1.sendMessage = lambda msg, dest: self.tq.addTask(dests[dest].transport.datagramReceived, str(msg.toString()), ("10.0.0.2", 5060))
        self.sip2.sendMessage = lambda msg, dest: self.tq.addTask(dests[dest].transport.datagramReceived, str(msg.toString()), ("10.0.0.1", 5060))
        self.svc.transport.sendMessage = lambda msg, dest: self.messages.append(msg) or self.tq.addTask(dests[dest].transport.datagramReceived, str(msg.toString()), ("127.0.0.1", 5060))
        useragent.Dialog.genTag = lambda self: "314159"
    def tearDown(self):
        self.clock.advance(33)
        self.clock.advance(33)

    def tearDown(self):
        sip.clock = reactor

    def test3PCC(self):

        self.svc.setupCallBetween(sip.parseAddress("sip:bob@10.0.0.2"),
                                  sip.parseAddress("sip:alice@10.0.0.1"))

    def testDialogAddsSDP(self):
        """
        Previously, there was a bug where no SDP was attached to
        certain INVITEs.  This ensures that it gets added.
        """
        uac = useragent.UserAgent.server(sip.IVoiceSystem(self.us2), "10.0.0.1", FakeMediaController())
        d = useragent.Dialog.forClient(uac, sip.URL(uac.host, "clicktocall"), sip.URL("10.0.0.2", "bob"), None, False, '')
        def invite(dlg):
            return dlg._generateInvite(sip.URL("localhost", "clicktocall"), "", sip.URL("10.0.0.2", "bob"), False)
        def test(dlg):
            sdplines = dlg.msg.body.split('\r\n')
            #There needs to be a m= line at a minimum, probably some other stuff.
            self.failIfEqual([line for line in sdplines if line.startswith("m=")], [])
        return d.addCallback(invite).addCallback(test)

    def testCreateRTPSocket(self):
        lcp = useragent.LocalControlProtocol(False)
        lcp.makeConnection(StringTransport())
        lcp.createRTPSocket("A Dialog", u"server.com")
        box = juice.parseString(lcp.transport.value())
        self.assertEquals(box[0]['host'], "server.com")
        lcp.dataReceived('-Answer: %s\r\nCookie: 123\r\n\r\n' % (box[0]['_ask']))
        self.assertEquals(lcp.dialogs['123'], "A Dialog")
        self.assertEquals(lcp.cookies["A Dialog"], '123')

class CallTerminateTest(unittest.TestCase):

    def setUp(self):
        self.dbdir = self.mktemp()
        self.store = store.Store(self.dbdir)
        self.login = userbase.LoginSystem(store=self.store)
        installOn(self.login, self.store)
        account = self.login.addAccount('bob', 'proxy2.org', None)
        us = account.avatars.open()
        installOn(FakeAvatar(store=us), us)
        self.uas = useragent.UserAgent.server(sip.IVoiceSystem(us), "127.0.0.2", FakeMediaController())
        self.sent = []
        self.sip = sip.SIPTransport(self.uas, ["server.com"], 5060)
        self.sip.startProtocol()
        self.sip.sendMessage = lambda dest, msg: self.sent.append((dest, msg))
        self.testMessages = []
        self.parser = sip.MessagesParser(self.testMessages.append)
        self.clock = sip.clock = task.Clock()
        #XXX this is probably not good
        useragent.Dialog.genTag = lambda self: "314159"

    def tearDown(self):
        self.clock.advance(33)
        self.clock.advance(33)
        sip.clock = reactor

    def assertMsgEqual(self, first, second):
        self.testMessages[:] = []
        if isinstance(first, basestring):
            self.parser.dataReceived(first)
            self.parser.dataDone()
        else:
            #presumably a Message
            self.testMessages.append(first)
        if isinstance(second, basestring):
            self.parser.dataReceived(second)
            self.parser.dataDone()
        else:
            self.testMessages.append(second)
        self.fuzzyMatch(self.testMessages[0],  self.testMessages[1])

    def fuzzyMatch(self, first, second):
        "try to ignore bits randomly generated by our code"
        self.assertEqual(first.__class__, second.__class__)
        self.assertEqual(first.version, second.version)
        if isinstance(first, sip.Request):
            self.assertEqual(first.method, second.method)
            self.assertEqual(first.uri, second.uri)
        else:
            self.assertEqual(first.code, second.code)

        for header in first.headers.keys():
            if not second.headers.get(header):
                if not first.headers[header]:
                    #woops, it's empty, never mind
                    continue
                raise unittest.FailTest("%s not present in %s" % (header, second))
            if header in ('from', 'to', 'contact'):
                #strip tags
                if isinstance(first.headers[header][0], sip.URL):
                    firsturl = first.headers[header][0]
                else:
                    firsturl = sip.parseAddress(first.headers[header][0])[1]
                secondurl = sip.parseAddress(second.headers[header][0])[1]
                self.assertEqual(firsturl, secondurl)
            elif header == "via":
                firstvia = [sip.parseViaHeader(h)
                            for h in first.headers['via']]
                secondvia = [sip.parseViaHeader(h)
                            for h in second.headers['via']]
                #convert to strings for easy reading of output
                self.assertEqual([x.toString() for x in firstvia],
                                 [x.toString() for x in firstvia])
            elif header == "content-length":
                continue
            else:
                self.assertEqual([str(x) for x in first.headers[header]],
                                 [str(x) for x in second.headers[header]])
    def testCallTermination(self):
        self.sip.datagramReceived(exampleInvite, ('10.0.0.1', 5060))
        self.clock.advance(0)
        self.assertEquals(len(self.sent), 1)
        self.assertMsgEqual(self.sent[0][0], response200)
        self.sent = []

        self.sip.datagramReceived(ackRequest, ('10.0.0.1', 5060))
        self.assertEquals(len(self.sent), 0)
        self.sip.datagramReceived(byeRequest, ('10.0.0.1', 5060))
        self.assertEquals(len(self.sent), 1)
        self.assertMsgEqual(self.sent[0][0], byeResponse)

