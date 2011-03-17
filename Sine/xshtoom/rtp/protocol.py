# Copyright (C) 2004-2005 Anthony Baxter

# $Id: rtp.py,v 1.40 2004/03/07 14:41:39 anthony Exp $
#

import random, os, md5, socket
from time import time

from twisted.internet import reactor, defer
from twisted.internet.protocol import DatagramProtocol
from twisted.python import log
from twisted.internet.task import LoopingCall
from xshtoom.rtp.formats import SDPGenerator, PT_CN, PT_xCN, PT_NTE, PT_PCMU
from xshtoom.rtp.packets import RTPPacket, parse_rtppacket

TWO_TO_THE_16TH = 2L<<16
TWO_TO_THE_32ND = 2L<<32
TWO_TO_THE_48TH = 2L<<48

from xshtoom.rtp.packets import NTE

class RTPProtocol(DatagramProtocol):
    """Implementation of the RTP protocol.

    Also manages a RTCP instance.
    """

    _stunAttempts = 0

    _cbDone = None

    dest = None

    Done = False
    def __init__(self, app, cookie, *args, **kwargs):
        self.app = app
        self.cookie = cookie
        self._pendingDTMF = []
        #DatagramProtocol.__init__(self, *args, **kwargs)
        self.ptdict = {}
        self.seq = self.genRandom(bits=16)
        self.ts = self.genInitTS()
        self.ssrc = self.genSSRC()
        self._silent = None
        # only for debugging -- the way to prevent the sending of RTP packets
        # onto the Net is to reopen the audio device with a None (default)
        # media sample handler instead of this RTP object as the media sample handler.
        self.sending = False

    def getSDP(self, othersdp=None):
        sdp = SDPGenerator().getSDP(self)
        if othersdp:
            sdp.intersect(othersdp)
        self.setSDP(sdp)
        return sdp

    def setSDP(self, sdp):
        "This is the canonical SDP for the call"
        #XXXSHTOOM
        #self.app.selectDefaultFormat(self.cookie, sdp)
        rtpmap = sdp.getMediaDescription('audio').rtpmap
        self.ptdict = {}
        for pt, (text, marker) in rtpmap.items():
            self.ptdict[pt] = marker
            self.ptdict[marker] = pt
        if PT_PCMU not in self.ptdict:
            # Goddam Asterisk has no idea about content negotiation
            self.ptdict[0] = PT_PCMU
            self.ptdict[PT_PCMU] = 0


    def createRTPSocket(self, locIP, needSTUN=False):
        """ Start listening on UDP ports for RTP and RTCP.

            Returns a Deferred, which is triggered when the sockets are
            connected, and any STUN has been completed. The deferred
            callback will be passed (extIP, extPort). (The port is the RTP
            port.) We don't guarantee a working RTCP port, just RTP.
        """
        self.needSTUN=needSTUN
        d = defer.Deferred()
        self._socketCompleteDef = d
        self._socketCreationAttempt(locIP)
        self.lastreceivetime = time()
        self.rtptimeout = 60 # make this configurable?
        self._startTimeouter()
        return d

    def _socketCreationAttempt(self, locIP=None):
        from twisted.internet.error import CannotListenError
        from xshtoom.rtp import rtcp
        self.RTCP = rtcp.RTCPProtocol(self)

        # RTP port must be even, RTCP must be odd
        # We select a RTP port at random, and try to get a pair of ports
        # next to each other. What fun!
        # Note that it's kinda pointless when we're behind a NAT that
        # rewrites ports. We can at least send RTCP out in that case,
        # but there's no way we'll get any back.
        #rtpPort = self.app.getPref('force_rtp_port')
        rtpPort = None
        if not rtpPort:
            rtpPort = 11000 + random.randint(0, 9000)
        if (rtpPort % 2) == 1:
            rtpPort += 1
        while True:
            try:
                self.rtpListener = reactor.listenUDP(rtpPort, self)
            except CannotListenError:
                rtpPort += 2
                continue
            else:
                break
        rtcpPort = rtpPort + 1
        while True:
            try:
                self.rtcpListener = reactor.listenUDP(rtcpPort, self.RTCP)
            except CannotListenError:
                # Not quite right - if it fails, re-do the RTP listen
                self.rtpListener.stopListening()
                rtpPort = rtpPort + 2
                rtcpPort = rtpPort + 1
                continue
            else:
                break
        #self.rtpListener.stopReading()
        if self.needSTUN is False:
            # The pain can stop right here
            self._extRTPPort = rtpPort
            self._extIP = locIP
            d = self._socketCompleteDef
            del self._socketCompleteDef
            d.callback(self.cookie)
        else:
            # If the NAT is doing port translation as well, we will just
            # have to try STUN and hope that the RTP/RTCP ports are on
            # adjacent port numbers. Please, someone make the pain stop.
            self.natMapping()

    def _startTimeouter(self):
        def checkTimeout():
            if time() >  self.lastreceivetime + self.rtptimeout:
                self.app.dropCall(self.cookie)
                self.Done = True
        self.timeouterLoop = LoopingCall(checkTimeout)
        self.timeouterLoop.start(61)
    def getVisibleAddress(self):
        ''' returns the local IP address used for RTP (as visible from the
            outside world if STUN applies) as ( 'w.x.y.z', rtpPort)
        '''
        # XXX got an exception at runtime here as mapper hasn't finished yet and attribute _extIP doesn't exist.  I guess this means this should be triggered by the mapper instead of being a return value... --Zooko 2005-04-05
        return (self._extIP, self._extRTPPort)

    def natMapping(self):
        ''' Uses STUN to discover the external address for the RTP/RTCP
            ports. deferred is a Deferred to be triggered when STUN is
            complete.
        '''
        # See above comment about port translation.
        # We have to do STUN for both RTP and RTCP, and hope we get a sane
        # answer.
        from xshtoom.nat import getMapper
        d = getMapper()
        d.addCallback(self._cb_gotMapper)
        return d

    def unmapRTP(self):
        from xshtoom.nat import getMapper
        if self.needSTUN is False:
            return defer.succeed(None)
        # Currently removing an already-fired trigger doesn't hurt,
        # but this seems likely to change.
        try:
            reactor.removeSystemEventTrigger(self._shutdownHook)
        except:
            pass
        d = getMapper()
        d.addCallback(self._cb_unmap_gotMapper)
        return d

    def _cb_unmap_gotMapper(self, mapper):
        rtpDef = mapper.unmap(self.transport)
        rtcpDef = mapper.unmap(self.RTCP.transport)
        dl = defer.DeferredList([rtpDef, rtcpDef])
        return dl

    def _cb_gotMapper(self, mapper):
        rtpDef = mapper.map(self.transport)
        rtcpDef = mapper.map(self.RTCP.transport)
        self._shutdownHook =reactor.addSystemEventTrigger('before', 'shutdown',
                                                          self.unmapRTP)
        dl = defer.DeferredList([rtpDef, rtcpDef])
        dl.addCallback(self.setStunnedAddress).addErrback(log.err)

    def setStunnedAddress(self, results):
        ''' Handle results of the rtp/rtcp STUN. We have to check that
            the results have the same IP and usable port numbers
        '''
        log.msg("got NAT mapping back! %r"%(results), system='rtp')
        rtpres, rtcpres = results
        if rtpres[0] != defer.SUCCESS or rtcpres[0] != defer.SUCCESS:
            # barf out.
            log.msg("uh oh, stun failed %r"%(results), system='rtp')
        else:
            # a=RTCP might help for wacked out RTCP/RTP pairings
            # format is something like "a=RTCP:AUDIO 16387"
            # See RFC 3605
            code1, rtp = rtpres
            code2, rtcp = rtcpres
            if rtp[0] != rtcp[0]:
                print "stun gave different IPs for rtp and rtcp", results
            # We _should_ try and see if we have working rtp and rtcp, but
            # this seems almost impossible with most firewalls. So just try
            # to get a working rtp port (an even port number is required).
            elif False and ((rtp[1] % 2) != 0):
                log.msg("stun: unusable RTP/RTCP ports %r, retry #%d"%
                                            (results, self._stunAttempts),
                                            system='rtp')
                # XXX close connection, try again, tell user
                if self._stunAttempts > 8:
                    # XXX
                    print "Giving up. Made %d attempts to get a working port"%(
                        self._stunAttempts)
                self._stunAttempts += 1
                defer.maybeDeferred(
                            self.rtpListener.stopListening).addCallback(
                                    lambda x:self.rtcpListener.stopListening()
                                                          ).addCallback(
                                    lambda x:self._socketCreationAttempt()
                                                          )
                #self.rtpListener.stopListening()
                #self.rtcpListener.stopListening()
                #self._socketCreationAttempt()
            else:
                # phew. working NAT
                log.msg("stun: sane NAT for RTP/RTCP; rtp addr: %s" % (rtp,), system='rtp')
                self._extIP, self._extRTPPort = rtp
                self._stunAttempts = 0
                d = self._socketCompleteDef
                del self._socketCompleteDef
                d.callback(self.cookie)

    def connectionRefused(self):
        log.err("RTP got a connection refused, continuing anyway")
        #self.Done = True
        #self.app.dropCall(self.cookie)

    def whenDone(self, cbDone):
        self._cbDone = cbDone

    def stopSendingAndReceiving(self):
        self.Done = 1
        #XXXSHTOOM
        #d = self.unmapRTP()
        d = defer.succeed(None)
        d.addCallback(lambda x: self.rtpListener.stopListening())
        d.addCallback(lambda x: self.rtcpListener.stopListening())

    def _send_packet(self, pt, data, marker=0, xhdrtype=None, xhdrdata=''):
        packet = RTPPacket(self.ssrc, self.seq, self.ts, data, pt=pt,
                                    marker=marker,
                                    xhdrtype=xhdrtype, xhdrdata=xhdrdata)

        self.seq += 1
        # Note that seqno gets modulo 2^16 in RTPPacket, so it doesn't need
        # to be wrapped at 16 bits here.
        if self.seq >= TWO_TO_THE_48TH:
            self.seq = self.seq - TWO_TO_THE_48TH

        bytes = packet.netbytes()
        ## For RTCP sender report.
        #self.currentSentBytesTotal += len(bytes)
        #self.currentSentPacketsTotal += 1
        try:
            self.transport.write(bytes, self.dest)
        except Exception, le:
            pass

    def _send_cn_packet(self, logit=False):
        assert hasattr(self, 'dest'), "_send_cn_packet called before start %r" % (self,)
        # PT 13 is CN.
        if self.ptdict.has_key(PT_CN):
            cnpt = PT_CN.pt
        elif self.ptdict.has_key(PT_xCN):
            cnpt = PT_xCN.pt
        else:
            # We need to send SOMETHING!?!
            cnpt = 0

        if logit:
            log.msg("sending CN(%s) to seed firewall to %s:%d"%(cnpt,
                                    self.dest[0], self.dest[1]), system='rtp')

        self._send_packet(cnpt, chr(127))

    def start(self, dest, fp=None):
        self.dest = dest

        self.Done = False
        self.sending = True
        if hasattr(self.transport, 'connect'):
            self.transport.connect(*self.dest)

        # Now send a single CN packet to seed any firewalls that might
        # need an outbound packet to let the inbound back.
        self._send_cn_packet(logit=True)

    def datagramReceived(self, datagram, addr, t=time):
        self.lastreceivetime = time()
        packet = parse_rtppacket(datagram)

        try:
            packet.header.ct = self.ptdict[packet.header.pt]
        except KeyError:
            if packet.header.pt == 19:
                # Argh nonstandardness suckage
                packet.header.pt = 13
                packet.header.ct = self.ptdict[packet.header.pt]
            else:
                # XXX This could overflow the log.  Ideally we would have a
                # "previous message repeated N times" feature...  --Zooko 2004-10-18
                log.msg("received packet with unknown PT %s" % packet.header.pt)
                return # drop the packet on the floor

        packet.header.ct = self.ptdict[packet.header.pt]
        self.app.incomingRTP(self.cookie, packet)

    def genSSRC(self):
        # Python-ish hack at RFC1889, Appendix A.6
        m = md5.new()
        m.update(str(time()))
        m.update(str(id(self)))
        if hasattr(os, 'getuid'):
            m.update(str(os.getuid()))
            m.update(str(os.getgid()))
        m.update(str(socket.gethostname()))
        hex = m.hexdigest()
        nums = hex[:8], hex[8:16], hex[16:24], hex[24:]
        nums = [ long(x, 17) for x in nums ]
        ssrc = 0
        for n in nums: ssrc = ssrc ^ n
        ssrc = ssrc & (2**32 - 1)
        return ssrc

    def genInitTS(self):
        # Python-ish hack at RFC1889, Appendix A.6
        m = md5.new()
        m.update(str(self.genSSRC()))
        m.update(str(time()))
        hex = m.hexdigest()
        nums = hex[:8], hex[8:16], hex[16:24], hex[24:]
        nums = [ long(x, 16) for x in nums ]
        ts = 0
        for n in nums: ts = ts ^ n
        ts = ts & (2**32 - 1)
        return ts

    def startDTMF(self, digit):
        self._pendingDTMF.append(NTE(digit, self.ts))

    def stopDTMF(self, digit):
        if self._pendingDTMF[-1].getKey() == digit:
            self._pendingDTMF[-1].end()

    def genRandom(self, bits):
        """Generate up to 128 bits of randomness."""
        if os.path.exists("/dev/urandom"):
            hex = open('/dev/urandom').read(16).encode("hex")
        else:
            m = md5.new()
            m.update(str(time()))
            m.update(str(random.random()))
            m.update(str(id(self.dest)))
            hex = m.hexdigest()
        return int(hex[:bits//4],16)

    def handle_media_sample(self, sample):
        if time() >  self.lastreceivetime + self.rtptimeout:
            self.app.dropCall(self.cookie)
            self.Done = True
        if self.Done:
            if self._cbDone:
                self._cbDone()
            return

        incrTS = False

        # We need to keep track of whether we were in silence mode or not -
        # when we go from silent->talking, set the marker bit. Other end
        # can use this as an excuse to adjust playout buffer.
        if not self.sending:
            if not hasattr(self, 'warnedaboutthis'):
                log.msg(("%s.handle_media_sample() should only be called" +
                         " only when it is in sending mode.") % (self,))
                self.warnedaboutthis = True
            return

        marker = 0
        if sample is not None:
            if self._silent is not None:
                # Set the marker bit
                marker = 1
            self._silent = None
            if sample.ct not in self.ptdict:
                log.msg('trying to send packet with CT %r, which was not in the negotiated SDP'%(sample.ct,), system='rtp')
                return
            pt = self.ptdict[sample.ct]
            self._send_packet(pt, sample.data, marker=marker)
            incrTS = True

        else:
            if self._silent is None:
                self._silent = 0
            if (self._silent % 25) == 0:
                incrTS = True
                self._send_cn_packet()
            self._silent += 1


        # Now send any pending DTMF keystrokes
        if self._pendingDTMF:
            incrTS = True
            payload = self._pendingDTMF[0].getPayload(self.ts)
            if payload:
                ntept = self.ptdict.get(PT_NTE)
                if ntept is not None:
                    self._send_packet(pt=ntept, data=payload)
                else:
                    print "no PT_NTE? can't send packet", payload
                if self._pendingDTMF[0].isDone():
                    self._pendingDTMF = self._pendingDTMF[1:]

        if incrTS:
            self.ts += 160
            # Wrapping
            if self.ts >= TWO_TO_THE_32ND:
                self.ts = self.ts - TWO_TO_THE_32ND
