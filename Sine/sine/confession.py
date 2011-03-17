# VoIP confession booth -- because angst is easier to convey with your voice

from axiom.item import Item
from xmantissa import website, ixmantissa

from zope.interface import implements
from sine import sip, useragent, sipserver
from axiom.attributes import inmemory, reference, integer, text, bytes, timestamp
from axiom.dependency import dependsOn, installOn

from twisted.internet import reactor
from twisted.python import filepath, log
from nevow import static
from epsilon.modal import ModalType, mode
import wave, os
from epsilon.extime import Time

ASTERISK_SOUNDS_DIR = "/usr/share/asterisk/sounds"
def soundFile(name):
    return os.path.join(ASTERISK_SOUNDS_DIR, name+".gsm")

class ConfessionBenefactor(Item):
    implements(ixmantissa.IBenefactor)

    typeName = 'confession_benefactor'
    schemaVersion = 1

    # Number of users this benefactor has endowed
    endowed = integer(default = 0)

    localHost = bytes()

class ConfessionUser(Item):
    implements(useragent.ICallControllerFactory)

    typeName = "sine_confession_user"
    schemaVersion = 1

    installedOn = reference()

    powerupInterfaces = (useragent.ICallControllerFactory,)

    def buildCallController(self, dialog):
        return ConfessionCall(self)

class ConfessionDispatcher(Item):
    implements(sip.IVoiceSystem)
    typeName = "sine_confession_dispatcher"
    schemaVersion = 1

    installedOn = reference()
    localHost = bytes()
    uas = inmemory()

    confessionUser = dependsOn(ConfessionUser)

    powerupInterfaces = (sip.IVoiceSystem,)

    def activate(self):
        svc = self.store.parent.findUnique(sipserver.SIPServer)
        self.uas = useragent.UserAgent.server(self, self.localHost, svc.mediaController)

    def lookupProcessor(self, msg, dialogs):
        #XXX haaaaack
        if 'confession@' in msg.headers['to'][0]:
            #double hack =/
            self.uas.dialogs = dialogs
            return self.uas

    def localElementByName(self, name):
        if name == 'confession':
            return self.confessionUser
        else:
            raise sip.SIPLookupError(404)

class ConfessionCall(object):
    __metaclass__ = ModalType
    initialMode = 'recording'
    modeAttribute = 'mode'
    implements(useragent.ICallController)
    filename = None
    recordingTimer = None
    def __init__(self, avatar, anon=False):
        self.avatar = avatar
        self.anon=anon

    def callBegan(self, dialog):
        def playBeep(r):
            return dialog.playFile(soundFile("beep"), "gsm")
        d = dialog.playFile(soundFile("vm-intro"), "gsm").addCallback(playBeep)
        if self.anon:
            d.addCallback(lambda _: self.beginRecording(dialog, dialog.remoteAddress[1].toCredString()))
        else:
            d.addCallback(lambda _: self.beginRecording(dialog))
        d.addErrback(lambda e: log.err(e))

    def beginRecording(self, dialog, target=""):
        if self.anon:
            timeLimit = 45
        else:
            timeLimit = 180
        self.fromAddress = target
        dir = self.avatar.store.newTemporaryFilePath(target, ".wav")
        if not os.path.exists(dir.path):
            os.makedirs(dir.path)
        self.filename = dir.temporarySibling().path
        dialog.startRecording(self.filename, format="wav")

        self.recordingTimer = reactor.callLater(timeLimit, self.endRecording, dialog)

    def saveRecording(self, store):
        r = Recording(store=store, fromAddress=unicode(self.fromAddress))
        r.audioFromFile(self.filename)
        installOn(r, store)


    def playReviewMessage(self, dialog):
        dialog.playFile(soundFile("vm-review"), "gsm").addCallback(
            lambda x: x['done'] and dialog.playFile(soundFile("vm-star-cancel"), "gsm")).addErrback(lambda e: log.err(e))

    class recording(mode):
        def receivedDTMF(self, dialog, key):
            if self.filename and key == 11:
                self.endRecording(dialog)
                self.playReviewMessage(dialog)
                self.mode = "review"

    class review(mode):
        def receivedDTMF(self, dialog, key):
            #1 - accept
            #2 - replay
            #3 - re-record
            #10 - give up
            dialog.stopPlaying()
            if key == 1:
                self.endRecording(dialog)
                self.avatar.store.transact(self.saveRecording, self.avatar.store)
                self.filename = None
                return dialog.playFile(soundFile("auth-thankyou"), "gsm").addCallback (lambda _: self.hangup(dialog))

            elif key == 2:
                return dialog.playFile(self.filename, "wav").addCallback(lambda _: self.playReviewMessage(dialog))
            elif key == 3:
                self.mode = "recording"
                def beginAgain():
                    dialog.playFile(soundFile("beep"), "gsm")
                    os.unlink(self.filename)
                    if self.anon:
                        self.beginRecording(dialog, dialog.remoteAddress[1].toCredString())
                    else:
                        self.beginRecording(dialog)
                reactor.callLater(0.5, beginAgain)
            elif key == 10:
                os.unlink(self.filename)
                self.filename = None
                self.endRecording(dialog)
                return dialog.playFile(soundFile("vm-goodbye"), "gsm").addCallback(lambda _: self.hangup(dialog))

    def hangup(self, dialog):
        reactor.callLater(0.5, dialog.sendBye)

    def endRecording(self, dialog):
        if self.recordingTimer and self.recordingTimer.active():
            self.recordingTimer.cancel()
        if self.mode == "recording":
            dialog.endRecording()


    def callEnded(self, dialog):
        self.endRecording(dialog)
        if self.filename:
            self.saveRecording(self.avatar.store)





class Recording(Item, website.PrefixURLMixin):
    typeName = "sine_confession_recording"
    schemaVersion = 1

    prefixURL = text()
    length = integer() #seconds in recording
    fromAddress = text()
    time = timestamp()

    sessioned = True
    sessionless = False

    def __init__(self, **args):
        super(Recording, self).__init__(**args)
        self.time = Time()
        self.prefixURL = unicode("private/recordings/%s.wav" % str(self.storeID))

    def getFile(self):
        dir = self.store.newDirectory("recordings")
        if not dir.exists():
            dir.makedirs() #should i really have to do this?
        return dir.child("%s.wav" % self.storeID)

    file = property(getFile)

    def audioFromFile(self, filename):
        f = self.file.path
        filepath.FilePath(filename).moveTo(self.file)
        w = wave.open(f)
        self.length = w.getnframes() / w.getframerate()
        w.close()

    def createResource(self):
        return static.File(self.file.path)



class AnonConfessionUser(Item):
    implements(useragent.ICallControllerFactory)

    typeName = "sine_anonconfession_user"
    schemaVersion = 1

    installedOn = reference()

    powerupInterfaces = (useragent.ICallControllerFactory,)

    def buildCallController(self, dialog):
        return ConfessionCall(self, True)
