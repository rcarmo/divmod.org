"""
Tests for xmantissa.offering.
"""

from zope.interface import Interface, implements
from zope.interface.verify import verifyClass, verifyObject

from twisted.trial import unittest

from axiom.store import Store
from axiom import item, attributes, userbase

from axiom.plugins.mantissacmd import Mantissa

from axiom.dependency import installedOn

from xmantissa import ixmantissa, offering

from xmantissa.web import SiteConfiguration
from xmantissa.ampserver import AMPConfiguration
from xmantissa.plugins.baseoff import baseOffering, ampOffering
from xmantissa.plugins.offerings import peopleOffering


class TestSiteRequirement(item.Item):
    typeName = 'test_site_requirement'
    schemaVersion = 1

    attr = attributes.integer()

class TestAppPowerup(item.Item):
    typeName = 'test_app_powerup'
    schemaVersion = 1

    attr = attributes.integer()



class ITestInterface(Interface):
    """
    An interface to which no object can be adapted.  Used to ensure failed
    adaption causes a powerup to be installed.
    """



class OfferingPluginTest(unittest.TestCase):
    """
    A simple test for getOffering.
    """

    def test_getOfferings(self):
        """
        getOffering should use the Twisted plugin system to load the plugins
        provided with Mantissa.  Since this is dynamic, we can't assert
        anything about the complete list, but we can at least verify that all
        the plugins that should be there, are.
        """
        foundOfferings = list(offering.getOfferings())
        allExpectedOfferings = [baseOffering, ampOffering, peopleOffering]
        for expected in allExpectedOfferings:
            self.assertIn(expected, foundOfferings)


class OfferingTest(unittest.TestCase):
    def setUp(self):
        self.store = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.store, u"localhost", u"", False)
        Mantissa().installAdmin(self.store, u'admin', u'localhost', u'asdf')
        self.userbase = self.store.findUnique(userbase.LoginSystem)
        self.adminAccount = self.userbase.accountByAddress(
            u'admin', u'localhost')
        off = offering.Offering(
            name=u'test_offering',
            description=u'This is an offering which tests the offering '
                         'installation mechanism',
            siteRequirements=[(ITestInterface, TestSiteRequirement)],
            appPowerups=[TestAppPowerup],
            installablePowerups=[],
            loginInterfaces=[],
            themes=[],
            )
        self.offering = off
        # Add this somewhere that the plugin system is going to see it.
        self._originalGetOfferings = offering.getOfferings
        offering.getOfferings = self.fakeGetOfferings


    def fakeGetOfferings(self):
        """
        Return standard list of offerings, plus one extra.
        """
        return list(self._originalGetOfferings()) + [self.offering]


    def tearDown(self):
        """
        Remove the temporary offering.
        """
        offering.getOfferings = self._originalGetOfferings


    def test_installOffering(self):
        """
        L{OfferingConfiguration.installOffering} should install the given
        offering on the Mantissa server.
        """
        conf = self.adminAccount.avatars.open().findUnique(
            offering.OfferingConfiguration)
        io = conf.installOffering(self.offering, None)

        # InstalledOffering should be returned, and installed on the site store
        foundIO = self.store.findUnique(offering.InstalledOffering,
                  offering.InstalledOffering.offeringName == self.offering.name)
        self.assertIdentical(io, foundIO)

        # Site store requirements should be on the site store
        tsr = self.store.findUnique(TestSiteRequirement)
        self.failUnless(installedOn(tsr), self.store)

        # App store should have been created
        appStore = self.userbase.accountByAddress(self.offering.name, None)
        self.assertNotEqual(appStore, None)

        # App store requirements should be on the app store
        ss = appStore.avatars.open()
        tap = ss.findUnique(TestAppPowerup)
        self.failUnless(installedOn(tap), ss)

        self.assertRaises(offering.OfferingAlreadyInstalled,
                          conf.installOffering, self.offering, None)


    def test_getInstalledOfferingNames(self):
        """
        L{getInstalledOfferingNames} should list the names of offerings
        installed on the given site store.
        """
        self.assertEquals(offering.getInstalledOfferingNames(self.store),
                          ['mantissa-base'])

        self.test_installOffering()

        installed = offering.getInstalledOfferingNames(self.store)
        installed.sort()
        expected = [u"mantissa-base", u"test_offering"]
        expected.sort()
        self.assertEquals(installed, expected)


    def test_getInstalledOfferings(self):
        """
        getInstalledOfferings should return a mapping of offering name to
        L{Offering} object for each installed offering on a given site store.
        """
        self.assertEquals(offering.getInstalledOfferings(self.store),
                          {baseOffering.name: baseOffering})
        self.test_installOffering()
        self.assertEquals(offering.getInstalledOfferings(self.store),
                          {baseOffering.name: baseOffering,
                           self.offering.name: self.offering})


    def test_isAppStore(self):
        """
        isAppStore returns True for stores with offerings installed on them,
        False otherwise.
        """
        conf = self.adminAccount.avatars.open().findUnique(
            offering.OfferingConfiguration)
        conf.installOffering(self.offering, None)
        app = self.userbase.accountByAddress(self.offering.name, None)
        self.failUnless(offering.isAppStore(app.avatars.open()))
        self.failIf(offering.isAppStore(self.adminAccount.avatars.open()))



