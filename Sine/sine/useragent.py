# -*- test-case-name: sine.test -*-

from xshtoom.sdp import SDP
from xshtoom.rtp.protocol import RTPProtocol
from xshtoom.audio.converters import Codecker, PT_PCMU
from xshtoom.rtp.formats import PT_NTE
from xshtoom.audio.aufile import WavReader, GSMReader, WavWriter
from sine.sip import responseFromRequest, parseAddress, formatAddress
from sine.sip import Response, Request, URL, T1, T2, SIPError, Via, debug
from sine.sip import ClientTransaction, ServerTransaction, SIPLookupError
from sine.sip import ITransactionUser, SIPResolverMixin, ServerInviteTransaction
from sine.sip import ClientInviteTransaction, computeBranch
from twisted.internet import reactor, defer, task, stdio
from twisted.application.service import Service
from twisted.cred.error import UnauthorizedLogin
from twisted.python import log
from axiom import batch
from axiom.errors import NoSuchUser
import random, wave, md5
from zope.interface import Interface, implements
from epsilon import juice

class Hangup(Exception):
    """
    Raise this in ITransactionUser.receivedAudio or .receivedDTMF to
    end the call.
    """

class StartRecording(juice.Command):
    commandName = 'Start-Recording'
    arguments = [('cookie', juice.String()), ('filename', juice.String()), ("format", juice.String())]

class StopRecording(juice.Command):
    commandName = "Stop-Recording"
    arguments = [('cookie', juice.String())]
    response = []

class PlayFile(juice.Command):
    commandName = "Play-File"
    arguments = [('cookie', juice.String()), ("filename", juice.String()), ("format", juice.String(optional=True))]
    response = [("done", juice.Boolean())]

class StopPlaying(juice.Command):
    commandName = "Stop-Playing"
    arguments = [('cookie', juice.String())]

class CreateRTPSocket(juice.Command):
    commandName= "Create-RTPSocket"
    arguments = [("host", juice.String())]
    response = [('cookie', juice.String())]

class GetSDP(juice.Command):
    commandName = "Get-SDP"
    arguments = [('cookie', juice.String()), ("othersdp", juice.String())]
    response = [('sdp', juice.String())]

class RTPStop(juice.Command):
    commandName = "Stop"
    arguments = [('cookie', juice.String())]

class RTPStart(juice.Command):
    commandName = "Start"
    arguments = [('cookie', juice.String()), ("targethost", juice.String()), ("targetport", juice.Integer())]

class DTMF(juice.Command):
    commandName = "DTMF"
    arguments = [('cookie', juice.String()), ("key", juice.Integer())]

class LocalControlProtocol(juice.Juice):
    #runs in main process
    def __init__(self, *args, **kwargs):
        juice.Juice.__init__(self, *args, **kwargs)
        self.dialogs = {}
        self.cookies = {}
    def command_DTMF(self, cookie, key):
        dialog = self.dialogs[cookie]
        dialog.callController.receivedDTMF(dialog, key)
        return {}

    command_DTMF.command = DTMF

    def createRTPSocket(self, dialog, host):
        d = CreateRTPSocket(host=str(host)).do(self)
        def remember(response):
            cookie = response['cookie']
            self.dialogs[cookie] = dialog
            self.cookies[dialog] = cookie
            return cookie
        return d.addCallback(remember)

    def getSDP(self, dialog, othersdp):
        if othersdp:
            othersdp = othersdp.show()
        else:
            othersdp = ""
        return GetSDP(cookie=self.cookies[dialog], othersdp=othersdp).do(self).addCallback(lambda r: SDP(r["sdp"]))

