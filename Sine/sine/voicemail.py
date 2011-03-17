from sine import sip, sipserver, useragent
from axiom import userbase, item
from axiom.upgrade import registerUpgrader
from axiom.attributes import inmemory, bytes, reference
from axiom.dependency import dependsOn

from twisted.internet import defer
from zope.interface import implements
from sine.confession import AnonConfessionUser

class VoicemailDispatcher(item.Item):

    implements(sip.IVoiceSystem)
    typeName = "sine_voicemail_dispatcher"
    schemaVersion = 2

    localHost = bytes()
    uas = inmemory()

    powerupInterfaces = (sip.IVoiceSystem,)
    voicemailUser = dependsOn(AnonConfessionUser)
    def activate(self):
        if self.store.parent:
            svc = self.store.parent.findUnique(sipserver.SIPServer)
            if svc:
                self.uas = useragent.UserAgent.server(self, svc.transport.host, svc.mediaController)
                self.uas.transport = svc.transport

    def lookupProcessor(self, msg, dialogs):
        if isinstance(msg, sip.Request) and msg.method == "REGISTER":
            #not our dept
            return defer.succeed(None)

        for name, domain in userbase.getAccountNames(self.store, protocol=u'sip'):
            if name == sip.parseAddress(msg.headers["to"][0])[1].username:
                contact = sip.IContact(self.store)
                def regged(_):
                    return defer.succeed(None)
                def unregged(e):
                    self.uas.dialogs = dialogs
                    return self.uas
                return defer.maybeDeferred(contact.getRegistrationInfo, sip.parseAddress(msg.headers["from"][0])[1]).addCallbacks(regged, unregged)
        else:
            return defer.succeed(None)


    def localElementByName(self, n):
        for name, domain in userbase.getAccountNames(self.store, protocol=u'sip'):
            #if we got here, we have a SIP account...
            return useragent.ICallControllerFactory(self.store)




item.declareLegacyItem(VoicemailDispatcher.typeName, 1, dict(
    localHost=bytes(),
    installedOn=reference()))

def _voicemailDispatcher1to2(old):
    df = old.upgradeVersion(VoicemailDispatcher.typeName, 1, 2,
                            localHost=old.localHost,
                            voicemailUser=old.store.findOrCreate(
        AnonConfessionUser))
    return df
registerUpgrader(_voicemailDispatcher1to2, VoicemailDispatcher.typeName, 1, 2)
