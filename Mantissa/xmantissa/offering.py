# -*- test-case-name: xmantissa.test.test_offering -*-
# Copyright 2008 Divmod, Inc. See LICENSE file for details
"""
Implemenation of Offerings, Mantissa's unit of installable application
functionality.
"""

from zope.interface import implements

from twisted import plugin
from twisted.python.components import registerAdapter

from nevow import inevow, loaders, rend, athena
from nevow.athena import expose

from epsilon.structlike import record

from axiom.store import Store
from axiom import item, userbase, attributes, substore
from axiom.dependency import installOn

from xmantissa import ixmantissa, plugins

class OfferingAlreadyInstalled(Exception):
    """
    Tried to install an offering, but an offering by the same name was
    already installed.

    This may mean someone tried to install the same offering twice, or
    that two unrelated offerings picked the same name and therefore
    conflict!  Oops.
    """

class Benefactor(object):
    """
    I implement a method of installing and removing chunks of
    functionality from a user's store.
    """

class Offering(record(
        'name description siteRequirements appPowerups installablePowerups '
        'loginInterfaces themes staticContentPath version',
        staticContentPath=None, version=None)):
    """
    A set of functionality which can be added to a Mantissa server.

    @see L{ixmantissa.IOffering}
    """
    implements(plugin.IPlugin, ixmantissa.IOffering)


class InstalledOffering(item.Item):
    typeName = 'mantissa_installed_offering'
    schemaVersion = 1

    offeringName = attributes.text(doc="""
    The name of the Offering to which this corresponds.
    """, allowNone=False)

    application = attributes.reference(doc="""
    A reference to the Application SubStore for this offering.
    """)

    def getOffering(self):
        """
        @return: the L{Offering} plugin object that corresponds to this object,
        or L{None}.
        """
        # XXX maybe we need to optimize this; it's called SUPER often, and this
        # is ghetto as hell, on the other hand, isn't that the plugin system's
        # fault?  dang, I don't know.
        for o in getOfferings():
            if o.name == self.offeringName:
                return o



def getOfferings():
    """
    Return the IOffering plugins available on this system.
    """
    return plugin.getPlugins(ixmantissa.IOffering, plugins)


class OfferingAdapter(object):
    """
    Implementation of L{ixmantissa.IOfferingTechnician} for
    L{axiom.store.Store}.

    @ivar _siteStore: The L{axiom.store.Store} being adapted.
    """
    implements(ixmantissa.IOfferingTechnician)

    def __init__(self, siteStore):
        self._siteStore = siteStore


    def getInstalledOfferingNames(self):
        """
        Get the I{offeringName} attribute of each L{InstalledOffering} in
        C{self._siteStore}.
        """
        return list(
            self._siteStore.query(InstalledOffering).getColumn("offeringName"))


    def getInstalledOfferings(self):
        """
        Return a mapping from the name of each L{InstalledOffering} in
        C{self._siteStore} to the corresponding L{IOffering} plugins.
        """
        d = {}
        installed = self._siteStore.query(InstalledOffering)
        for installation in installed:
            offering = installation.getOffering()
            if offering is not None:
                d[offering.name] = offering
        return d


    def installOffering(self, offering):
        """
        Install the given offering::

          - Create and install the powerups in its I{siteRequirements} list.
          - Create an application L{Store} and a L{LoginAccount} referring to
            it.  Install the I{appPowerups} on the application store.
          - Create an L{InstalledOffering.

        Perform all of these tasks in a transaction managed within the scope of
        this call (that means you should not call this function inside a
        transaction, or you should not handle any exceptions it raises inside
        an externally managed transaction).

        @type offering: L{IOffering}
        @param offering: The offering to install.

        @return: The C{InstalledOffering} item created.
        """
        for off in self._siteStore.query(
            InstalledOffering,
            InstalledOffering.offeringName == offering.name):
            raise OfferingAlreadyInstalled(off)

        def siteSetup():
            for (requiredInterface, requiredPowerup) in offering.siteRequirements:
                if requiredInterface is not None:
                    nn = requiredInterface(self._siteStore, None)
                    if nn is not None:
                        continue
                if requiredPowerup is None:
                    raise NotImplementedError(
                        'Interface %r required by %r but not provided by %r' %
                        (requiredInterface, offering, self._siteStore))
                self._siteStore.findOrCreate(
                    requiredPowerup, lambda p: installOn(p, self._siteStore))

            ls = self._siteStore.findOrCreate(userbase.LoginSystem)
            substoreItem = substore.SubStore.createNew(
                self._siteStore, ('app', offering.name + '.axiom'))
            ls.addAccount(offering.name, None, None, internal=True,
                          avatars=substoreItem)

            from xmantissa.publicweb import PublicWeb
            PublicWeb(store=self._siteStore, application=substoreItem,
                      prefixURL=offering.name)
            ss = substoreItem.open()
            def appSetup():
                for pup in offering.appPowerups:
                    installOn(pup(store=ss), ss)

            ss.transact(appSetup)
            # Woops, we need atomic cross-store transactions.
            io = InstalledOffering(
                store=self._siteStore, offeringName=offering.name,
                application=substoreItem)

            #Some new themes may be available now. Clear the theme cache
            #so they can show up.
            #XXX This is pretty terrible -- there
            #really should be a scheme by which ThemeCache instances can
            #be non-global. Fix this at the earliest opportunity.
            from xmantissa import webtheme
            webtheme.theThemeCache.emptyCache()
            return io
        return self._siteStore.transact(siteSetup)

