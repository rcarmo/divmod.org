# Copyright (C) 2004 Anthony Baxter

# This file will eventually contain all of the horrors of import magic
# for audio interfaces

from xshtoom.avail import _removeImport

try:
    import ossaudiodev
except ImportError:
    ossaudiodev = None
    _removeImport('ossaudiodev')

if ossaudiodev is not None:
    from xshtoom.audio import ossaudio
    del ossaudiodev
else:
    ossaudio = None


try:
    import fastaudio
except ImportError:
    fastaudio = None
    _removeImport('fastaudio')

if fastaudio is not None:
    del fastaudio
    from xshtoom.audio import fast as fastaudio


try:
    import coreaudio
except ImportError:
    coreaudio = None
    _removeImport('coreaudio')

if coreaudio is not None:
    from xshtoom.audio import osxaudio
    del coreaudio
else:
    osxaudio = None

from xshtoom.audio import fileaudio

try:
    import alsaaudio
except ImportError:
    alsaaudio = None
    _removeImport('alsaaudio')

if alsaaudio is not None:
    from xshtoom.audio import alsa as alsaaudio

from xshtoom.audio import fileaudio, echoaudio


def listAudio():
    all = globals().copy()
    del all['listAudio']
    for name, val in all.items():
        if val is None:
            del all[name]
        elif name.startswith('_'):
            del all[name]
    out = []
    for order in ( 'alsaaudio', 'ossaudio', 'fastaudio', 'fileaudio' ):
        if order in all:
            out.append(order)
    return out
