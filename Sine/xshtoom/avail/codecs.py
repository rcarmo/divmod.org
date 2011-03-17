# Copyright (C) 2004 Anthony Baxter

# This file will eventually contain all of the horrors of import magic
# for codecs


from xshtoom.avail import _removeImport

try:
    import gsm
except ImportError:
    gsm = None
    _removeImport('gsm')

try:
    import speex
except ImportError:
    speex = None
    _removeImport('speex')

try:
    from audioop import ulaw2lin, lin2ulaw
    mulaw = ulaw2lin
    del ulaw2lin, lin2ulaw
except ImportError:
    mulaw = None

try:
    # _obviously_ broken :-)
    from audioop import alaw2lin, lin2alaw
    alaw = alaw2lin
except ImportError:
    alaw = None

dvi4 = None # always, until it's implemented
ilbc = None # always, until it's implemented

def listCodecs():
    all = globals().copy()
    del all['listCodecs']
    for name, val in all.items():
        if val is None:
            del all[name]
        elif name.startswith('_'):
            del all[name]
    return all.keys()