class MediaServerControlProtocol(batch.JuiceChild):
    #runs in RTP subprocess
    file = None
    def __init__(self, _):
        juice.Juice.__init__(self, False)
        self.codec = Codecker(PT_PCMU)
        self.currentRecordings = {}
        self.currentPlayouts = {}
        self.cookies = 0

    def dropCall(self, cookie):
        pass

    def incomingRTP(self, cookie, packet):
        rtp, fObj = self.currentRecordings[cookie]
        if packet.header.ct is PT_NTE:
            data = packet.data
            key = ord(data[0])
            start = (ord(data[1]) & 128) and True or False
            if start:
                DTMF(cookie=cookie, key=key).do(self)
            else:
                #print "stop inbound dtmf", key
                return
        else:
            if fObj is not None:
                fObj.write(self.codec.decode(packet))

    def command_START_RECORDING(self, cookie, filename, format="raw"):
        rtp, currentFile = self.currentRecordings[cookie]
        formats = {"wav": WavWriter,
                   "raw": (lambda f: f)}
        if format not in formats:
            raise ValueError("no support for writing format %r" % (format,))

        if currentFile is not None:
            log.msg("Uh oh we were already recording in %s" % (currentFile))
            currentFile.close()
        log.msg("FORMAT IS! %s" % (formats[format],))
        self.currentRecordings[cookie] = (rtp, formats[format](open(filename, 'wb')))
        return {}
    command_START_RECORDING.command = StartRecording

    def command_STOP_RECORDING(self, cookie):
        #XXX what should this return
        if cookie in self.currentRecordings:
            rtp, f = self.currentRecordings[cookie]
            self.currentRecordings[cookie] = (rtp, None)
            if f:
                f.close()
        return {}

    command_STOP_RECORDING.command = StopRecording

    def command_PLAY_FILE(self, cookie, filename, format="raw"):
        """
        Play a shtoom-format sound file. (Raw unsigned linear, 16 bit
        8000Hz audio. sox options: -u -w -r 8000)
        """
        rtp, _ = self.currentRecordings[cookie]
        formats = {"wav": (WavReader, 160),
                   "raw": ((lambda f: f), 320),
                   "gsm": (GSMReader, 320)}
        if format not in formats:
            raise ValueError("no support for format %r" % (format,))
        codec, samplesize = formats[format]
        f = codec(open(filename))
        d = defer.Deferred()
        def playSample():
            data = f.read(samplesize)
            if data == '':
                self.stopPlaying(cookie, True)
            else:
                sample = self.codec.handle_audio(data)
                rtp.handle_media_sample(sample)
        if cookie in self.currentPlayouts:
            self.stopPlaying(cookie, False)
        LC = task.LoopingCall(playSample)
        LC.start(0.020)
        self.currentPlayouts[cookie] = LC, d
        return d

    command_PLAY_FILE.command = PlayFile

    def command_CREATE_RTPSOCKET(self, host):
        c = self.makeCookie()
        rtp = RTPProtocol(self, c)
        self.currentRecordings[c] = (rtp, None)
        rtp.createRTPSocket(host, False)
        return {"cookie": c}
    command_CREATE_RTPSOCKET.command = CreateRTPSocket

    def command_GET_SDP(self, cookie, othersdp=None):
        rtp, _ = self.currentRecordings[cookie]
        if othersdp:
            sdptxt = SDP(othersdp)
        else:
            sdptxt = None
        return {"sdp": rtp.getSDP(sdptxt).show()}
    command_GET_SDP.command = GetSDP

    def command_STOP(self, cookie):
        rtp, _ = self.currentRecordings[cookie]
        self.stopPlaying(cookie, False)
        self.command_STOP_RECORDING(cookie)
        del self.currentRecordings[cookie]
        rtp.stopSendingAndReceiving()
        rtp.timeouterLoop.stop()
        return {}
    command_STOP.command = RTPStop

    def command_START(self, cookie, targethost, targetport):
        rtp, _ = self.currentRecordings[cookie]
        rtp.start((targethost, targetport))
        return {}
    command_START.command = RTPStart

    def command_STOP_PLAYING(self, cookie):
        self.stopPlaying(cookie, False)
        return {}
    command_STOP_PLAYING.command = StopPlaying

    def stopPlaying(self, cookie, finishedPlaying):
        if cookie not in self.currentPlayouts:
            return
        LC, d = self.currentPlayouts[cookie]
        if LC:
            LC.stop()
            LC = None
            d.callback({"done": finishedPlaying})
            del self.currentPlayouts[cookie]


    def makeCookie(self):
        self.cookies += 1
        return "cookie%s" % (self.cookies,)

class MediaServer(Service):
    def startService(self):
        j = MediaServerControlProtocol(False)
        stdio.StandardIO(j)

