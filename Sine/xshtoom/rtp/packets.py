# Copyright (C) 2004 Anthony Baxter

import struct

# This class supports extension headers, but only one per packet.
class RTPPacket:
    """ Contains RTP data. """
    class Header:
        def __init__(self, ssrc, pt, ct, seq, ts, marker=0,
                     xhdrtype=None, xhdrdata=''):
            """
            If xhdrtype is not None then it is required to be an
            int >= 0 and < 2**16 and xhdrdata is required to be
            a string whose length is a multiple of 4.
            """
            assert isinstance(ts, (int, long,)), "ts: %s :: %s" % (ts, type(ts))
            assert isinstance(ssrc, (int, long,))
            assert xhdrtype is None or isinstance(xhdrtype, int) \
                    and xhdrtype >= 0 and xhdrtype < 2**16
            # Sorry, RFC standard specifies that len is in 4-byte words,
            # and I'm not going to do the padding and unpadding for you.
            assert xhdrtype is None or (isinstance(xhdrdata, str) and \
                    len(xhdrdata) % 4 == 0), \
                    "xhdrtype: %s, len(xhdrdata): %s, xhdrdata: %s" % (
                    xhdrtype, len(xhdrdata), `xhdrdata`,)

            (self.ssrc, self.pt, self.ct, self.seq, self.ts,
                 self.marker, self.xhdrtype, self.xhdrdata) = (
             ssrc,      pt,      ct,      seq,      ts,
                 marker,      xhdrtype,      xhdrdata)

        def netbytes(self):
            "Return network-formatted header."
            assert isinstance(self.pt, int) and self.pt >= 0 and \
                self.pt < 2**8, \
                "pt is required to be a simple byte, suitable " + \
                "for stuffing into an RTP packet and sending. pt: %s" % self.pt
            if self.xhdrtype is not None:
                firstbyte = 0x90
                xhdrnetbytes = struct.pack('!HH', self.xhdrtype,
                                    len(self.xhdrdata)/4) + self.xhdrdata
            else:
                firstbyte = 0x80
                xhdrnetbytes = ''
            return struct.pack('!BBHII', firstbyte,
                                        self.pt | self.marker << 7,
                                        self.seq % 2**16,
                                        self.ts, self.ssrc) + xhdrnetbytes

    def __init__(self, ssrc, seq, ts, data, pt=None, ct=None, marker=0,
                 authtag='', xhdrtype=None, xhdrdata=''):
        assert pt is None or isinstance(pt, int) and pt >= 0 and pt < 2**8, \
            "pt is required to be a simple byte, suitable for stuffing " + \
            "into an RTP packet and sending. pt: %s" % pt
        self.header = RTPPacket.Header(ssrc, pt, ct, seq, ts, marker,
                                       xhdrtype, xhdrdata)
        self.data = data
        # please leave this alone even if it appears unused --
        # it is required for SRTP
        self.authtag = authtag

    def __repr__(self):
        if self.header.ct is not None:
            ptrepr = "%r" % (self.header.ct,)
        else:
            ptrepr = "pt %s" % (self.header.pt,)

        if self.header.xhdrtype is not None:
            return "<%s #%d (%s) %s [%s] at %x>"%(self.__class__.__name__,
                                                  self.header.seq,
                                                  self.header.xhdrtype,
                                                  ptrepr,
                                                  repr(self.header.xhdrdata),
                                                  id(self))
        else:
            return "<%s #%d %s at %x>"%(self.__class__.__name__,
                                        self.header.seq, ptrepr, id(self))

    def netbytes(self):
        "Return network-formatted packet."
        return self.header.netbytes() + self.data + self.authtag

def parse_rtppacket(bytes, authtaglen=0):
    # Most variables are named for the fields in the RTP RFC.
    hdrpieces = struct.unpack('!BBHII', bytes[:12])

    # XXX we ignore v (version)
    # Padding?
    p = (hdrpieces[0] & 32) and 1 or 0
    # Extension header present?
    x = (hdrpieces[0] & 16) and 1 or 0
    # CSRC Count
    cc = hdrpieces[0] & 15
    # Marker bit
    marker = hdrpieces[1] & 128
    # Payload type
    pt = hdrpieces[1] & 127
    # Sequence number
    seq = hdrpieces[2]
    # Timestamp
    ts = hdrpieces[3]
    ssrc = hdrpieces[4]
    headerlen = 12 + cc * 4
    # XXX throwing away csrc info for now
    bytes = bytes[headerlen:]
    if x:
        # Only one extension header
        (xhdrtype, xhdrlen,) = struct.unpack('!HH', bytes[:4])
        xhdrdata = bytes[4:4+xhdrlen*4]
        bytes = bytes[xhdrlen*4 + 4:]
    else:
        xhdrtype, xhdrdata = None, None
    if authtaglen:
        authtag = bytes[-authtaglen:]
        bytes = bytes[:-authtaglen]
    else:
        authtag = ''
    if p:
        # padding
        padlen = struct.unpack('!B', bytes[-1])[0]
        if padlen:
            bytes = bytes[:-padlen]
    return RTPPacket(ssrc, seq, ts, bytes, marker=marker, pt=pt,
                     authtag=authtag, xhdrtype=xhdrtype, xhdrdata=xhdrdata)


class NTE:
    "An object representing an RTP NTE (rfc2833)"
    # XXX at some point, this should be hooked into the RTPPacketFactory.
    def __init__(self, key, startTS):
        self.startTS = startTS
        self.ending = False
        self.counter = 3
        self.key = key
        if key >= '0' and key <= '9':
            self._payKey = chr(int(key))
        elif key == '*':
            self._payKey = chr(10)
        elif key == '#':
            self._payKey = chr(11)
        elif key >= 'A' and key <= 'D':
            # A - D are 12-15
            self._payKey = chr(ord(key)-53)
        elif key == 'flash':
            self._payKey = chr(16)
        else:
            raise ValueError, "%s is not a valid NTE"%(key)

    def getKey(self):
        return self.key

    def end(self):
        self.ending = True
        self.counter = 1

    def getPayload(self, ts):
        if self.counter > 0:
            if self.ending:
                end = 128
            else:
                end = 0
            payload = self._payKey + chr(10|end) + \
                                struct.pack('!H', ts - self.startTS)
            self.counter -= 1
            return payload
        else:
            return None

    def isDone(self):
        if self.ending and self.counter < 1:
            return True
        else:
            return False

    def __repr__(self):
        return '<NTE %s%s>'%(self.key, self.ending and ' (ending)' or '')
