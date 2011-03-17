# -*- test-case-name: shtoom.test.test_new_sdp -*-#
# Copyright (C) 2004 Anthony Baxter
# Copyright (C) 2004 Jamey Hicks
#

from xshtoom.rtp.formats import RTPDict, PTMarker
from twisted.python.util import OrderedDict

class BadAnnounceError(Exception):
    "Bad Announcement"

def get(obj,typechar,optional=0):
    return obj._d.get(typechar)

def getA(obj, subkey):
    return obj._a.get(subkey)

def parse_generic(obj, k, text):
    obj._d.setdefault(k, []).append(text)

def unparse_generic(obj, k):
    if obj._d.has_key(k):
        return obj._d[k]
    else:
        return []

def parse_singleton(obj, k, text):
    obj._d[k] = text

def unparse_singleton(obj, k):
    if obj._d.has_key(k):
        return [obj._d[k]]
    else:
        return []

def parse_o(obj, o, value):
    if value:
        l = value.split()
        if len(l) != 6:
            raise BadAnnounceError("wrong # fields in o=`%s'"%value)
        ( obj._o_username, obj._o_sessid, obj._o_version,
            obj._o_nettype, obj._o_addrfamily, obj._o_ipaddr ) = tuple(l)

def unparse_o(obj, o):
    return ['%s %s %s %s %s %s' % ( obj._o_username, obj._o_sessid,
                                    obj._o_version, obj._o_nettype,
                                    obj._o_addrfamily, obj._o_ipaddr )]

def parse_a(obj, a, text):
    words = text.split(':', 1)
    if len(words) > 1:
        # I don't know what is happening here, but I got a traceback here
        # because 'words' was too long before the ,1 was added.  The value was:
        # ['alt', '1 1 ', ' 55A94DDE 98A2400C *ip address elided* 6086']
        # Adding the ,1 seems to fix it but I don't know why. -glyph
        attr, attrvalue = words
    else:
        attr, attrvalue = text, None
    if attr == 'rtpmap':
        payload,info = attrvalue.split(' ')
        entry = rtpmap2canonical(int(payload), attrvalue)
        try:
            fmt = RTPDict[entry]
        except KeyError:
            name,clock,params = entry
            fmt = PTMarker(name, None, clock, params)
        obj.rtpmap[int(payload)] = (attrvalue, fmt)
        obj._a.setdefault(attr, OrderedDict())[int(payload)] = attrvalue
    else:
        obj._a.setdefault(attr, []).append(attrvalue)

def unparse_a(obj, k):
    out = []
    for (a,vs) in obj._a.items():
        if isinstance(vs, OrderedDict):
            vs = vs.values()
        for v in vs:
            if v:
                out.append('%s:%s' % (a, v))
            else:
                out.append(a)
    return out

def parse_c(obj, c, text):
    words = text.split(' ')
    (obj.nettype, obj.addrfamily, obj.ipaddr) = words

def unparse_c(obj, c):
    mds = getattr(obj, "mediaDescriptions", None)
    if mds and not [x for x in mds if not x.ipaddr]: #if every MediaDescription has an IP...
        return []
    if obj.ipaddr:
        return ['%s %s %s' % (obj.nettype, obj.addrfamily, obj.ipaddr)]
    else:
        return []
def parse_m(obj, m, value):
    if value:
        els = value.split()
        (obj.media, port, obj.transport) = els[:3]
        obj.setFormats(els[3:])
        obj.port = int(port)

def unparse_m(obj, m):
    return ['%s %s %s %s' % (obj.media, str(obj.port), obj.transport,
                            ' '.join(obj.formats))]

parsers = [
    ('v', 1, parse_singleton, unparse_singleton),
    ('o', 1, parse_o, unparse_o),
    ('s', 1, parse_singleton, unparse_singleton),
    ('i', 0, parse_generic, unparse_generic),
    ('u', 0, parse_generic, unparse_generic),
    ('e', 0, parse_generic, unparse_generic),
    ('p', 0, parse_generic, unparse_generic),
    ('c', 0, parse_c, unparse_c),
    ('b', 0, parse_generic, unparse_generic),
    ('t', 0, parse_singleton, unparse_singleton),
    ('r', 0, parse_generic, unparse_generic),
    ('k', 0, parse_generic, unparse_generic),
    ('a', 0, parse_a, unparse_a)
    ]

mdparsers = [
    ('m', 0, parse_m, unparse_m),
    ('i', 0, parse_generic, unparse_generic),
    ('c', 0, parse_c, unparse_c),
    ('b', 0, parse_generic, unparse_generic),
    ('k', 0, parse_generic, unparse_generic),
    ('a', 0, parse_a, unparse_a)
]

parser = {}
unparser = {}
mdparser = {}
mdunparser = {}
for (key, required, parseFcn, unparseFcn) in parsers:
    parser[key] = parseFcn
    unparser[key] = unparseFcn
for (key, required, parseFcn, unparseFcn) in mdparsers:
    mdparser[key] = parseFcn
    mdunparser[key] = unparseFcn
del key,required,parseFcn,unparseFcn

