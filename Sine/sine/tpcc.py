import os
from xshtoom.sdp import SDP
from zope.interface import implements
from twisted.internet import defer
from sine import useragent
from twisted.python import log

ASTERISK_SOUNDS_DIR = "/usr/share/asterisk/sounds"
def soundFile(name):
    return os.path.join(ASTERISK_SOUNDS_DIR, name+".gsm")

class UserAgent43PCC(useragent.UserAgent):
    def maybeStartAudio(self, dialog, sdp):
        """
        Do nothing.  We never want to start audio in the call-control path.
        """

class UserAgentA(UserAgent43PCC):
    """
    I handle steps 8,9, and 11 in RFC 3725 example 10.1.

    I am the same as a normal UserAgent, except I trigger the sending
    of an ACK to party B just before sending one to my peer. Also,
    receipt of a BYE sends a BYE to the other party.
    """
    def __init__(self, userAgentB, localpart, localHost, mc, dialogs):
        self.userAgentB = userAgentB
        self.controller = TrivialController()
        self.user = localpart
        useragent.UserAgent.__init__(self, localHost, mc, dialogs)

    def acknowledgeInvite(self, dialog, response):
        #step 9 has just occurred
        sdp = SDP(response.body)
        if self.userAgentB.ackDeferred:
            self.userAgentB.ackDeferred.callback(sdp)
        dialog.sendAck() #step 11

    def process_BYE(self, st, msg, addr, dialog):
        UserAgent43PCC.process_BYE(self, st, msg, addr, dialog)
        self.userAgentB.partyBDialog.sendBye()

class UserAgentB(UserAgent43PCC):
    """
    I handle steps 6,7, and 10 in RFC 3725 example 10.1.

    I am the same as a normal UserAgent, except that I respond
    differently to the 200 to the INVITE, by reinviting party A with
    the new session description offer and setting up a callback to
    send an ACK with the answer. Also, receipt of a BYE sends a BYE to
    the other party.

    """
    def __init__(self, partyADialog, localpart, localHost, mc, dialogs):

        self.controller = TrivialController()
        self.partyADialog = partyADialog
        self.user = localpart
        useragent.UserAgent.__init__(self, localHost, mc, dialogs)
        self.ackDeferred = None

    def acknowledgeInvite(self, dialog, response):
        #step 7 has just occurred
        if dialog.clientState == "early":
            #this is the first 200 we have received
            sdp = SDP(response.body)
            self.partyADialog.reinvite(None, sdp)
            oldtu = self.partyADialog.tu
            self.partyADialog.tu = UserAgentA(self, self.user, self.host, self.mediaController, self.dialogs)
            self.partyADialog.tu.transport = self.transport
            for ct in self.transport.clientTransactions.values():
                if ct.tu == oldtu:
                    ct.tu = self.partyADialog.tu
                    break
            self.ackDeferred = defer.Deferred()
            self.partyBDialog = dialog
            def _sendAck(answer):
                dialog.sendAck(answer.show()) #step 10
                dialog.sessionDescription = answer
                self.ackDeferred = None
            def _errAck(e):
                import pdb; pdb.set_trace()
                log.err(e)
                self.ackDeferred = None
            self.ackDeferred.addCallback(_sendAck).addErrback(_errAck)

    def process_BYE(self, st, msg, addr, dialog):
        UserAgent43PCC.process_BYE(self, st, msg, addr, dialog)
        self.partyADialog.sendBye()

class ThirdPartyCallController:
    """
    I start the second call after the original UserAgent sets up the first.
    """

    implements(useragent.ICallController)
    def __init__(self, dispatcher, localpart, localHost, mc, fromName, partyB):
        self.dispatcher = dispatcher
        self.localpart = localpart
        self.host = localHost
        self.fromName = fromName
        self.partyB = partyB
        self.reinvited = False
        self.mc = mc
    def callBegan(self, dialog):
        dialog.playFile(soundFile("transfer"), "gsm")
        uac2 = UserAgentB(dialog, self.localpart, self.host, self.mc, self.dispatcher.dialogs)
        uac2.transport = self.dispatcher.transport
        uac2._doCall(self.partyB, noSDP=True, fromName=self.fromName)

    def callEnded(self, dialog):
        pass
    def callFailed(self, dialog, message):
        pass

    def acceptCall(self, dialog):
        pass

    def receivedAudio(self, dialog, audio):
        pass

    def receivedDTMF(self, dialog, key):
        pass

class TrivialController:
    def acceptCall(self, dialog):
        pass
    def callBegan(self, dialog):
        pass
    def callFailed(self, dialog, message):
        pass
    def callEnded(self, dialog):
        pass
    def receivedAudio(self, dialog, audio):
        pass
