import os
import sys
import time
from StringIO import StringIO
from os.path import join as opj

from twisted.python import log
from twisted.internet import defer
from twisted.mail import smtp
from twisted.internet import reactor

def sendmail(smtphost, port, from_addr, to_addrs, msg):
    msg = StringIO(str(msg))
    d = defer.Deferred()
    factory = smtp.SMTPSenderFactory(from_addr, to_addrs, msg, d)
    factory.noisy = False
    reactor.connectTCP(smtphost, port, factory)
    return d

class MessageSendingController:
    sentBytes = 0

    def __init__(self, host, port, recip, messages):
        self.host = host
        self.port = port
        self.recip = recip
        self.messages = messages[:]
        self.nMsgs = len(self.messages)

    def next(self):
        try:
            return file(self.messages.pop(0), 'rU').read()
        except:
            raise StopIteration

    def send(self, nConns=1, bps=None):
        d = []
        pb = self.messages.append
        for c in range(nConns):
            d.append(MessageSender(self.host, self.port, self.recip, self.next, bps, pb
                ).sendMessages(
                ).addCallback(self._cbSenderFinished
                ))
        return defer.DeferredList(d
            ).addCallback(self._cbSentAll
            )

    def _cbSenderFinished(self, bytes):
        self.sentBytes += bytes

    def _cbSentAll(self, result):
        return self.sentBytes

class MessageSender:
    def __init__(self, host, port, recip, msgs, bps, putBack):
        self.host = host
        self.port = port
        self.recip = recip
        self.msgs = msgs
        self.bps = bps
        self.putBack = putBack

    def msgFrom(self):
        return "foo@bar"

    def msgTo(self):
        return self.recip

    def sendMessages(self, _bytes=0):
        try:
            m = self.msgs()
        except StopIteration:
            return defer.succeed(_bytes)
        else:
            return self.sendOneMessage(m
                ).addErrback(self._ebSendMessages, m
                ).addCallback(self._cbSendMessages, _bytes + len(m)
                )

    def sendOneMessage(self, msg):
        return sendmail(self.host, self.port, self.msgFrom(), [self.msgTo()], msg
            )

    def _ebSendMessages(self, failure, msg):
        self.putBack(msg)
        log.err(failure)

    def _cbSendMessages(self, result, bytes):
        return self.sendMessages(bytes)

def sendDirectory(path, host, port, recip):
    return MessageSendingController(host, port, recip, [opj(path, f) for f in os.listdir(path)])

def finished(bytes, nMsgs, startTime):
    dur = (time.time() - startTime)
    log.msg('%4.2f bps' % (bytes / dur))
    log.msg('%4.2f mps' % (nMsgs / dur))

def main(path, host, port, recip, conns=4):
    log.startLogging(sys.stdout)

    c = sendDirectory(path, host, int(port), recip)
    c.send(int(conns)
        ).addCallback(finished, len(c.messages), time.time(),
        ).addBoth(lambda _: reactor.stop()
        )
    reactor.run()

def usage():
    return ("Usage: %s <directory of messages> <host> <port> "
            "<recipient address> [<concurrent connections>] "
            % (sys.argv[0],))