class FakeOfferingTechnician(object):
    """
    In-memory only implementation of the offering inspection/installation API.

    @ivar installedOfferings: A mapping from offering names to corresponding
        L{IOffering} providers which have been passed to C{installOffering}.
    """
    implements(ixmantissa.IOfferingTechnician)

    def __init__(self):
        self.installedOfferings = {}


    def installOffering(self, offering):
        """
        Add the given L{IOffering} provider to the list of installed offerings.
        """
        self.installedOfferings[offering.name] = offering


    def getInstalledOfferings(self):
        """
        Return a copy of the internal installed offerings mapping.
        """
        return self.installedOfferings.copy()


    def getInstalledOfferingNames(self):
        """
        Return the names from the internal installed offerings mapping.
        """
        return self.installedOfferings.keys()



class OfferingTechnicianTestMixin:
    """
    L{unittest.TestCase} mixin which defines unit tests for classes which
    implement L{IOfferingTechnician}.

    @ivar offerings: A C{list} of L{Offering} instances which will be installed
        by the tests this mixin defines.
    """
    offerings = [
        offering.Offering(u'an offering', None, [], [], [], [], []),
        offering.Offering(u'another offering', None, [], [], [], [], [])]

    def createTechnician(self):
        """
        @return: An L{IOfferingTechnician} provider which will be tested.
        """
        raise NotImplementedError(
            "%r did not implement createTechnician" % (self.__class__,))


    def test_interface(self):
        """
        L{createTechnician} returns an instance of a type which declares that
        it implements L{IOfferingTechnician} and has all of the methods and
        attributes defined by the interface.
        """
        technician = self.createTechnician()
        technicianType = type(technician)
        self.assertTrue(
            ixmantissa.IOfferingTechnician.implementedBy(technicianType))
        self.assertTrue(
            verifyClass(ixmantissa.IOfferingTechnician, technicianType))
        self.assertTrue(
            verifyObject(ixmantissa.IOfferingTechnician, technician))


    def test_getInstalledOfferingNames(self):
        """
        The L{ixmantissa.IOfferingTechnician.getInstalledOfferingNames}
        implementation returns a C{list} of C{unicode} strings, each element
        giving the name of an offering which has been installed.
        """
        offer = self.createTechnician()
        self.assertEqual(offer.getInstalledOfferingNames(), [])

        expected = []
        for dummyOffering in self.offerings:
            offer.installOffering(dummyOffering)
            expected.append(dummyOffering.name)
            expected.sort()
            installed = offer.getInstalledOfferingNames()
            installed.sort()
            self.assertEqual(installed, expected)


    def test_getInstalledOfferings(self):
        """
        The L{ixmantissa.IOfferingTechnician.getInstalledOfferings}
        implementation returns a C{dict} mapping C{unicode} offering names to
        the corresponding L{IOffering} providers.
        """
        offer = self.createTechnician()
        self.assertEqual(offer.getInstalledOfferings(), {})

        expected = {}
        for dummyOffering in self.offerings:
            offer.installOffering(dummyOffering)
            expected[dummyOffering.name] = dummyOffering
            self.assertEqual(offer.getInstalledOfferings(), expected)



class OfferingAdapterTests(unittest.TestCase, OfferingTechnicianTestMixin):
    """
    Tests for L{offering.OfferingAdapter}.
    """
    def setUp(self):
        """
        Hook offering plugin discovery so that only the fake offerings the test
        wants exist.
        """
        self.origGetOfferings = offering.getOfferings
        offering.getOfferings = self.getOfferings


    def tearDown(self):
        """
        Restore the original L{getOfferings} function.
        """
        offering.getOfferings = self.origGetOfferings


    def getOfferings(self):
        """
        Return some dummy offerings, as defined by C{self.offerings}.
        """
        return self.offerings


    def createTechnician(self):
        """
        Create an L{offering.OfferingAdapter}.
        """
        store = Store()
        technician = offering.OfferingAdapter(store)
        return technician



class FakeOfferingTechnicianTests(unittest.TestCase, OfferingTechnicianTestMixin):
    """
    Tests (ie, verification) for L{FakeOfferingTechnician}.
    """
    def createTechnician(self):
        """
        Create a L{FakeOfferingTechnician}.
        """
        return FakeOfferingTechnician()



class BaseOfferingTests(unittest.TestCase):
    """
    Tests for the base Mantissa offering,
    L{xmantissa.plugins.baseoff.baseOffering}.
    """
    def test_interface(self):
        """
        C{baseOffering} provides L{IOffering}.
        """
        self.assertTrue(verifyObject(ixmantissa.IOffering, baseOffering))


    def test_staticContentPath(self):
        """
        C{baseOffering.staticContentPath} gives the location of a directory
        which has I{mantissa.css} in it.
        """
        self.assertTrue(
            baseOffering.staticContentPath.child('mantissa.css').exists())


    def _siteRequirementTest(self, offering, cls):
        """
        Verify that installing C{offering} results in an instance of the given
        Item subclass being installed as a powerup for IProtocolFactoryFactory.
        """
        store = Store()
        ixmantissa.IOfferingTechnician(store).installOffering(offering)

        factories = list(store.powerupsFor(ixmantissa.IProtocolFactoryFactory))
        for factory in factories:
            if isinstance(factory, cls):
                break
        else:
            self.fail("No instance of %r in %r" % (cls, factories))


    def test_siteConfiguration(self):
        """
        L{SiteConfiguration} powers up a store for L{IProtocolFactoryFactory}
        when L{baseOffering} is installed on that store.
        """
        self._siteRequirementTest(baseOffering, SiteConfiguration)


    def test_ampConfiguration(self):
        """
        L{AMPConfiguration} powers up a store for L{IProtocolFactoryFactory}
        when L{ampOffering} is installed on that store.
        """
        self._siteRequirementTest(ampOffering, AMPConfiguration)