class Dialog:
    """
    I represent the state of a SIP call, and am responsible for
    providing appropriate information for generating requests or
    responses in that call.

    Note that RFC 3261 distinguishes between dialogs and sessions,
    because under certain circumstances you can have multiple dialogs
    in a single session, for instance if the request forks and
    receives multiple 2xx responses. The right thing to do in that
    situation isn't clear, so I don't deal with that specially.
    """

    callController = None

    def forServer(cls, tu, contactURI, msg):
        """
        Create a dialog from a received INVITE.

        tu: the transaction user handling this dialog.
        contactURI: the contact for the other party.
        msg: the initial INVITE that establishes this dialog.
        """
        #RFC 3261 12.1.1
        self = cls(tu, contactURI)
        self.msg = msg
        toAddress, fromAddress = self._finishInit()
        self.localAddress = toAddress
        self.remoteAddress = fromAddress
        self.localAddress[2]['tag'] = self.genTag()
        self.direction = "server"
        self.routeSet = [parseAddress(route) for route in self.msg.headers.get('record-route', [])]
        self.clientState = "confirmed"
        def gotRTP(rtp):
            self.rtp = rtp
            return self.rtp.createRTPSocket(self, contactURI.host)
        def gotCookie(c):
            self.cookie = c
            return self
        return self.tu.mediaController.getProcess().addCallback(gotRTP).addCallback(gotCookie)

    forServer = classmethod(forServer)

    def forClient(cls, tu, contactURI, targetURI, controller, noSDP=False, fromName=""):
        """
        Create a dialog with a remote party by sending an INVITE.

        tu: the transaction user handling this dialog.
        contactURI: the _local_ contact URI (port and host media will be received on)
        targetURI: URI of the remote party.
        controller: an ICallController instance that will handle media for this call.
        """

        #XXX Need to distinguish between contact and "logical" address
        #Contact usually includes the IP this element is actually listening on,
        #rather than some address that may proxy to here
        #this code assumes that they are identical
        #and specifically, that you can RTP-listen on contactURI.host

        # RFC 3261 12.1.2

        self = cls(tu, contactURI)
        self.callController = controller
        self.direction = "client"
        def startProcess(rtp):
            self.rtp = rtp
        return self.tu.mediaController.getProcess().addCallback(startProcess).addCallback(lambda _: self._generateInvite(contactURI, fromName, targetURI, noSDP))

    forClient = classmethod(forClient)
    routeSet = None

    def __init__(self, tu, contactURI):
        self.tu = tu
        self.contactURI = contactURI
        self.localCSeq = random.randint(1E4,1E5)
        self.LC = None
        #UAC bits
        self.clientState = "early"
        self.sessionDescription = None
        self.ackTimer = [None, 0]
        self.acked = False
        self.ended = False

    def _finishInit(self):
        self.callID = self.msg.headers['call-id'][0]
        toAddress = parseAddress(self.msg.headers['to'][0])
        fromAddress = parseAddress(self.msg.headers['from'][0])
        return toAddress, fromAddress

    def ackTimerRetry(self, msg):
        timer, tries = self.ackTimer
        if tries > 10:
            #more than 64**T1 seconds since we've heard from the other end
            #so say bye and give up
            self.sendBye()
            return
        if tries > 0:
            self.tu.transport.sendResponse(msg)
        self.ackTimer = (reactor.callLater(min((2**tries)*T1, T2),
                                           self.ackTimerRetry, msg),
                         tries+1)

    def getDialogID(self):
        return (self.callID,
                self.localAddress[2].get('tag',''),
                self.remoteAddress[2].get('tag',''))

    def genTag(self):
        tag = ('%04x'%(random.randint(0, 2**10)))[:4]
        tag += ('%04x'%(random.randint(0, 2**10)))[:4]
        return tag

    def responseFromRequest(self, code, msg, body, bodyType="application/sdp"):

        response = Response(code)
        for name in ("via", "call-id", "record-route", "cseq"):
           response.headers[name] = msg.headers.get(name, [])[:]
        if self.direction == 'server':
            response.addHeader('to', formatAddress(self.localAddress))
            response.addHeader('from', formatAddress(self.remoteAddress))
        elif self.direction == 'client':
            response.addHeader('from', formatAddress(self.localAddress))
            response.addHeader('to', formatAddress(self.remoteAddress))
        response.addHeader('user-agent', "Divmod Sine")
        if msg.method == 'INVITE' and code == 200:
            response.addHeader('contact', formatAddress(self.contactURI))
            response.addHeader('content-length', len(body))
            response.addHeader('content-type', bodyType)
            response.bodyDataReceived(body)
        else:
            response.addHeader('content-length', 0)
        response.creationFinished()
        return response

    def _generateInvite(self, contacturi, fromName, uri, noSDP):
        #RFC 3261 8.1.1
        #RFC 3261 13.2.1
        invite = Request("INVITE", uri)
        invite.addHeader("to", formatAddress(uri))
        invite.addHeader("from", formatAddress((fromName, URL(contacturi.host, contacturi.username), {'tag': self.genTag()})))
        invite.addHeader("call-id",
                         "%s@%s" % (md5.md5(str(random.random())).hexdigest(),
                                    contacturi.host))
        invite.addHeader("cseq", "%s INVITE" % self.localCSeq)
        invite.addHeader("user-agent", "Divmod Sine")
        if noSDP:
            invite.headers["content-length"] =  ["0"]
        else:
            invite.addHeader("content-type", "application/sdp")
        #XXX maybe rip off IP discovered in SDP phase?
        invite.addHeader("contact", formatAddress(contacturi))
        def fillSDP(_):
            def consultSDP(sdpobj):
                sdp = sdpobj.show()
                self.sessionDescription = sdp
                invite.body = sdp
                invite.headers['content-length'] = [str(len(sdp))]
                invite.creationFinished()
            return defer.maybeDeferred(self.rtp.getSDP, self, None).addCallback(consultSDP)

        def finish(_):
            self.msg = invite
            toAddress,fromAddress = self._finishInit()
            self.localAddress = fromAddress
            self.remoteAddress = toAddress
            return self

        d = self.rtp.createRTPSocket(self, contacturi.host)
        def gotCookie(c):
            self.cookie = c
        d.addCallback(gotCookie)
        if noSDP:
            invite.creationFinished()
            return d.addCallback(finish)
        else:
            return d.addCallback(fillSDP).addCallback(finish)

    def reinvite(self, newContact, newSDP):
        """
        Send a new INVITE to the remote address for this dialog.
        @param newContact: a new local address for this dialog. if None, the existing one is used.
        @param newSDP: An L{xshtoom.sdp.SDP} instance describing the new session.
        """
        newSDP = upgradeSDP(self.sessionDescription, newSDP)
        msg = self.generateRequest('INVITE')
        if newContact:
            msg.headers['contact'] = [formatAddress(newContact)]
        msg.body = newSDP.show()
        msg.headers['content-length'] = [str(len(newSDP.show()))]
        msg.addHeader("content-type", "application/sdp")

        self.reinviteMsg = msg
        self.reinviteSDP = newSDP
        for ct in self.tu.cts:
            if (isinstance(ct, ClientInviteTransaction) and
                ct.mode not in ('completed', 'terminated')):
                self.clientState = "reinvite-waiting"
                return
        for st in self.tu.transport.serverTransactions.values():
            if (st.tu == self.tu and
                st.mode not in ('confirmed', 'terminated')):
                self.clientState = "reinvite-waiting"
                #XXX gotta do something to trigger the reinvite once the
                #offending ST finishes
                return
        return self._sendReinvite(msg)

    def _sendReinvite(self, msg):
        if self.clientState == "byeSent":
            #it's over, never mind
            return
        dest = self._findDest(msg)
        ct = ClientInviteTransaction(self.tu.transport, self.tu, msg, (dest.host, dest.port))
        self.clientState = "reinviteSent"
        self.tu.cts[ct] = self


    def generateRequest(self, method):
        #RFC 3261 12.2.1.1
        r = Request(method, self.remoteAddress[1])

        if self.routeSet:
            r.headers['route'] = [formatAddress(route) for route in self.routeSet]
            if 'lr' not in self.routeSet[0][1].other:
                r.headers['route'].append(formatAddress(("", r.uri, {})))
                r.uri = parseAddress(r.headers['route'].pop())[1]

        r.addHeader('to', formatAddress(self.remoteAddress))
        r.addHeader('from', formatAddress(self.localAddress))
        r.addHeader('cseq', "%s %s" % (self.localCSeq, method))
        self.localCSeq += 1
        r.addHeader('call-id', self.msg.headers['call-id'][0])
        r.addHeader('contact', formatAddress(self.contactURI))
        r.addHeader('content-length', 0)
        return r


    def _findDest(self, msg):
        rs = msg.headers.get('route', None)
        if rs:
            dest = parseAddress(rs[0])[1]
        else:
            dest = self.remoteAddress[1]
        return dest


    def sendBye(self):
        "Send a BYE and stop media."
        msg = self.generateRequest('BYE')
        self.clientState = "byeSent"
        dest = self._findDest(msg)
        ct = ClientTransaction(self.tu.transport, self.tu, msg, (dest.host, dest.port))
        self.tu.cts[ct] = self #is this bad?
        self.end()

    def sendAck(self, body=""):
        msg = self.generateRequest('ACK')
        msg.headers['cseq'] = ["%s ACK" % self.msg.headers['cseq'][0].split(' ')[0]]
        msg.body = body
        msg.headers['content-length'] = [str( len(body))]
        if body:
            msg.addHeader("content-type", "application/sdp")
        dest = self._findDest(msg)
        msg.headers.setdefault('via', []).insert(0, Via(self.tu.transport.host, self.tu.transport.port,
                                                        rport=True,
                                                        branch=computeBranch(msg)).toString())
        self.tu.transport.sendRequest(msg, (dest.host, dest.port))


    def playFile(self, filename, codec=None):
        def check(r):
            if not r['done']:
                return defer.fail(RuntimeError("cancelled"))

        if codec is None:
            return PlayFile(cookie=self.cookie, filename=str(filename)).do(self.rtp).addCallback(check)
        else:
            return PlayFile(cookie=self.cookie, filename=str(filename), format=codec).do(self.rtp).addCallback(check)

    def stopPlaying(self):
        return StopPlaying(cookie=self.cookie).do(self.rtp)

    def end(self):
        if self.ended:
            return
        self.ended = True
        RTPStop(cookie=self.cookie).do(self.rtp)
        self.callController.callEnded(self)

    def startRecording(self, filename, format):
        return StartRecording(
            cookie=self.cookie,
            format=format,
            filename=str(filename)).do(self.rtp)

    def endRecording(self):
        return StopRecording(
            cookie=self.cookie).do(self.rtp)

    def startAudio(self, sdp):
        md = sdp.getMediaDescription('audio')
        addr = md.ipaddr or sdp.ipaddr
        def go(ipaddr):
            remoteAddr = (ipaddr, md.port)
            return RTPStart(cookie=self.cookie, targethost=remoteAddr[0], targetport=remoteAddr[1]).do(self.rtp)
        reactor.resolve(addr).addCallback(go)

