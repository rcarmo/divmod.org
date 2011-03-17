# Copyright (c) 2008 Divmod.  See LICENSE for details.

import operator

from twisted.internet.protocol import ServerFactory
from twisted.protocols.amp import Unicode, Command, AMP

from epsilon.amprouter import Router


class NewRoute(Command):
    arguments = [('name', Unicode())]
    response = [('name', Unicode())]



class RoutingAMP(AMP):
    @NewRoute.responder
    def newRoute(self, name):
        route = self.boxReceiver.bindRoute(self.factory.routeProtocol())
        route.connectTo(name)
        return {'name': route.localRouteName}



class AMPRouteServerFactory(ServerFactory):
    protocol = RoutingAMP
    routeProtocol = None

    def buildProtocol(self, addr):
        router = Router()
        proto = self.protocol(router)
        proto.factory = self
        default = router.bindRoute(proto, None)
        default.connectTo(None)
        return proto



def connect(proto, router, receiver):
    route = router.bindRoute(receiver)
    d = proto.callRemote(NewRoute, name=route.localRouteName)
    d.addCallback(operator.getitem, 'name')
    d.addCallback(lambda name: route.connectTo(name))
    def connectionFailed(err):
        route.unbind()
        return err
    d.addErrback(connectionFailed)
    return d
