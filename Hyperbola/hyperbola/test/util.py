
from twisted.python.reflect import qual

from epsilon.extime import Time

from axiom.store import Store
from axiom.userbase import LoginSystem
from axiom.plugins.mantissacmd import Mantissa

from xmantissa import sharing
from xmantissa.port import SSLPort
from xmantissa.product import Product
from xmantissa.web import SiteConfiguration

from hyperbola import hyperblurb
from hyperbola.hyperbola_model import HyperbolaPublicPresence

class HyperbolaTestMixin:
    """
    Mixin class providing various Hyperbola-specific test utilities
    """

    def _setUpStore(self):
        """
        Set up a store, install a L{HyperbolaPublicPresence} and its
        dependencies, and create a role
        """
        self.siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(
            self.siteStore, u"localhost", u"", generateCert=False)

        # Make it standard so there's no port number in the generated URL.
        # This kind of sucks.  I don't want people assuming SSLPorts are
        # created by Mantissa().installSite().  Oh right, I should add a better
        # API for initializing a Mantissa server. -exarkun
        site = self.siteStore.findUnique(SiteConfiguration)
        ssls = list(site.store.query(SSLPort))
        ssls[0].portNumber = 443

        self.loginSystem = self.siteStore.findUnique(LoginSystem)

        product = Product(store=self.siteStore,
                          types=[qual(HyperbolaPublicPresence)])

        acct = self.loginSystem.addAccount(
            u'user', u'localhost', u'asdf', internal=True)
        self.userStore = acct.avatars.open()

        product.installProductOn(self.userStore)

        self.publicPresence = self.userStore.findUnique(
            HyperbolaPublicPresence)

        self.role = sharing.Role(
            store=self.userStore,
            externalID=u'foo@host', description=u'foo')


    def _makeBlurb(self, flavor, title=None, body=None):
        """
        Make a minimal nonsense blurb with flavor C{flavor}

        @param flavor: the blurb flavor
        @type flavor: one of the C{unicode} L{hyperbola.hyperblurb.FLAVOR}
        constants

        @param title: the blurb title.  defaults to C{flavor}
        @type title: C{unicode}

        @param body: the blurb body.  defaults to C{flavor}
        @type body: C{unicode}

        @rtype: L{hyperbola.hyperblurb.Blurb}
        """
        if title is None:
            title = flavor
        if body is None:
            body = flavor
        return hyperblurb.Blurb(
            store=self.userStore,
            title=title,
            body=body,
            flavor=flavor,
            dateCreated=Time(),
            author=self.role)

    def _shareAndGetProxy(self, blurb):
        """
        Share C{blurb} to everyone and return a shared proxy

        @param blurb: a blurb
        @type blurb: L{hyperbola.hyperblurb.Blurb}

        @rtype: L{xmantissa.sharing.SharedProxy}
        """
        share = sharing.shareItem(blurb)
        return sharing.getShare(
            self.userStore,
            sharing.getEveryoneRole(self.userStore),
            share.shareID)
