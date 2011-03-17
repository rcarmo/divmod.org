from zope.interface import implements

from axiom.item import Item
from axiom.attributes import bytes

from nevow.url import URL

from xmantissa.ixmantissa import ISiteRootPlugin

class RedirectPlugin(Item):
    redirectFrom = bytes(default='admin.php')
    redirectTo = bytes(default='private')
    powerupInterfaces = (ISiteRootPlugin,)
    implements(*powerupInterfaces)

    def produceResource(self, request, segments, viewer):
        if segments == tuple([self.redirectFrom]):
            return (URL.fromRequest(request).child(self.redirectTo), ())

