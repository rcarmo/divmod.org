# Copyright (c) 2008 Divmod.  See LICENSE for details.

"""
An AMP server which requires authentication of its clients before exposing an
addition command.
"""

from sys import stdout

from twisted.python.log import startLogging, msg
from twisted.internet import reactor
from twisted.cred.portal import Portal
from twisted.protocols.amp import IBoxReceiver, Command, Integer, AMP

from epsilon.ampauth import CredAMPServerFactory, OneTimePadChecker


class Add(Command):
    """
    An example of an application-defined command which should be made available
    to clients after they successfully authenticate.
    """
    arguments = [("left", Integer()),
                 ("right", Integer())]

    response = [("sum", Integer())]



class Adder(AMP):
    """
    An example of an application-defined AMP protocol, the responders defined
    by which should only be available to clients after they have successfully
    authenticated.
    """
    def __init__(self, avatarId):
        AMP.__init__(self)
        self.avatarId = avatarId


    @Add.responder
    def add(self, left, right):
        msg("Adding %d to %d for %s" % (left, right, self.avatarId))
        return {'sum': left + right}



class AdditionRealm(object):
    """
    An example of an application-defined realm.
    """
    def requestAvatar(self, avatarId, mind, *interfaces):
        """
        Create Adder avatars for any IBoxReceiver request.
        """
        if IBoxReceiver in interfaces:
            return (IBoxReceiver, Adder(avatarId), lambda: None)
        raise NotImplementedError()



def main():
    """
    Start the AMP server and the reactor.
    """
    startLogging(stdout)
    checker = OneTimePadChecker({'pad': 0})
    realm = AdditionRealm()
    factory = CredAMPServerFactory(Portal(realm, [checker]))
    reactor.listenTCP(7805, factory)
    reactor.run()


if __name__ == '__main__':
    main()

