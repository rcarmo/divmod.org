"""
"""

from twisted.python import log
from xshtoom.audio.converters import MediaLayer



def findAudioInterface():
    # Ugh. Circular import hell
    from xshtoom.avail import audio as av_audio
    audioOptions = { 'oss': av_audio.ossaudio,
                     'alsa': av_audio.alsaaudio,
                     'fast': av_audio.fastaudio,
                     'port': av_audio.fastaudio,
                     'osx': av_audio.osxaudio,
                     'core': av_audio.osxaudio,
                     'file': av_audio.fileaudio,
                     'echo': av_audio.echoaudio,
                   }
    allAudioOptions = [
                        av_audio.alsaaudio,
                        av_audio.ossaudio,
                        av_audio.fastaudio,
                        av_audio.osxaudio
                      ]

    audioPref = attempts = None

    try:
        from __main__ import app
    except:
        app = None

    if app:
        audioPref = app.getPref('audio')

    print "audioPref is", audioPref
    if audioPref:
        audioint = audioOptions.get(audioPref)
        if not audioint:
            log.msg("requested audio interface %s unavailable"%(audioPref,))
        else:
            return audioint

    for audioint in allAudioOptions:
        if audioint:
            return audioint

_device = None

def getAudioDevice(_testAudioInt=None):
    from xshtoom.exceptions import NoAudioDevice
    global _device
    if _testAudioInt is not None:
        return MediaLayer(_testAudioInt.Device())

    if _device is None:
        audioint = findAudioInterface()
        if audioint is None:
            raise NoAudioDevice("no working audio interface found")
        dev = audioint.Device()
        _device = MediaLayer(dev)
    return _device