def upgradeSDP(currentSession, newSDP):
    "Read the media description from the new SDP and update the current session by removing the current media."

    sdp = SDP(currentSession)
    if newSDP.ipaddr:
        c = (newSDP.nettype, newSDP.addrfamily, newSDP.ipaddr)
        sdp.nettype, sdp.addrfamily, sdp.ipaddr = c
    sdp.mediaDescriptions =  newSDP.mediaDescriptions
    sdp._o_version = str(int(sdp._o_version) + 1)
    return sdp

class ICallControllerFactory(Interface):
    def buildCallController(self, dialog):
        "Return an ICallController"

class ICallController(Interface):
    """
    The order of calls received is:
    - acceptCall
    - callBegan
    - zero or more receiveAudio and/or receiveDTMF (if zero, there is probably a network problem)
    - callEnded
    """

    def acceptCall(dialog):
        """
        Decide if this call will be accepted or not: raise a
        SIPError(code) if the call should be rejected, where 'code' is
        the SIP error code desired.
        """

    def callBegan(dialog):
        """
        Called after the INVITE response has been ACKed and audio started.
        """

    def callFailed(dialog, message):
        """
        Called when an incoming call is canceled or an outgoing call
        receives a failure response.
        """

    def callEnded(dialog):
        """
        Called after BYE received.
        """

    def receivedAudio(dialog, packet):
        """
        Called with a chunk of audio data, decode into shtoom's
        preferred format (signed linear 16bit 8000Hz).
        """

    def receivedDTMF(dialog, key):
        """
        Called with the numeric value of the pressed key. * and # are
        10 and 11.
        """

