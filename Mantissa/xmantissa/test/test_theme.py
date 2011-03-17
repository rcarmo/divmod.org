from zope.interface import implements
from zope.interface import classProvides

from twisted.trial.unittest import TestCase
from twisted.python.reflect import qual
from twisted.python.util import sibpath
from twisted.python.filepath import FilePath, InsecurePath

from nevow.athena import LivePage
from nevow.loaders import stan, xmlstr
from nevow.tags import (
    html, head, body, invisible, directive)
from nevow.context import WovenContext
from nevow.testutil import FakeRequest
from nevow.flat import flatten
from nevow.inevow import IRequest

from nevow.athena import LiveFragment

from axiom.item import Item
from axiom.attributes import integer
from axiom.store import Store
from axiom.substore import SubStore
from axiom.dependency import installOn
from axiom.plugins.mantissacmd import Mantissa

from xmantissa.ixmantissa import (
    ITemplateNameResolver, IOfferingTechnician, ISiteURLGenerator)

from xmantissa import webtheme
from xmantissa.webtheme import (
    getInstalledThemes, MantissaTheme, ThemedFragment,
    ThemedElement, ThemedDocumentFactory,
    SiteTemplateResolver, XHTMLDirectoryTheme)

from xmantissa.offering import Offering, installOffering
from xmantissa.plugins.baseoff import baseOffering

from xmantissa.publicweb import PublicAthenaLivePage
from xmantissa.webapp import GenericNavigationAthenaPage, _PageComponents

from xmantissa.test.test_offering import FakeOfferingTechnician
from xmantissa.test.validation import XHTMLDirectoryThemeTestsMixin


class ThemedDocumentFactoryTests(TestCase):
    """
    Tests for the automatic document factory descriptor,
    L{ThemedDocumentFactory}.
    """
    def test_getter(self):
        """
        Retrieving the value of a L{ThemedDocumentFactory} descriptor should
        cause an L{ITemplateNameResolver} to be requested from the supplied
        callable and a loader for the template for the fragment name the
        descriptor was created with to be created and returned.
        """
        _docFactory = object()
        loadAttempts = []
        fragmentName = 'abc'
        class Dummy(object):
            class StubResolver(object):
                classProvides(ITemplateNameResolver)
                def getDocFactory(name):
                    loadAttempts.append(name)
                    return _docFactory
                getDocFactory = staticmethod(getDocFactory)
            docFactory = ThemedDocumentFactory(fragmentName, 'StubResolver')
        self.assertIdentical(Dummy().docFactory, _docFactory)
        self.assertEqual(loadAttempts, [fragmentName])



class FakeTheme:
    """
    Stub theme object for template-loader tests.
    """
    implements(ITemplateNameResolver)
    def __init__(self, name, priority):
        self.name = name
        self.priority = priority

    def getDocFactory(self, n, default):
        """
        Doesn't have to return anything meaningful, just something
        recognizable for assertions.
        """
        return [self.name, n]


class FakeOffering:
    def __init__(self, name, priority):
        self.themes = [FakeTheme(name, priority)]

class WebThemeTestCase(TestCase):
    def _render(self, element):
        """
        Put the given L{IRenderer} provider into an L{athena.LivePage} and
        render it.  Return a Deferred which fires with the request object used
        which is an instance of L{nevow.testutil.FakeRequest}.
        """
        p = LivePage(
            docFactory=stan(
                html[
                    head(render=directive('liveglue')),
                    body[
                        invisible(render=lambda ctx, data: element)]]))
        element.setFragmentParent(p)

        ctx = WovenContext()
        req = FakeRequest()
        ctx.remember(req, IRequest)

        d = p.renderHTTP(ctx)
        def rendered(ign):
            p.action_close(None)
            return req
        d.addCallback(rendered)
        return d


    def test_getAllThemesPrioritization(self):
        """
        Test that the L{xmantissa.webtheme.getAllThemes} function returns
        L{ITemplateNameResolver} providers from the installed
        L{xmantissa.ixmantissa.IOffering} plugins in priority order.
        """
        lastPriority = None
        for theme in webtheme.getAllThemes():
            if lastPriority is None:
                lastPriority = theme.priority
            else:
                self.failIf(
                    theme.priority > lastPriority,
                    "Theme out of order: %r" % (theme,))
                lastPriority = theme.priority


    def test_getInstalledThemes(self):
        """
        Test that only themes which belong to offerings installed on a
        particular store are returned by
        L{xmantissa.webtheme.getInstalledThemes}.
        """
        s = Store()
        self.assertEquals(getInstalledThemes(s), [])

        installOffering(s, baseOffering, {})

        installedThemes = getInstalledThemes(s)
        self.assertEquals(len(installedThemes), 1)
        self.failUnless(isinstance(installedThemes[0], MantissaTheme))


    def _defaultThemedRendering(self, cls):
        class ThemedSubclass(cls):
            pass
        d = self._render(ThemedSubclass())
        def rendered(req):
            self.assertIn(
                qual(ThemedSubclass),
                req.v)
            self.assertIn(
                'specified no <code>fragmentName</code> attribute.',
                req.v)
        d.addCallback(rendered)
        return d


    def test_themedFragmentDefaultRendering(self):
        """
        Test that a ThemedFragment which does not override fragmentName is
        rendered with some debugging tips.
        """
        return self._defaultThemedRendering(ThemedFragment)


    def test_themedElementDefaultRendering(self):
        """
        Test that a ThemedElement which does not override fragmentName is
        rendered with some debugging tips.
        """
        return self._defaultThemedRendering(ThemedElement)