registerAdapter(OfferingAdapter, Store, ixmantissa.IOfferingTechnician)



def isAppStore(s):
    """
    Return whether the given store is an application store or not.
    @param s: A Store.
    """
    if s.parent is None:
        return False
    substore = s.parent.getItemByID(s.idInParent)
    return s.parent.query(InstalledOffering,
                          InstalledOffering.application == substore
                          ).count() > 0



def getInstalledOfferingNames(s):
    """
    Return a list of the names of the Offerings which are installed on the
    given store.

    @param s: Site Store on which offering installations are tracked.
    """
    return ixmantissa.IOfferingTechnician(s).getInstalledOfferingNames()


def getInstalledOfferings(s):
    """
    Return a mapping from the names of installed IOffering plugins to
    the plugins themselves.

    @param s: Site Store on which offering installations are tracked.
    """
    return ixmantissa.IOfferingTechnician(s).getInstalledOfferings()


def installOffering(s, offering, configuration):
    """
    Create an app store for an L{Offering}, possibly installing some powerups
    on it, after checking that the site store has the requisite powerups
    installed on it. Also create an L{InstalledOffering} item referring to the
    app store and return it.
    """
    return ixmantissa.IOfferingTechnician(s).installOffering(offering)


class OfferingConfiguration(item.Item):
    """
    Provide administrative configuration tools for the L{IOffering}s available
    in this Mantissa server.
    """
    typeName = 'mantissa_offering_configuration_powerup'
    schemaVersion = 1

    installedOfferingCount = attributes.integer(default=0)
    installedOn = attributes.reference()
    powerupInterfaces = (ixmantissa.INavigableElement,)

    def installOffering(self, offering, configuration):
        """
        Create an app store for an L{Offering} and install its
        dependencies. Also create an L{InstalledOffering} in the site store,
        and return it.
        """
        s = self.store.parent
        self.installedOfferingCount += 1
        return installOffering(s, offering, configuration)


    def getTabs(self):
        # XXX profanity
        from xmantissa import webnav
        return [webnav.Tab('Admin', self.storeID, 0.3,
                           [webnav.Tab('Offerings', self.storeID, 1.0)],
                           authoritative=True)]



class UninstalledOfferingFragment(athena.LiveFragment):
    """
    Fragment representing a single Offering which has not been
    installed on the system.  It has a single remote method which will
    install it.
    """
    jsClass = u'Mantissa.Offering.UninstalledOffering'

    def __init__(self, original, offeringConfig, offeringPlugin, **kw):
        super(UninstalledOfferingFragment, self).__init__(original, **kw)
        self.offeringConfig = offeringConfig
        self.offeringPlugin = offeringPlugin

    def install(self, configuration):
        self.offeringConfig.installOffering(self.offeringPlugin, configuration)
    expose(install)


class OfferingConfigurationFragment(athena.LiveFragment):
    fragmentName = 'offering-configuration'
    live = 'athena'


    def __init__(self, *a, **kw):
        super(OfferingConfigurationFragment, self).__init__(*a, **kw)
        self.installedOfferings = getInstalledOfferingNames(self.original.store.parent)
        self.offeringPlugins = dict((p.name, p) for p in plugin.getPlugins(ixmantissa.IOffering, plugins))

    def head(self):
        return None

    def render_offerings(self, ctx, data):
        iq = inevow.IQ(ctx.tag)
        uninstalled = iq.patternGenerator('uninstalled')
        installed = iq.patternGenerator('installed')

        def offerings():
            for p in self.offeringPlugins.itervalues():
                data = {'name': p.name, 'description': p.description}
                if p.name not in self.installedOfferings:
                    f = UninstalledOfferingFragment(data, self.original, p, docFactory=loaders.stan(uninstalled()))
                    f.page = self.page
                else:
                    f = rend.Fragment(data, docFactory=loaders.stan(installed()))
                yield f

        return ctx.tag[offerings()]

registerAdapter(OfferingConfigurationFragment, OfferingConfiguration, ixmantissa.INavigableFragment)
