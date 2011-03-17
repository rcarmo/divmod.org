
"""
Simple SMTP client which connects to localhost:$SMTP_SERVER_PORT and sends
$SMTP_MESSAGE_COUNT messages to $SMTP_RECIPIENT_ADDRESS.
"""

import os

from twisted.python.filepath import FilePath
from twisted.python.log import err
from twisted.internet import reactor
from twisted.internet.defer import Deferred, waitForDeferred, deferredGenerator
from twisted.application.service import Application, Service
from twisted.mail.smtp import SMTPSenderFactory

class MailerService(Service):
    def __init__(self, portNumber, messageCount, recipientAddress):
        self.portNumber = portNumber
        self.messageCount = messageCount
        self.recipientAddress = recipientAddress


    def main(self):
        files = [ch
                 for ch
                 in FilePath(__file__).sibling('messages').children()
                 if ch.isfile()]
        currentBatch = []
        sentSuccessfully = 0
        while self.running and sentSuccessfully < self.messageCount:
            if not currentBatch:
                currentBatch = list(files)
            d = Deferred()
            f = SMTPSenderFactory('postmaster@example.com',
                                  self.recipientAddress,
                                  currentBatch.pop().open(),
                                  d)
            reactor.connectTCP('127.0.0.1', self.portNumber, f)
            r = waitForDeferred(d)
            yield r
            try:
                r.getResult()
            except:
                err()
            else:
                sentSuccessfully += 1
    main = deferredGenerator(main)


    def startService(self):
        Service.startService(self)
        self.runningDeferred = self.main()
        self.runningDeferred.addErrback(err)


    def stopService(self):
        Service.stopService(self)
        return self.runningDeferred



application = Application("Mailer")
svc = MailerService(
    int(os.environ['SMTP_SERVER_PORT']),
    int(os.environ['SMTP_MESSAGE_COUNT']),
    os.environ['SMTP_RECIPIENT_ADDRESS'])
svc.setServiceParent(application)
