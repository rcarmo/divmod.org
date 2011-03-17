
"""
Simple POP3 server which accepts any login and serves the same small set of
messages many times over in a single giant mailbox.
"""

import sys, itertools, cStringIO

from zope.interface import implements

from twisted.mail import pop3
from twisted.cred import portal, checkers, credentials
from twisted.internet import protocol
from twisted.application import internet, service
from twisted.python import filepath


class Mailbox(object):
    implements(pop3.IMailbox)

    def __init__(self, messages, repetitions=None):
        self.messages = messages
        if repetitions is None:
            repetitions = 50
        self.repetitions = repetitions


    def listMessages(self, index=None):
        if index is None:
            sizes = map(len, self.messages)
            repeatedSizes = itertools.cycle(sizes)
            boundedRepeated = itertools.islice(
                repeatedSizes, len(self.messages) * self.repetitions)
            return boundedRepeated
        return len(self.messages[index % len(self.messages)])


    def getMessage(self, index):
        return cStringIO.StringIO(self.messages[index % len(self.messages)])


    def getUidl(self, index):
        return index


    def deleteMessage(self, index):
        raise NotImplementedError("Don't delete stuff")


    def undeleteMessages(self):
        pass


    def sync(self):
        pass



class Realm(object):
    implements(portal.IRealm)

    def __init__(self, mailbox):
        self.mailbox = mailbox


    def requestAvatar(self, avatarId, mind, *interfaces):
        for iface in interfaces:
            if iface is pop3.IMailbox:
                return iface, self.mailbox, lambda: None
        raise NotImplementedError()



class Checker(object):
    implements(checkers.ICredentialsChecker)

    credentialInterfaces = (credentials.IUsernamePassword,)

    def requestAvatarId(self, credentials):
        return credentials.username



def makeService(messages, repetitions=None):
    m = Mailbox(messages, repetitions)
    r = Realm(m)
    p = portal.Portal(r)
    p.registerChecker(Checker())
    f = protocol.ServerFactory()
    f.protocol = pop3.POP3
    f.protocol.portal = p
    return internet.TCPServer(12345, f)

application = service.Application("POP3 Server")
makeService([p.open().read()
             for p
             in filepath.FilePath(__file__).sibling('messages').children()
             if p.isfile()
             ]).setServiceParent(application)
