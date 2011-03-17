
"""
Tests for L{xmantissa.website.WebSite}'s discovery of L{ISiteRootPlugin}
powerups.
"""

from twisted.trial import unittest

from nevow.testutil import FakeRequest

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import text
from axiom.dependency import installOn

from xmantissa.website import PrefixURLMixin, WebSite
from xmantissa.ixmantissa import ISiteRootPlugin

from zope.interface import implements


class Dummy:
    def __init__(self, pfx):
        self.pfx = pfx



class PrefixTester(Item, PrefixURLMixin):

    implements(ISiteRootPlugin)

    sessioned = True

    typeName = 'test_prefix_widget'
    schemaVersion = 1

    prefixURL = text()

    def createResource(self):
        return Dummy(self.prefixURL)

    def installSite(self):
        """
        Not using the dependency system for this class because multiple
        instances can be installed.
        """
        for iface, priority in self.__getPowerupInterfaces__([]):
            self.store.powerUp(self, iface, priority)



class SiteRootTest(unittest.TestCase):
    def test_prefixPriorityMath(self):
        """
        L{WebSite.locateChild} returns the most specific L{ISiteRootPlugin}
        based on I{prefixURL} and the request path segments.
        """
        store = Store()

        PrefixTester(store=store, prefixURL=u"hello").installSite()
        PrefixTester(store=store, prefixURL=u"").installSite()

        website = WebSite(store=store)
        installOn(website, store)

        res, segs = website.locateChild(FakeRequest(), ('hello',))
        self.assertEquals(res.pfx, 'hello')
        self.assertEquals(segs, ())

        res, segs = website.locateChild(FakeRequest(), ('',))
        self.assertEquals(res.pfx, '')
        self.assertEquals(segs, ('',))
