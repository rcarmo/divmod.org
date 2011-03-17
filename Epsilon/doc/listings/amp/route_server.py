# Copyright (c) 2008 Divmod.  See LICENSE for details.

from sys import stdout

from twisted.python.log import startLogging
from twisted.protocols.amp import Integer, Command, AMP
from twisted.internet import reactor

from route_setup import AMPRouteServerFactory


class Count(Command):
    response = [('value', Integer())]



class Counter(AMP):
    _valueCounter = 0

    @Count.responder
    def count(self):
        self._valueCounter += 1
        return {'value': self._valueCounter}



def main():
    startLogging(stdout)
    serverFactory = AMPRouteServerFactory()
    serverFactory.routeProtocol = Counter
    reactor.listenTCP(7805, serverFactory)
    reactor.run()



if __name__ == '__main__':
    main()