class MantissaThemeTests(XHTMLDirectoryThemeTestsMixin, TestCase):
    """
    Stock L{XHTMLDirectoryTheme} tests applied to L{baseOffering} and its
    theme.
    """
    offering = baseOffering
    theme = offering.themes[0]



CUSTOM_MSG = xmlstr('<div>Athena unsupported here</div>')
BASE_MSG =  file(sibpath(__file__,
                         "../themes/base/athena-unsupported.html")
                 ).read().strip()



class StubThemeProvider(Item):
    """
    Trivial implementation of a theme provider, for testing that custom
    Athena-unsupported pages can be used.
    """
    _attribute = integer(doc="exists to pacify Axiom's hunger for attributes")
    implements(ITemplateNameResolver)
    powerupInterfaces = (ITemplateNameResolver,)
    def getDocFactory(self, name):
        """
        Return the page indicating Athena isn't available, if requested.
        """
        if name == 'athena-unsupported':
            return CUSTOM_MSG



class AthenaUnsupported(TestCase):
    """
    Tests for proper treatment of browsers that don't support Athena.
    """
    def setUp(self):
        self.siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.siteStore, u"example.com", u"", False)


    def test_publicPage(self):
        """
        Test that L{publicpage.PublicAthenaLivePage} supports themeing of
        Athena's unsupported-browser page.
        """
        stp = StubThemeProvider(store=self.siteStore)
        installOn(stp, self.siteStore)
        p = PublicAthenaLivePage(self.siteStore, None)
        self.assertEqual(p.renderUnsupported(None),
                         flatten(CUSTOM_MSG))


    def test_navPage(self):
        """
        Test that L{webapp.GenericNavigationLivePage} supports theming of
        Athena's unsupported-browser page based on an L{ITemplateNameResolver}
        installed on the viewing user's store.
        """
        subStore = SubStore.createNew(
            self.siteStore, ['athena', 'unsupported']).open()
        stp = StubThemeProvider(store=subStore)
        installOn(stp, subStore)
        p = GenericNavigationAthenaPage(stp,
                                        LiveFragment(),
                                        _PageComponents([], None, None,
                                                        None, None),
                                        None)
        self.assertEqual(p.renderUnsupported(None),
                         flatten(CUSTOM_MSG))



class Loader(TestCase):
    def setUp(self):
        self._getAllThemes = webtheme.getAllThemes
        self.gATcalled = 0
        def fakeGetAllThemes():
            self.gATcalled += 1
            return [FakeTheme('foo', 7),
                    FakeTheme('baz', 2)]
        webtheme._loaderCache.clear()
        webtheme.getAllThemes = fakeGetAllThemes

    def tearDown(self):
        webtheme.getAllThemes = self._getAllThemes

    def test_getLoader(self):
        """
        getLoader should search available themes for the named
        template and return it.
        """
        self.assertEquals(webtheme.getLoader('template'),
                          ['foo', 'template'])

    def test_getLoaderCaching(self):
        """
        getLoader should return identical loaders for equal arguments.
        """
        self.assertIdentical(webtheme.getLoader('template'),
                             webtheme.getLoader('template'))
        self.assertEqual(self.gATcalled, 1)



class TestSiteTemplateResolver(TestCase):
    """
    Tests for L{SiteTemplateResolver}
    """
    def setUp(self):
        """
        Create a L{Store} with a fake L{IOfferingTechnician} powerup which
        allows fine-grained control of template name resolution.
        """
        self.offeringTech = FakeOfferingTechnician()
        self.store = Store()
        self.store.inMemoryPowerUp(self.offeringTech, IOfferingTechnician)
        self.siteResolver = SiteTemplateResolver(self.store)


    def getDocFactoryWithoutCaching(self, templateName):
        """
        Use C{self.siteResolver} to get a loader for the named template,
        flushing the template cache first in order to make the result reflect
        any changes which in offering or theme availability which may have
        happened since the last call.
        """
        webtheme.theThemeCache.emptyCache()
        return self.siteResolver.getDocFactory(templateName)


    def test_getDocFactory(self):
        """
        L{SiteTemplateResolver.getDocFactory} should return only installed
        themes for its store.
        """
        class FakeTheme(object):
            priority = 0

            def getDocFactory(self, templateName, default=None):
                if templateName == 'shell':
                    return object()
                return default

        self.assertIdentical(self.getDocFactoryWithoutCaching('shell'), None)
        self.offeringTech.installOffering(
            Offering(
                u'an offering', None, [], [], [], [], [FakeTheme()]))
        self.assertNotIdentical(self.getDocFactoryWithoutCaching('shell'), None)



