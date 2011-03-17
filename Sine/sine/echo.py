from axiom.item import Item 
from zope.interface import implements
from sine import sip, useragent
from axiom.attributes import reference, inmemory, bytes

import os
class EchoDispatcher(Item):
    implements(sip.IVoiceSystem)
    typeName = "sine_echo_dispatcher"
    schemaVersion = 1

    installedOn = reference()
    localHost = bytes()
    uas = inmemory()

    powerupInterfaces = (sip.IVoiceSystem,)

    def activate(self):
        self.uas = useragent.UserAgent.server(self, self.localHost)

    def lookupProcessor(self, msg, dialogs):
        self.uas.dialogs = dialogs
        return self.uas

    def localElementByName(self, name):
        if name == 'echo':
            return useragent.ICallControllerFactory(self.store)
        else:
            raise sip.SIPLookupError(404)

class Echoer:
    implements(useragent.ICallController)
    def acceptCall(self, dialog):
        return True

    def callBegan(self, dialog):
        f = open(os.path.join(os.path.split(__file__)[0], 'echo_greeting.raw'))
        dialog.playFile(f).addCallback(lambda _: self.beginEchoing(dialog))

    def beginEchoing(self, dialog):
        dialog.echoing = True

    def receivedAudio(self, dialog, bytes):
        if getattr(dialog, 'echoing', False):
            sample = dialog.codec.handle_audio(bytes)
            dialog.rtp.handle_media_sample(sample)

    def receivedDTMF(self, dialog, key):
        if key == 11:
            raise useragent.Hangup()

    def callEnded(self, dialog):
        pass
    def callFailed(self, dialog, msg):
        pass
class EchoTest(Item, Echoer):
    implements(useragent.ICallControllerFactory, useragent.ICallController)

    typeName = "sine_echo_test"
    schemaVersion = 1

    installedOn = reference()

    def buildCallController(self, dialog):
        return self

    powerupInterfaces = (useragent.ICallControllerFactory,)
