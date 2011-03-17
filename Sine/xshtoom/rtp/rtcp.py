# Copyright (C) 2004 Anthony Baxter

"""
RTCP packet encoding and decoding code. RTCP is a bit of a bitch - there's
so many things you can stuff in a packet.

Note that this code merely encodes and decodes the various formats - it does
not attempt to do anything useful with the data. Nor is there code here (yet)
to generate RR or SR packets from the RTP stack. Soon.
"""

from twisted.internet.protocol import DatagramProtocol
import time

RTCP_PT_SR = 200
RTCP_PT_RR = 201
RTCP_PT_SDES = 202
RTCP_PT_BYE = 203
RTCP_PT_APP = 204
rtcpPTdict = {RTCP_PT_SR: 'SR', RTCP_PT_RR: 'RR', RTCP_PT_SDES:'SDES', RTCP_PT_BYE:'BYE'}
for k,v in rtcpPTdict.items():
    rtcpPTdict[v] = k

RTCP_SDES_CNAME = 1
RTCP_SDES_NAME = 2
RTCP_SDES_EMAIL = 3
RTCP_SDES_PHONE = 4
RTCP_SDES_LOC = 5
RTCP_SDES_TOOL = 6
RTCP_SDES_NOTE = 7
RTCP_SDES_PRIV = 8

rtcpSDESdict = {RTCP_SDES_CNAME: 'CNAME',
                RTCP_SDES_NAME: 'NAME',
                RTCP_SDES_EMAIL: 'EMAIL',
                RTCP_SDES_PHONE: 'PHONE',
                RTCP_SDES_LOC: 'LOC',
                RTCP_SDES_TOOL: 'TOOL',
                RTCP_SDES_NOTE: 'NOTE',
                RTCP_SDES_PRIV: 'PRIV',
               }
for k,v in rtcpSDESdict.items():
    rtcpSDESdict[v] = k



import struct

def hexrepr(bytes):
    out = ''
    bytes = bytes + '\0'* ( 8 - len(bytes)%8 )
    for i in range(0,len(bytes), 8):
        out = out +  "    %02x%02x%02x%02x %02x%02x%02x%02x\n"%tuple(
                                                    [ord(bytes[i+x]) for x in range(8)])
    return out

