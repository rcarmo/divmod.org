from itertools import chain
from twisted.python.reflect import namedAny, qual
from twisted.python.components import registerAdapter

from axiom.item import Item
from axiom.attributes import textlist, integer, boolean
from axiom.dependency import installOn, uninstallFrom, installedRequirements

from nevow import athena, tags
from nevow.page import renderer

from xmantissa.suspension import  unsuspendTabProviders
from xmantissa.ixmantissa import INavigableElement, INavigableFragment
from xmantissa import liveform
from xmantissa.offering import getInstalledOfferings
from xmantissa.webnav import Tab

from zope.interface import implements

class Product(Item):
    """
    I represent a collection of powerups to install on a user store. When a
    user is to be endowed with the functionality described here, an
    Installation is created in its store based on me.
    """

    types = textlist()

    def installProductOn(self, userstore):
        """
        Creates an Installation in this user store for our collection
        of powerups, and then install those powerups on the user's
        store.
        """

        def install():
            i = Installation(store=userstore)
            i.types = self.types
            i.install()
        userstore.transact(install)

    def removeProductFrom(self, userstore):
        """
        Uninstall all the powerups this product references and remove
        the Installation item from the user's store. Doesn't remove
        the actual powerups currently, but /should/ reactivate them if
        this product is reinstalled.
        """
        def uninstall():
            #this is probably highly insufficient, but i don't know the
            #requirements
            i = userstore.findFirst(Installation,
                                    Installation.types == self.types)
            i.uninstall()
            i.deleteFromStore()
        userstore.transact(uninstall)

    def installOrResume(self, userstore):
        """
        Install this product on a user store. If this product has been
        installed on the user store already and the installation is suspended,
        it will be resumed. If it exists and is not suspended, an error will be
        raised.
        """
        for i in userstore.query(Installation, Installation.types == self.types):
            if i.suspended:
                unsuspendTabProviders(i)
                return
            else:
                raise RuntimeError("installOrResume called for an"
                                   " installation that isn't suspended")
        else:
            self.installProductOn(userstore)

class Installation(Item):
    """
    I represent a collection of functionality installed on a user store. I
    reference a collection of powerups, probably designated by a Product.
    """

    types = textlist()
    _items = textlist()
    suspended = boolean(default=False)

    def items(self):
        """
        Loads the items this Installation refers to.
        """
        for id in self._items:
            yield self.store.getItemByID(int(id))
    items = property(items)
    def allPowerups(self):
        return set(chain(self.items, *[installedRequirements(self.store, i) for
                                       i in self.items]))
    allPowerups = property(allPowerups)

    def install(self):
        """
        Called when installed on the user store. Installs my powerups.
        """
        items = []
        for typeName in self.types:
            it = self.store.findOrCreate(namedAny(typeName))
            installOn(it, self.store)
            items.append(str(it.storeID).decode('ascii'))
        self._items = items

    def uninstall(self):
        """
        Called when uninstalled from the user store. Uninstalls all my
        powerups.
        """
        for item in self.items:
            uninstallFrom(item, self.store)
        self._items = []


class ProductConfiguration(Item):
    implements(INavigableElement)
    attribute = integer(doc="It is an attribute")

    powerupInterfaces = (INavigableElement,)

    def getTabs(self):
        return [Tab('Admin', self.storeID, 0.5,
                    [Tab('Products', self.storeID, 0.6)],
                    authoritative=False)]

    def createProduct(self, powerups):
        """
        Create a new L{Product} instance which confers the given
        powerups.

        @type powerups: C{list} of powerup item types

        @rtype: L{Product}
        @return: The new product instance.
        """
        types = [qual(powerup).decode('ascii')
                       for powerup in powerups]
        for p in self.store.parent.query(Product):
            for t in types:
                if t in p.types:
                    raise ValueError("%s is already included in a Product" % (t,))
        return Product(store=self.store.parent,
                       types=types)

class ProductFragment(athena.LiveElement):
    fragmentName = 'product-configuration'
    live = 'athena'

    def __init__(self, configger):
        athena.LiveElement.__init__(self)
        self.original = configger

    def head(self):
        #XXX put this in its own CSS file?
        return tags.style(type='text/css')['''
        input[name=linktext], input[name=subject], textarea[name=blurb] { width: 40em }
        ''']

    def getInstallablePowerups(self):
                for installedOffering in getInstalledOfferings(self.original.store.parent).itervalues():
                    for p in installedOffering.installablePowerups:
                        yield p


    def coerceProduct(self, **kw):
        """
        Create a product and return a status string which should be part of a
        template.

        @param **kw: Fully qualified Python names for powerup types to
        associate with the created product.
        """
        self.original.createProduct(filter(None, kw.values()))
        return u'Created.'


    def makePowerupCoercer(self, powerup):
        def powerupCoercer(selectedPowerup):
            if selectedPowerup:
                return powerup
            else:
                return None
        return powerupCoercer

    def makePowerupSelector(self, desc):
        return liveform.Parameter('selectedPowerup',
                                  liveform.CHECKBOX_INPUT,
                                  bool, desc)

    def powerupConfigurationParameter(self, (name, desc, p)):
        return liveform.Parameter(
            name,
            liveform.FORM_INPUT,
            liveform.LiveForm(self.makePowerupCoercer(p),
                              [self.makePowerupSelector(desc)],
                              name))
    def productConfigurationForm(self, request, tag):
        productList = liveform.LiveForm(self.coerceProduct,
                                        [self.powerupConfigurationParameter(pi)
                                         for pi in self.getInstallablePowerups()],
                                        u"Installable Powerups")
        productList.setFragmentParent(self)
        return productList

    renderer(productConfigurationForm)

    def configuredProducts(self, request, tag):
        for prod in self.original.store.parent.query(Product):
            yield repr(prod.types)

    renderer(configuredProducts)
registerAdapter(ProductFragment, ProductConfiguration, INavigableFragment)
