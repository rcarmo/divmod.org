# Copyright (C) 2004 Anthony Baxter
"This module contains the logic and classes for format negotiation"

from twisted.python.util import OrderedDict
from xshtoom.avail import codecs


class PTMarker:
    "A marker of a particular payload type"
    media = None

    def __init__(self, name, pt=None, clock=8000, params=1, fmtp=None):
        self.name = name
        self.pt = pt
        self.clock = clock
        self.params = params
        self.fmtp = fmtp

    def __repr__(self):
        if self.pt is None:
            pt = 'dynamic'
        else:
            pt = str(self.pt)
        cname = self.__class__.__name__
        return "<%s %s(%s)/%s/%s at %x>"%(cname, self.name, pt,
                                          self.clock, self.params, id(self))

class AudioPTMarker(PTMarker):
    "An audio payload type"
    media = 'audio'

class VideoPTMarker(PTMarker):
    "A video payload type"
    media = 'video'

PT_PCMU =       AudioPTMarker('PCMU',    clock=8000,  params=1, pt=0)
PT_GSM =        AudioPTMarker('GSM',     clock=8000,  params=1, pt=3)
# G723 is actually G.723.1, but is the same as G.723. XXX test against cisco
PT_G723 =       AudioPTMarker('G723',    clock=8000,  params=1, pt=4)
PT_DVI4 =       AudioPTMarker('DVI4',    clock=8000,  params=1, pt=5)
PT_DVI4_16K =   AudioPTMarker('DVI4',    clock=16000, params=1, pt=6)
PT_LPC =        AudioPTMarker('LPC',     clock=8000,  params=1, pt=7)
PT_PCMA =       AudioPTMarker('PCMA',    clock=8000,  params=1, pt=8)
PT_G722 =       AudioPTMarker('G722',    clock=8000,  params=1, pt=9)
PT_L16_STEREO = AudioPTMarker('L16',     clock=44100, params=2, pt=10)
PT_L16 =        AudioPTMarker('L16',     clock=44100, params=1, pt=11)
PT_QCELP =      AudioPTMarker('QCELP',   clock=8000,  params=1, pt=12)
PT_CN =         AudioPTMarker('CN',      clock=8000,  params=1, pt=13)
PT_G728 =       AudioPTMarker('G728',    clock=8000,  params=1, pt=15)
PT_DVI4_11K =   AudioPTMarker('DVI4',    clock=11025, params=1, pt=16)
PT_DVI4_22K =   AudioPTMarker('DVI4',    clock=22050, params=1, pt=17)
PT_G729 =       AudioPTMarker('G729',    clock=8000,  params=1, pt=18)
PT_xCN =        AudioPTMarker('xCN',     clock=8000,  params=1, pt=19)
PT_SPEEX =      AudioPTMarker('speex',   clock=8000,  params=1)
PT_SPEEX_16K =  AudioPTMarker('speex',   clock=16000, params=1)
PT_G726_40 =    AudioPTMarker('G726-40', clock=8000,  params=1)
# Deprecated - gone from RFC3551
PT_1016 =       AudioPTMarker('1016', clock=8000,  params=1, pt=1)
# aka G723-40 (5 bit data)
PT_G726_40 =    AudioPTMarker('G726-40', clock=8000,  params=1)
# G726-32 aka G721-32 (4 bit data)
PT_G726_32 =    AudioPTMarker('G726-32', clock=8000,  params=1)
# Deprecated spelling for G726-32 - gone from RFC3551
PT_G721 =       AudioPTMarker('G721', clock=8000,  params=1, pt=2)
# G726-24 aka G723-24 (3 bit data)
PT_G726_24 =    AudioPTMarker('G726-24', clock=8000,  params=1)
PT_G726_16 =    AudioPTMarker('G726-16', clock=8000,  params=1)
PT_G729D =      AudioPTMarker('G729D',   clock=8000,  params=1)
PT_G729E =      AudioPTMarker('G729E',   clock=8000,  params=1)
PT_GSM_EFR =    AudioPTMarker('GSM-EFR', clock=8000,  params=1)
PT_ILBC =       AudioPTMarker('iLBC',    clock=8000,  params=1)
#PT_L8 =         AudioPTMarker('L8',      clock=None,  params=1)
#PT_RED =        AudioPTMarker('RED',     clock=8000,  params=1)
#PT_VDVI =       AudioPTMarker('VDVI',    clock=None,  params=1)
PT_NTE =        PTMarker('telephone-event', clock=8000, params=None,
                        fmtp='0-16')
# Internal shtoom codec. Note that the L16 format, above, is at 44100 KHz.
PT_RAW =        AudioPTMarker('RAW_L16', clock=8000, params=1)

PT_CELB =       VideoPTMarker('CelB', clock=90000, pt=25)
PT_JPEG =       VideoPTMarker('JPEG', clock=90000, pt=26)
PT_NV =         VideoPTMarker('nv',   clock=90000, pt=28)
PT_H261 =       VideoPTMarker('H261', clock=90000, pt=31)
PT_MPV =        VideoPTMarker('MPV',  clock=90000, pt=32)
PT_MP2T =       VideoPTMarker('MP2T', clock=90000, pt=33)
PT_H263 =       VideoPTMarker('H263', clock=90000, pt=34)

TryCodecs = OrderedDict()
TryCodecs[PT_GSM] = codecs.gsm
TryCodecs[PT_SPEEX] = codecs.speex
TryCodecs[PT_DVI4] = codecs.dvi4
TryCodecs[PT_ILBC] = codecs.ilbc

class SDPGenerator:
    "Responsible for generating SDP for the RTPProtocol"

    def getSDP(self, rtp, extrartp=None):
        from xshtoom.sdp import SDP, MediaDescription
        if extrartp:
            raise ValueError("can't handle multiple RTP streams in a call yet")
        s = SDP()
        addr = rtp.getVisibleAddress()
        s.setServerIP(addr[0])
        md = MediaDescription() # defaults to type 'audio'
        s.addMediaDescription(md)
        md.setServerIP(addr[0])
        md.setLocalPort(addr[1])
        for pt, test in TryCodecs.items():
            if test is not None:
                md.addRtpMap(pt)
        md.addRtpMap(PT_PCMU)
        md.addRtpMap(PT_CN)
        md.addRtpMap(PT_NTE)
        return s

RTPDict = {}
all = globals()
for key,val in all.items():
    if isinstance(val, PTMarker):
        # By name
        RTPDict[key] = val
        # By object
        if val.pt is not None:
            RTPDict[val] = val.pt
        # By PT
        if val.pt is not None:
            RTPDict[val.pt] = val
        # By name/clock/param
        RTPDict[(val.name.lower(),val.clock,val.params or 1)] = val

del all, key, val
