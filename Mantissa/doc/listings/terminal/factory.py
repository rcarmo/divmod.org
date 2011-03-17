# Copyright (c) 2009 Divmod.  See LICENSE for details.

from zope.interface import implements

from twisted.conch.insults.insults import TerminalProtocol

from axiom.item import Item
from axiom.attributes import integer

from xmantissa.ixmantissa import ITerminalServerFactory


class NoOpFactory(Item):
    powerupInterfaces = (ITerminalServerFactory,)
    implements(ITerminalServerFactory)

    extra = integer()

    name = u"no-op example"

    def buildTerminalProtocol(self, viewer):
        return TerminalProtocol()
