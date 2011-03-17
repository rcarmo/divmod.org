from axiom.test.historic.stubloader import saveStub
from axiom.userbase import LoginSystem
from sine.sipserver import SIPServer
from sine.voicemail import VoicemailDispatcher

def createDatabase(s):
    loginSystem = LoginSystem(store=s)
    loginSystem.installOn(s)
    sip = SIPServer(store=s)
    sip.startService()
    account = loginSystem.addAccount(u'testuser', u'localhost', None)
    subStore = account.avatars.open()
    VoicemailDispatcher(store=subStore,
                        localHost='localhost').installOn(subStore)
    sip.stopService()
if __name__ == '__main__':
    saveStub(createDatabase, 10876)