class MediaDescription:
    "The MediaDescription encapsulates all of the SDP media descriptions"
    def __init__(self, text=None):
        self.media = None
        self.nettype = 'IN'
        self.addrfamily = 'IP4'
        self.ipaddr = None
        self.port = None
        self.transport = None
        self.formats = []
        self._d = {}
        self._a = {}
        self.rtpmap = OrderedDict()
        self.media = 'audio'
        self.transport = 'RTP/AVP'
        self.keyManagement = None
        if text:
            parse_m(self, 'm', text)

    def setFormats(self, formats):
        if self.media in ( 'audio', 'video'):
            for pt in formats:
                pt = int(pt)
                if pt < 97:
                    try:
                        PT = RTPDict[pt]
                    except KeyError:
                        # We don't know this one - hopefully there's an
                        # a=rtpmap entry for it.
                        continue
                    self.addRtpMap(PT)
                    # XXX the above line is unbound local variable error if not RTPDict.has_key(pt) --Zooko 2004-09-29
        self.formats = formats

    def setMedia(self, media):
        self.media = media
    def setTransport(self, transport):
        self.transport = transport
    def setServerIP(self, l):
        self.ipaddr = l
    def setLocalPort(self, l):
        self.port = l

    def setKeyManagement(self, km):
        parse_a(self, 'keymgmt', km)

    def clearRtpMap(self):
        self.rtpmap = OrderedDict()

    def addRtpMap(self, fmt):
        if fmt.pt is None:
            pts = self.rtpmap.keys()
            pts.sort()
            if pts and pts[-1] > 100:
                payload = pts[-1] + 1
            else:
                payload = 101
        else:
            payload = fmt.pt
        rtpmap = "%d %s/%d%s%s"%(payload, fmt.name, fmt.clock,
                                 ((fmt.params and '/') or ""),
                                 fmt.params or "")
        self.rtpmap[int(payload)] = (rtpmap, fmt)
        self._a.setdefault('rtpmap', OrderedDict())[payload] = rtpmap
        self.formats.append(str(payload))

    def intersect(self, other):
        # See RFC 3264
        map1 = self.rtpmap
        d1 = {}
        for code,(e,fmt) in map1.items():
            d1[rtpmap2canonical(code,e)] = e
        map2 = other.rtpmap
        outmap = OrderedDict()
        # XXX quadratic - make rtpmap an ordereddict
        for code, (e, fmt) in map2.items():
            canon = rtpmap2canonical(code,e)
            if d1.has_key(canon):
                outmap[code] = (e, fmt)
        self.rtpmap = outmap
        self.formats = [ str(x) for x in self.rtpmap.keys() ]
        self._a['rtpmap'] = OrderedDict([ (code,e) for (code, (e, fmt)) in outmap.items() ])

class SDP:
    def __init__(self, text=None):
        from time import time
        self._id = None
        self._d = {'v': '0', 't': '0 0', 's': 'shtoom'}
        self._a = OrderedDict()
        self.mediaDescriptions = []
        # XXX Use the username preference
        self._o_username = '-'
        self._o_sessid = self._o_version = str(int(time()%1000 * 100))
        self._o_nettype = self.nettype = 'IN'
        self._o_addrfamily = self.addrfamily = 'IP4'
        self._o_ipaddr = self.ipaddr = None
        self.port = None
        if text:
            self.parse(text)
            self.assertSanity()
        else:
            # new SDP
            pass

    def name(self):
        return self._sessionName

    def info(self):
        return self._sessionInfo

    def version(self):
        return self._o_version

    def id(self):
        if not self._id:
            self._id = (self._o_username, self._o_sessid, self.nettype,
                        self.addrfamily, self.ipaddr)
        return self._id

    def parse(self, text):
        lines = text.split('\r\n')
        md = None
        for line in lines:
            elts = line.split('=')
            if len(elts) != 2:
                continue
            (k,v) = elts
            if k == 'm':
                md = MediaDescription(v)
                self.mediaDescriptions.append(md)
            elif md:
                mdparser[k](md, k, v)
            else:
                parser[k](self, k, v)

    def get(self, typechar, option=None):
        if option is None:
            return get(self, typechar)
        elif typechar is 'a':
            return getA(self, option)
        else:
            raise ValueError, "only know about suboptions for 'a' so far"

    def setServerIP(self, l):
        self._o_ipaddr = self.ipaddr = l

    def addSessionAttribute(self, attrname, attrval):
        if not isinstance(attrval, (list, tuple)):
            attrval = (attrval,)
        self._a[attrname] = attrval

    def addMediaDescription(self, md):
        self.mediaDescriptions.append(md)
    def removeMediaDescription(self, md):
        self.mediaDescriptions.remove(md)
    def getMediaDescription(self, media):
        for md in self.mediaDescriptions:
            if md.media == media:
                return md
        return None
    def hasMediaDescriptions(self):
        return bool(len(self.mediaDescriptions))

    def show(self):
        out = []
        for (k, req, p, u) in parsers:
            for l in u(self, k):
                out.append('%s=%s' % (k, l))
        for md in self.mediaDescriptions:
            for (k, req, p, u) in mdparsers:
                for l in u(md, k):
                    out.append('%s=%s' % (k, l))
        out.append('')
        s = '\r\n'.join(out)
        return s

    def intersect(self, other):
        # See RFC 3264
        mds = self.mediaDescriptions
        self.mediaDescriptions = []
        for md in mds:
            omd = None
            for o in other.mediaDescriptions:
                if md.media == o.media:
                    omd = o
                    break
            if omd:
                md.intersect(omd)
                self.mediaDescriptions.append(md)

    def assertSanity(self):
        pass

def ntp2delta(ticks):
    return (ticks - 220898800)


def rtpmap2canonical(code, entry):
    if not isinstance(code, int):
        raise ValueError(code)
    if code < 96:
        return code
    else:
        ocode,desc = entry.split(' ',1)
        desc = desc.split('/')
        if len(desc) == 2:
            desc.append('1') # default channels
        name,rate,channels = desc
        return (name.lower(),int(rate),int(channels))
