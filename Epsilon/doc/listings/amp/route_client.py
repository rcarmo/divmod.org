# Copyright (c) 2008 Divmod.  See LICENSE for details.

import random

from twisted.internet.defer import Deferred, gatherResults
from twisted.internet.protocol import ClientCreator
from twisted.protocols.amp import AMP

from epsilon.react import react
from epsilon.amprouter import Router

from route_setup import connect
from route_server import Count


def display(value, id):
    print id, value


class CountClient(AMP):
    def __init__(self, identifier):
        AMP.__init__(self)
        self.identifier = identifier
        self.finished = Deferred()

    def startReceivingBoxes(self, sender):
        AMP.startReceivingBoxes(self, sender)

        counts = []
        for i in range(random.randrange(1, 5)):
            d = self.callRemote(Count)
            d.addCallback(display, self.identifier)
            counts.append(d)
        gatherResults(counts).chainDeferred(self.finished)



def makeRoutes(proto, router):
    router.bindRoute(proto, None).connectTo(None)

    finish = []
    for i in range(3):
        client = CountClient(i)
        finish.append(connect(proto, router, client))
        finish.append(client.finished)
    return gatherResults(finish)



def main(reactor):
    router = Router()
    cc = ClientCreator(reactor, AMP, router)
    d = cc.connectTCP('localhost', 7805)
    d.addCallback(makeRoutes, router)
    return d


if __name__ == '__main__':
    from twisted.internet import reactor
    react(reactor, main, [])
