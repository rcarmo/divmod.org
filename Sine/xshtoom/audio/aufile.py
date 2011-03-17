import wave, sunau, sndhdr

from audioop import tomono, lin2lin, ratecv

import struct
if struct.pack("h", 1) == "\000\001":
    big_endian = 1
else:
    big_endian = 0

class BaseReader:
    _cvt = lambda s, x: x
    _freqCvt = { 8000: 160, 16000: 320, 32000: 640, 64000: 1280 }

    def __init__(self, fp):
        self.fp = self.module.open(fp, 'rb')
        p = self.fp.getparams()
        print p
        if (p[4] not in self.allowedComp):
            raise ValueError("Incorrect file format %r"%(p,))
        self.comptype = p[4]
        if p[0] == 2:
            self._cvt = lambda x,ch=p[1],c=self._cvt: tomono(c(x),ch,0.5,0.5)
        elif p[0] != 1:
            raise ValueError("can only handle mono/stereo, not %d"%p[0])
        if p[1] != 2:
            self._cvt = lambda x,ch=p[1],c=self._cvt: lin2lin(c(x),ch,2)
        self.sampwidth = p[1]
        if p[2] % 8000 != 0:
            raise ValueError("sampfreq must be multiple of 8k")
        self.sampfreq = p[2]
        if p[2] != 8000:
            print "rate conversion"
            self._ratecvt = None
            self._cvt = lambda x,c=self._cvt: self.rateCvt(c(x))

    def rateCvt(self, data):
        data, self._ratecvt = ratecv(data,2,1,self.sampfreq,8000,self._ratecvt)
        return data

    def read(self, frames=160):
        data = self.fp.readframes(frames * (self.sampfreq/8000))
        data = self._cvt(data)
        return data

    def reset(self):
        self.fp.setpos(0)

    def _close(self):
        self.fp.close()

class WavReader(BaseReader):
    module = wave
    allowedComp = ('NONE','ULAW')

class AuReader(BaseReader):
    module = sunau
    allowedComp = ('ULAW','NONE')

    def endianCvt(self, data):
        import array
        _array_fmts = None, None, 'h', None, 'l'
        if self.comptype == 'ULAW' or big_endian:
            return data
        if _array_fmts[self.sampwidth]:
            arr = array.array(_array_fmts[self.sampwidth])
            arr.fromstring(data)
            arr.byteswap()
            data = arr.tostring()
        return data

    _cvt = endianCvt

class BaseWriter:
    sampwidth = 2

    def __init__(self, fp):
        self.fp = self.module.open(fp, 'wb')
        self.fp.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))

    def write(self, data):
        return self.fp.writeframes(data)

    def close(self):
        self.fp.close()
    def getName(self):
        return self.fp.name
    name = property(getName)

class WavWriter(BaseWriter):
    module = wave

class AuWriter(BaseWriter):
    module = sunau
    def endianCvt(self, data):
        import array
        _array_fmts = None, None, 'h', None, 'l'
        if _array_fmts[self.sampwidth]:
            arr = array.array(_array_fmts[self.sampwidth])
            arr.fromstring(data)
            arr.byteswap()
            data = arr.tostring()
        return data
    def write(self, data):
        data = self.endianCvt(data)
        BaseWriter.write(self, data)


def getReader(filename):
    if filename.lower().endswith('.wav'):
        audio = WavReader(open(filename, 'rb'))
    elif filename.lower().endswith('.au'):
        audio = AuReader(open(filename, 'rb'))
    else:
        raise ValueError("only know .au/.wav files, not %s"%(filename))
    return audio

def getWriter(filename):
    if filename.lower().endswith('.wav'):
        audio = WavWriter(open(filename, 'wb'))
    elif filename.lower().endswith('.au'):
        audio = AuWriter(open(filename, 'wb'))
    else:
        raise ValueError("only know .au/.wav files, not %s"%(filename))
    return audio

try:
    import gsm
except ImportError:
    GSMReader = None
else:
    class GSMReader:
        def __init__(self, f):
            self.file = f
            self.gsm = gsm.gsm(big_endian)
        def read(self, samples):
            data = self.file.read(33)
            if data:
                return self.gsm.decode(data)
            else:
                return ''

# For testing porpoises
def getdev():
    import ossaudiodev
    dev = ossaudiodev.open('rw')
    dev.speed(8000)
    #dev.nonblock()
    ch = dev.channels(1)
    dev.setfmt(ossaudiodev.AFMT_S16_LE)
    return dev

def test():
    import sys
    if len(sys.argv) == 2:
        print sndhdr.what(sys.argv[1])
        inaudio = getReader(sys.argv[1])
        outaudio = getdev()
    elif len(sys.argv) == 3:
        inaudio = getReader(sys.argv[1])
        outaudio = getWriter(sys.argv[2])
    while True:
        data = inaudio.read()
        outaudio.write(data)
        print "len(data)", len(data)
        if not len(data):
            print "stopping because data len == %d"%(len(data))
            break


if __name__ == "__main__":
    test()