class RTCPPacket:
    def __init__(self, pt, contents=None, ptcode=None):
        self._pt = pt
        if ptcode is None:
            self._ptcode = rtcpPTdict.get(pt)
        else:
            self._ptcode = ptcode
        self._body = ''
        if contents:
            self._contents = contents
        else:
            self._contents = None

    def getPT(self):
        return self._pt

    def getContents(self):
        return self._contents

    def decode(self, count, body):
        self._count = count
        self._body = body
        getattr(self, 'decode_%s'%self._pt)()

    def encode(self):
        out = getattr(self, 'encode_%s'%self._pt)()
        return out

    def _padIfNeeded(self, packet):
        if len(packet)%4:
            pad = '\0' * (4-(len(packet)%4))
            packet += pad
        return packet

    def _patchLengthHeader(self, packet):
        length = (len(packet)/4) - 1
        packet = packet[:2] + struct.pack('!H', length) + packet[4:]
        return packet

    def decode_SDES(self):
        for i in range(self._count):
            self._contents = []
            ssrc, = struct.unpack('!I', self._body[:4])
            self._contents.append((ssrc,[]))
            self._body = self._body[4:]
            while True:
                type, length = ord(self._body[0]), ord(self._body[1])
                off = length+2
                maybepadlen = 4-((length+2)%4)
                body, maybepad = self._body[2:off], self._body[off:off+maybepadlen]
                self._body = self._body[length+2:]
                self._contents[-1][1].append((rtcpSDESdict[type], body))
                if ord(maybepad[0]) == 0:
                    # end of list. eat the padding.
                    self._body = self._body[maybepadlen:]
                    break

    def encode_SDES(self):
        blocks = self._contents
        packet = struct.pack('!BBH',len(blocks)|128, self._ptcode, 0)
        for ssrc,items in blocks:
            packet += struct.pack('!I', ssrc)
            for sdes, value in items:
                sdescode = rtcpSDESdict[sdes]
                packet += struct.pack('!BB', sdescode, len(value)) + value
            packet = self._padIfNeeded(packet)
        packet = self._patchLengthHeader(packet)
        return packet

    def decode_BYE(self):
        self._contents = [[],'']
        for i in range(self._count):
            ssrc, = struct.unpack('!I', self._body[:4])
            self._contents[0].append(ssrc)
            self._body = self._body[4:]
        if self._body:
            # A reason!
            length = ord(self._body[0])
            reason = self._body[1:length+1]
            self._contents[1] = reason
            self._body = ''

    def encode_BYE(self):
        ssrcs, reason = self._contents
        packet = struct.pack('!BBH',len(ssrcs)|128, self._ptcode, 0)
        for ssrc in ssrcs:
            packet = packet + struct.pack('!I', ssrc)
        if reason:
            packet = packet + chr(len(reason)) + reason
        packet = self._padIfNeeded(packet)
        packet = self._patchLengthHeader(packet)
        return packet

    def decode_SR(self):
        self._contents = []
        ssrc, = struct.unpack('!I', self._body[:4])
        bits = struct.unpack('!IIIII', self._body[4:24])
        names = 'ntpHi', 'ntpLo', 'rtpTS', 'packets', 'octets'
        sender = dict(zip(names, bits))
        sender['ntpTS'] = (sender['ntpHi'] * 2**32) + sender['ntpLo']
        del sender['ntpHi'], sender['ntpLo']
        blocks = self._decodeRRSRReportBlocks()
        self._contents = [ssrc,sender,blocks]

    def encode_SR(self):
        return ''

    def decode_RR(self):
        ssrc, = struct.unpack('!I', self._body[:4])
        self._body = self._body[4:]
        blocks = self._decodeRRSRReportBlocks()
        self._contents = [ssrc,blocks]

    def encode_RR(self):
        return ''

    def _decodeRRSRReportBlocks(self):
        blocks = []
        for i in range(self._count):
            bits = struct.unpack('!IIIIII', self._body[:24])
            names = 'ssrc', 'lost', 'highest', 'jitter', 'lsr', 'dlsr'
            c = dict(zip(names,bits))
            c['fraclost'] = ((c['lost'] & 0xFF000000) >> 24)/256.0
            c['packlost'] = (c['lost'] & 0x00FFFFFF)
            del c['lost']
            blocks.append(c)
            self._body = self._body[24:]
        return blocks

    def decode_APP(self):
        self._contents = []
        subtype = self._count
        ssrc, = struct.unpack('!I', self._body[:4])
        name = self._body[4:8]
        value = self._body[8:]
        self._contents = [subtype,ssrc,name,value]

    def encode_APP(self):
        subtype,ssrc,name,value = self._contents
        packet = struct.pack('!BBHI',subtype|128, self._ptcode, 0, ssrc)
        packet = packet + name + value
        packet = self._padIfNeeded(packet)
        packet = self._patchLengthHeader(packet)
        return packet

    # We can at least roundtrip unknown RTCP PTs
    def decode_UNKNOWN(self):
        self._contents = (self._count, self._body)
        self._body = ''

    def encode_UKNOWN(self):
        count, body = self._contents
        packet = struct.pack('!BBH',count|128, self._ptcode, 0)
        packet = packet + body
        packet = self._padIfNeeded(packet)
        packet = self._patchLengthHeader(packet)
        return packet

    def __repr__(self):
        if self._body:
            leftover = ' '+repr(self._body)
        else:
            leftover = ''
        return '<RTCP %s %r %s>'%(self._pt, self._contents, leftover)

class RTCPCompound:
    "A single RTCP packet can contain multiple RTCP items"
    def __init__(self, bytes=None):
        self._rtcp = []
        if bytes:
            self.decode(bytes)

    def addPacket(self, packet):
        self._rtcp.append(packet)

    def decode(self, bytes):
        while bytes:
            count = ord(bytes[0]) & 31
            pt = ord(bytes[1])
            PT = rtcpPTdict.get(pt, 'UNKNOWN')
            try:
                length, = struct.unpack('!H', bytes[2:4])
            except struct.error:
                print "struct.unpack got bad number of bytes"
                return
            offset = 4*(length+1)
            body, bytes = bytes[4:offset], bytes[offset:]
            p = RTCPPacket(PT, ptcode=pt)
            p.decode(count, body)
            self._rtcp.append(p)

    def encode(self):
        return ''.join([x.encode() for x in self._rtcp])

    def __len__(self):
        return len(self._rtcp)

    def __getitem__(self, i):
        return self._rtcp[i]

    def __repr__(self):
        return "<RTCP Packet: (%s)>"%(', '.join([x.getPT() for x in self._rtcp]))


class RTCPProtocol(DatagramProtocol):
    def __init__(self, rtp):
        self.rtp = rtp
    def datagramReceived(self, datagram, addr):
        #print "received RTCP from %r (%d bytes): \n%s"%(addr, len(datagram), hexrepr(datagram))
        packet = RTCPCompound(datagram)
        self.rtp.lastreceivetime = time.time()
        #for rtcp in packet:
        #    print "RTCP:", rtcp

    def sendDatagram(self, packet):
        self.transport.write(packet)
