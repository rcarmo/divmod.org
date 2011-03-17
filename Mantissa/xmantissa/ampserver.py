# -*- test-case-name: xmantissa.test.test_ampserver -*-
# Copyright (c) 2008 Divmod.  See LICENSE for details.

"""
This module provides an extensible L{AMP<twisted.protocols.amp>} server for
Mantissa.  The server supports authentication and allows interaction with one
or more L{IBoxReceiver} implementations.  L{IBoxReceiverFactory} powerups are
used to get L{IBoxReceiver} providers by name, routing AMP boxes for multiple
receivers over a single AMP connection.
"""

from zope.interface import implements

from twisted.internet.protocol import ServerFactory
from twisted.internet import reactor
from twisted.cred.portal import Portal
from twisted.protocols.amp import IBoxReceiver, Unicode
from twisted.protocols.amp import BoxDispatcher, CommandLocator, Command
from twisted.python.randbytes import secureRandom

from epsilon.ampauth import CredReceiver, OneTimePadChecker
from epsilon.amprouter import Router

from axiom.iaxiom import IPowerupIndirector
from axiom.item import Item
from axiom.attributes import integer, inmemory
from axiom.dependency import dependsOn
from axiom.userbase import LoginSystem, getLoginMethods
from axiom.upgrade import registerAttributeCopyingUpgrader

from xmantissa.ixmantissa import (
    IProtocolFactoryFactory, IBoxReceiverFactory, IOneTimePadGenerator)

__metaclass__ = type


class AMPConfiguration(Item):
    """
    Configuration object for a Mantissa AMP server.

    @ivar ONE_TIME_PAD_DURATION: The duration of each one-time pad, in
        seconds.
    @type ONE_TIME_PAD_DURATION: C{int}
    """
    powerupInterfaces = (IProtocolFactoryFactory, IOneTimePadGenerator)
    implements(*powerupInterfaces)

    schemaVersion = 2

    loginSystem = dependsOn(LoginSystem)
    _oneTimePads = inmemory()

    ONE_TIME_PAD_DURATION = 60 * 2
    callLater = staticmethod(reactor.callLater)

    def activate(self):
        """
        Initialize L{_oneTimePads}
        """
        self._oneTimePads = {}


    # IOneTimePadGenerator
    def generateOneTimePad(self, userStore):
        """
        Generate a pad which can be used to authenticate via AMP.  This pad
        will expire in L{ONE_TIME_PAD_DURATION} seconds.
        """
        pad = secureRandom(16).encode('hex')
        self._oneTimePads[pad] = userStore.idInParent
        def expirePad():
            self._oneTimePads.pop(pad, None)
        self.callLater(self.ONE_TIME_PAD_DURATION, expirePad)
        return pad


    # IProtocolFactoryFactory
    def getFactory(self):
        """
        Return a server factory which creates AMP protocol instances.
        """
        factory = ServerFactory()
        def protocol():
            proto = CredReceiver()
            proto.portal = Portal(
                self.loginSystem,
                [self.loginSystem,
                 OneTimePadChecker(self._oneTimePads)])
            return proto
        factory.protocol = protocol
        return factory



registerAttributeCopyingUpgrader(
    AMPConfiguration, 1, 2,
    postCopy=lambda new: new.store.powerUp(new, IOneTimePadGenerator))



class ProtocolUnknown(Exception):
    """
    An attempt was made to establish a connection over an AMP route via the
    L{Connect} command to a protocol name for which no factory could be
    located.
    """



class Connect(Command):
    """
    Command to establish a new route to an L{IBoxReceiver} as specified by a
    protocol name.
    """
    arguments = [('origin', Unicode()), ('protocol', Unicode())]
    response = [('route', Unicode())]

    errors = {ProtocolUnknown: 'PROTOCOL_UNKNOWN'}



