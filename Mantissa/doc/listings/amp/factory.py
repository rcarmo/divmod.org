# Copyright (c) 2008 Divmod.  See LICENSE for details.

from zope.interface import implements

from twisted.protocols.amp import AMP

from axiom.item import Item
from axiom.attributes import integer

from xmantissa.ixmantissa import IBoxReceiverFactory


class SimpleFactory(Item):
    powerupInterfaces = (IBoxReceiverFactory,)
    implements(IBoxReceiverFactory)

    extra = integer()

    protocol = u"http://divmod.org/ns/example"

    def getBoxReceiver(self):
        return AMP()