class XHTMLDirectoryThemeTests(TestCase):
    """
    Tests for L{XHTMLDirectoryTheme}.
    """
    def setUp(self):
        """
        Set up the store, a temporary test dir and a theme for the tests.
        """
        self.store = Store()
        self.testDir = FilePath(self.mktemp())
        self.testDir.makedirs()
        self.theme = XHTMLDirectoryTheme(
            'testtheme',
            directoryName=self.testDir.path)


    def test_directoryAttribute(self):
        """
        L{XHTMLDirectoryTheme} should have a directory attribute of type
        L{twisted.python.filepath.FilePath}.
        """
        self.assertEqual(self.theme.directory, self.testDir)
        self.assertEqual(self.theme.directory.path, self.theme.directoryName)


    def test_childFragmentsInGetDocFactory(self):
        """
        L{XHTMLDirectoryTheme.getDocFactory} should handle subdirectories
        sanely, without exposing parent directories.
        """
        fragmentName = 'dir/file'
        child = self.testDir.child('dir')
        child.makedirs()
        child.child('file.html').touch()
        resolvedTemplate = self.theme.getDocFactory(fragmentName)
        foundPath = FilePath(resolvedTemplate.template)
        expectedPath = FilePath(
            "%s/%s.html" % (self.theme.directoryName, fragmentName))
        self.assertEqual(foundPath, expectedPath)
        self.assertRaises(InsecurePath, self.theme.getDocFactory,
                          '../insecure/')


    def test_noStylesheetLocation(self):
        """
        L{XHTMLDirectoryTheme.head} returns C{None} if I{stylesheetLocation} is
        C{None}.
        """
        self.assertIdentical(self.theme.head(None, None), None)


    def test_stylesheetLocation(self):
        """
        L{XHTMLDirectoryTheme.head} returns a link tag which gives the location
        of the stylesheet given by I{stylesheetLocation} if there is one.
        """
        siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(siteStore, u"example.com", u"", False)
        site = ISiteURLGenerator(siteStore)

        self.theme.stylesheetLocation = ['foo', 'bar']
        request = FakeRequest()
        link = self.theme.head(request, site)
        self.assertEqual(link.tagName, 'link')
        self.assertEqual(link.attributes['rel'], 'stylesheet')
        self.assertEqual(link.attributes['type'], 'text/css')
        self.assertEqual(
            site.rootURL(request).child('foo').child('bar'),
            link.attributes['href'])



class TestThemeCache(TestCase):
    """
    some tests for L{ThemeCache}.
    """
    def setUp(self):
        """
        Replace L{getOfferings} with a mock method returning some fake
        offerings.
        """
        self._getOfferings = webtheme.getOfferings
        self.called = 0
        def fakeGetOfferings():
            self.called += 1
            return [FakeOffering('foo', 7),
                    FakeOffering('baz', 2),
                    FakeOffering('boz', 5)]

        webtheme.getOfferings = fakeGetOfferings

    def tearDown(self):
        """
        Reset L{getOfferings} to its original value.
        """
        webtheme.getOfferings = self._getOfferings


    def test_getAllThemes(self):
        """
        C{getAllThemes} should collect themes from available
        offerings, and only call C{getOfferings} once no matter how
        many times it's called.
        """
        tc = webtheme.ThemeCache()
        ths = tc.getAllThemes()
        self.assertEqual([theme.name for theme in ths],
                         ['foo', 'boz', 'baz'])
        tc.getAllThemes()
        self.assertEqual(self.called, 1)

    def test_realGetAllThemes(self):
        """
        C{_realGetAllThemes} should collect themes from available offerings.
        """
        tc = webtheme.ThemeCache()
        ths = tc.getAllThemes()
        self.assertEqual([theme.name for theme in ths],
                         ['foo', 'boz', 'baz'])


    def test_clearThemeCache(self):
        """
        C{emptyCache} should invalidate the cache contents for both types.
        """
        tc = webtheme.ThemeCache()
        s = Store()
        tc.getAllThemes()
        tc.getInstalledThemes(s)
        tc.emptyCache()
        self.assertEqual(tc._getAllThemesCache, None)
        self.assertEqual(len(tc._getInstalledThemesCache), 0)