class _RouteConnector(BoxDispatcher, CommandLocator):
    """
    The actual L{IBoxReceiver} implementation supplied by L{AMPRouter} to be
    used as the avatar.  There is one L{_RouteConnector} instance per
    connection.

    @ivar reactor: An L{IReactorTime} provider which will be used to schedule
        the actual route connection.  This is a workaround for a missing AMP
        API: the ability to indicate a response without returning a value from
        a responder.  The application L{IBoxReceiver} being associated with a
        new route cannot be allowed to send any boxes before the I{Connect}
        response box is sent.  The simplest way to do this is to schedule a
        timed call to do the route connection so that it happens after the
        responder returns.

    @ivar store: The L{Store} which contained the L{AMPRouter} which created
        this object and which will be used to find L{IBoxReceiverFactory}
        powerups.

    @ivar router: The L{Router} which will be used to create new routes.
    """
    def __init__(self, reactor, store, router):
        BoxDispatcher.__init__(self, self)
        self.reactor = reactor
        self.store = store
        self.router = router


    @Connect.responder
    def accept(self, origin, protocol):
        """
        Create a new route attached to a L{IBoxReceiver} created by the
        L{IBoxReceiverFactory} with the indicated protocol.

        @type origin: C{unicode}
        @param origin: The identifier of a route on the peer which will be
            associated with this connection.  Boxes sent back by the protocol
            which is created in this call will be sent back to this route.

        @type protocol: C{unicode}
        @param protocol: The name of the protocol to which to establish a
            connection.

        @raise ProtocolUnknown: If no factory can be found for the named
            protocol.

        @return: A newly created C{unicode} route identifier for this
            connection (as the value of a C{dict} with a C{'route'} key).
        """
        for factory in self.store.powerupsFor(IBoxReceiverFactory):
            # XXX What if there's a duplicate somewhere?
            if factory.protocol == protocol:
                receiver = factory.getBoxReceiver()
                route = self.router.bindRoute(receiver)
                # This might be better implemented using a hook on the box.
                # See Twisted ticket #3479.
                self.reactor.callLater(0, route.connectTo, origin)
                return {'route': route.localRouteName}
        raise ProtocolUnknown()



class AMPAvatar(Item):
    """
    An L{IBoxReceiver} avatar which multiplexes AMP boxes for other receiver
    powerups on this item's store.
    """
    powerupInterfaces = (IBoxReceiver,)
    implements(IPowerupIndirector)

    garbage = integer(
        doc="""
        This class is stateless.  This attribute satisfies the Axiom
        requirement that L{Item} subclasses have at least one attribute.
        """)


    def connectorFactory(self, router):
        """
        Create the default receiver to use with the L{Router} returned
        by C{indirect}.
        """
        return _RouteConnector(reactor, self.store, router)


    def indirect(self, interface):
        """
        Create a L{Router} to handle AMP boxes received over an AMP connection.
        """
        if interface is IBoxReceiver:
            router = Router()
            connector = self.connectorFactory(router)
            router.bindRoute(connector, None).connectTo(None)
            return router
        raise NotImplementedError()



def connectRoute(amp, router, receiver, protocol):
    """
    Connect the given receiver to a new box receiver for the given
    protocol.

    After connecting this router to an AMP server, use this method
    similarly to how you would use C{reactor.connectTCP} to establish a new
    connection to an HTTP, SMTP, or IRC server.

    @param receiver: An L{IBoxReceiver} which will be started when a route
        to a receiver for the given protocol is found.

    @param protocol: The name of a protocol which the AMP peer to which
        this router is connected has an L{IBoxReceiverFactory}.

    @return: A L{Deferred} which fires with C{receiver} when the route is
        established.
    """
    route = router.bindRoute(receiver)
    d = amp.callRemote(
        Connect,
        origin=route.localRouteName,
        protocol=protocol)
    def cbGotRoute(result):
        route.connectTo(result['route'])
        return receiver
    d.addCallback(cbGotRoute)
    return d



class EchoFactory(Item):
    """
    Box receiver factory for an AMP protocol which just echoes AMP boxes back
    to the sender.  This is primarily useful as an example of a box receiver
    factory and as a way to test whether it is possible to connect to protocols
    over a Mantissa AMP server (similar to VoIP echo tests).
    """
    powerupInterfaces = (IBoxReceiverFactory,)
    implements(*powerupInterfaces)

    protocol = u"http://divmod.org/ns/echo"

    _garbage = integer(
        doc="""
        meaningless attribute, only here to satisfy Axiom requirement for at
        least one attribute.
        """)

    def getBoxReceiver(self):
        return EchoReceiver()



class EchoReceiver:
    """
    An AMP box echoer.
    """
    implements(IBoxReceiver)

    def startReceivingBoxes(self, sender):
        self.sender = sender


    def ampBoxReceived(self, box):
        self.sender.sendBox(box)


    def stopReceivingBoxes(self, reason):
        pass



__all__ = [
    'ProtocolUnknown', 'RouteNotConnected',

    'Connect', 'connectRoute',

    'AMPConfiguration', 'AMPAvatar',

    'Router', 'MantissaRouter',

    'EchoFactory', 'EchoReceiver']