def _matchToDialog(msg, origin, dest, dialogs):
    dialog= dialogs.get(
        (msg.headers['call-id'][0],
         parseAddress(msg.headers[origin][0])[2].get('tag',''),
         parseAddress(msg.headers[dest][0])[2].get('tag','')),
        None)
    return dialog

def matchResponseToDialog(msg, dialogs):
    return _matchToDialog(msg, 'from', 'to', dialogs)

def matchRequestToDialog(msg, dialogs):
    return _matchToDialog(msg, 'to', 'from', dialogs)



class UserAgent(SIPResolverMixin):
    """
    I listen on a sine.sip.SIPTransport and create or accept SIP calls
    """
    implements(ITransactionUser)

    def server(cls, voicesystem, localHost, mediaController, dialogs=None):
        """
        I listen for incoming SIP calls and connect them to
        ICallController instances, looked up via an IVoiceSystem.
        """
        self = cls(localHost, mediaController, dialogs)
        self.voicesystem = voicesystem
        return self

    server = classmethod(server)

    def client(cls, controller, localpart, localHost, mediaController, dialogs=None):
        """
        I create calls to SIP URIs and connect them to my ICallController instance.
        """
        self = cls(localHost, mediaController, dialogs)
        self.controller = controller
        self.user = localpart

        return self

    client = classmethod(client)

    def __init__(self, localHost, mc, dialogs):
        self.mediaController = mc
        if dialogs is None:
            self.dialogs = {}
        else:
            self.dialogs = dialogs
        self.cts = {}
        self.host = localHost
        self.shutdownDeferred = None

    def start(self, transport):
        self.transport = transport

    def stopTransactionUser(self, hard=False):
        for d in self.dialogs.values():
            if hard:
                d.end()
            else:
                d.sendBye()
        self.shutdownDeferred = defer.Deferred()
        return self.shutdownDeferred

    def maybeStartAudio(self, dialog, sdp):
        """
        Start audio on the dialog.  This method is designed to be
        overridden by user-agents that provide facilities like
        third-party call control.  See L{sine.tpcc} for details.
        """
        debug("START AUDIO (maybe)")
        dialog.startAudio(sdp)

    def requestReceived(self, msg, addr):
        #RFC 3261 12.2.2
        if msg.method == "INVITE":
            st = ServerInviteTransaction(self.transport, self, msg, addr)
        else:
            st = ServerTransaction(self.transport, self, msg, addr)
        #dialog checking
        dialog = matchRequestToDialog(msg, self.dialogs)

        #untagged requests must be checked against ongoing transactions
        # see 8.2.2.2


        if not dialog and parseAddress(msg.headers['to'][0])[2].get('tag',None):
            #uh oh, there was an expectation of a dialog
            #but we can't remember it (maybe we crashed?)
            st.messageReceivedFromTU(responseFromRequest(481, msg))
            return defer.succeed(st)
            #authentication
            #check for Require
        m = getattr(self, "process_" + msg.method, None)
        if not m:
            st.messageReceivedFromTU(responseFromRequest(405, msg))
            return defer.succeed(st)
        else:
            return defer.maybeDeferred(m, st, msg, addr, dialog).addCallback(
                lambda x: st)

    def process_INVITE(self, st, msg, addr, dialog):
        #RFC 3261 13.3.1
        if dialog:
            #it's a reinvite
            if msg.body:
                #new SDP ahoy
                sdp = SDP(msg.body)
            else:
                sdp = None
            d = defer.maybeDeferred(dialog.rtp.getSDP, dialog, sdp)
            def gotSDP(mysdp):
                if not mysdp.hasMediaDescriptions():
                    st.messageReceivedFromTU(responseFromRequest(488, msg))
                    return st
                dialog.sessionDescription = mysdp
                if dialog.clientState == "reinviteSent":
                    st.messageReceivedFromTU(dialog.responseFromRequest(491, msg))
                else:
                    if sdp:
                        self.maybeStartAudio(dialog, sdp)
                    dialog.msg = msg
                    dialog.reinviteMsg = True
                    dialog.remoteAddress = parseAddress(msg.headers['from'][0])
                    response = dialog.responseFromRequest(200, msg, mysdp.show())
                    st.messageReceivedFromTU(response)
                    dialog.ackTimerRetry(response)

                return st
            return d.addCallback(gotSDP)
        #otherwise, time to start a new dialog

        d = Dialog.forServer(self, URL(self.host,
                             parseAddress(msg.headers['to'][0])[1].username),
                             msg)


        def lookupElement(dialog):

            avatar = self.voicesystem.localElementByName(parseAddress(msg.headers['to'][0])[1].username)

            dialog.callController = avatar.buildCallController(dialog)
            if msg.body:
                sdp = SDP(msg.body)
            else:
                sdp = None
            d = defer.maybeDeferred(dialog.rtp.getSDP, dialog, sdp)
            def gotSDP(mysdp):
                dialog.sessionDescription = mysdp
                if not mysdp.hasMediaDescriptions():
                    st.messageReceivedFromTU(responseFromRequest(406, msg))
                    return st
                if sdp:
                    self.maybeStartAudio(dialog, sdp)
                self.dialogs[dialog.getDialogID()] = dialog
                response = dialog.responseFromRequest(200, msg, mysdp.show())
                st.messageReceivedFromTU(response)

                dialog.ackTimerRetry(response)
            d.addCallback(gotSDP)
            return d

        def failedLookup(err):
            err.trap(NoSuchUser, UnauthorizedLogin)
            raise SIPLookupError(604)

        return d.addCallback(lookupElement).addErrback(failedLookup)

    def process_ACK(self, st, msg, addr, dialog):
        #woooo it is an ack for a 200, it is call setup time
        timer = dialog.ackTimer[0]
        if timer.active():
            timer.cancel()
        if not getattr(dialog, 'reinviteMsg', None):
            #only do this for the initial INVITE
            if not dialog.acked:
                dialog.callController.callBegan(dialog)
                dialog.acked = True
        else: debug("reinvite ACKed")
        if msg.body:
            #must've gotten an invite with no SDP
            #so this is the answer
            sdp = SDP(msg.body)
            self.maybeStartAudio(dialog, sdp)


    def process_BYE(self, st, msg, addr, dialog):
        if not dialog:
            raise SIPError(481)
        #stop RTP stuff
        dialog.end()
        response = dialog.responseFromRequest(200, msg, None)
        st.messageReceivedFromTU(response)

        del self.dialogs[dialog.getDialogID()]


    def responseReceived(self, response, ct=None):

        #OK this function is a bit hairy because I don't want to track
        #any call state in this class and responses to various things
        #need to be handled differently. The main event is 2xx
        #responses to the INVITE -- that changes the early dialog
        #(created when the INVITE was sent) to an confirmed dialog.
        #Error responses result in dialog teardown, as do responses to BYEs.

        #RFC 3261 12.2.1.2
        dialog = self.cts.get(ct, None)
        if dialog is None:
            dialog = matchResponseToDialog(response, self.dialogs)


        if 'INVITE' in response.headers['cseq'][0] and 200 <= response.code < 300:
            #possibly this line doesn't belong here? earlyResponseReceived
            #does it too but IIRC it can't come before sending the ack
            dialog.remoteAddress = parseAddress(response.headers['to'][0])
            self.acknowledgeInvite(dialog, response)

        if dialog.clientState == "early":
            self.earlyResponseReceived(dialog, response, ct)

        if dialog.clientState == "byeSent":
            self.byeResponseReceived(dialog, response, ct)
        elif dialog.clientState == "reinviteSent":
            self.reinviteResponseReceived(dialog, response, ct)


    def acknowledgeInvite(self, dialog, response):
        #RFC 3261, 13.2.2.4
        if dialog.sessionDescription:
            #the INVITE contained the offer, no body in the ACK
            dialog.sendAck()
        else:
            #the 200 contained the offer, answer in the ACK
            sdp = SDP(response.body)
            d = defer.maybeDeferred(dialog.rtp.getSDP, dialog, sdp)
            def gotSDP(mysdpobj):
                mysdp = mysdpobj.show()
                dialog.sendAck(mysdp)
                dialog.sessionDescription = mysdp
            d.addCallback(gotSDP)
            return d

    def reinviteResponseReceived(self, dialog, response, ct):
        if response.code == 491:
            if dialog.direction == "client":
                reactor.callLater(random.randint(210,400)/100.0,
                                  dialog._sendReinvite, dialog.reinviteMsg)
            else:
                reactor.callLater(random.randint(0, 200)/100.0,
                                  dialog._sendReinvite, dialog.reinviteMsg)
        elif 200 <= response.code < 300:
            dialog.clientState = "confirmed"
            dialog.msg = dialog.reinviteMsg
            dialog.contactURI = parseAddress(dialog.msg.headers['contact'][0])[1]
            dialog.sessionDescription = dialog.reinviteSDP
        else:
            dialog.clientState = "confirmed"

    def byeResponseReceived(self, dialog, response, ct):
        del self.cts[ct]
        del self.dialogs[dialog.getDialogID()]

    def earlyResponseReceived(self, dialog, response, ct):
        if 200 <= response.code < 300:
            #RFC 3261 12.1.2
            dialog.clientState = "confirmed"
            dialog.remoteAddress = parseAddress(response.headers['to'][0])
            dialog.routeSet = [parseAddress(route) for route in response.headers.get('record-route', [])[::-1]]
            self.dialogs[dialog.getDialogID()] = dialog
            sdp = SDP(response.body)
            self.maybeStartAudio(dialog, sdp)
            if self.controller:
                self.controller.callBegan(dialog)
        elif 300 <= response.code < 400:
            raise NotImplemented, "Dunno about redirects yet"
        elif 400 <= response.code < 700:
            if dialog.getDialogID() in self.dialogs:
                del self.dialogs[dialog.getDialogID()]
            del self.cts[ct]
            self.controller.callFailed(dialog, response)

    def call(self, uri):
        """
        Call the specified URI and notify our controller when it is set up.
        """
        return self._doCall(uri)

    def _doCall(self, uri, noSDP=False,fromName=""):
        dlgD = Dialog.forClient(self, URL(self.host, self.user), uri, self.controller, noSDP, fromName)
        def _cb(dlg):
            targetsD = self._lookupURI(uri)
            def _send(targets):
                #'targets' is a list of (host, port) obtained from SRV lookup
                #ideally, if there's a 503 response to this message, we can
                #resend through another target.
                #For now we'll just send to the first and hope for the best.

                ct = ClientInviteTransaction(self.transport, self, dlg.msg, targets[0])
                self.cts[ct] = dlg
            targetsD.addCallback(_send)
            return dlg
        return dlgD.addCallback(_cb)


    def clientTransactionTerminated(self, ct):
        if ct not in self.cts:
            return
        dialog = self.cts.pop(ct)
        if dialog.clientState != "confirmed":
            self.responseReceived(ct.response)
        if self.shutdownDeferred and not self.cts:
            self.shutdownDeferred.callback(True)

    def dropCall(self, dialog):
        "For shtoom compatibility."
        dialog.sendBye()



class SimpleCallRecipient:
    """
    An example SIP application: upon receipt of a call, a greeting is
    played, then audio is recorded until hangup or # is pressed.
    """

    implements(ICallController)
    file = None

    def acceptCall(self, dialog):
        pass

    def callBegan(self, dialog):
        import os
        fn = os.path.join(os.path.split(__file__)[0], 'test_audio.raw')
        dialog.playFile(fn).addCallback(lambda _: self.beginRecording())

    def receivedDTMF(self, key):
        if key == 11:
            self.endRecording()

    def callEnded(self, dialog):
        self.endRecording()

    def beginRecording(self):
        self.file = wave.open('recording.wav', 'wb')
        self.file.setparams((1,2,8000,0,'NONE','NONE'))

    def receivedAudio(self, dialog, bytes):
        if self.file:
            self.file.writeframes(bytes)

    def endRecording(self):
        if self.file:
            self.file.close()
