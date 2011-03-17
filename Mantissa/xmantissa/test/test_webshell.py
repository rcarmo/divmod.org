
"""
Tests for common functionality between L{IWebViewer} implementations.

No runnable tests are currently defined here; the mixin defined here is
imported from test_webapp (for the authenticated view) and test_publicweb (for
the anonymous view).
"""

from axiom.userbase import LoginSystem
from axiom.store import Store

from nevow.rend import Page, NotFound
from nevow.page import deferflatten, Element
from nevow.loaders import stan

from nevow.athena import LivePage
from nevow import tags
from nevow.inevow import IRequest
from nevow.context import WovenContext
from nevow.testutil import FakeRequest

from xmantissa.error import CouldNotLoadFromThemes
from xmantissa.ixmantissa import ISiteURLGenerator
from xmantissa.webtheme import theThemeCache

from xmantissa.test.fakes import (
    FakeLoader, FakeTheme, FakeFragmentModel, FakeLiveElementModel,
    FakeLiveFragmentModel, FakeModel, ResourceViewForFakeModel,
    FakeElementModel, FakeElementModelWithTheme, FakeElementModelWithDocFactory,
    FakeElementModelWithThemeAndDocFactory, ElementViewForFakeModelWithTheme,
    FakeElementModelWithLocateChildView, FakeElementModelWithHead,
    ElementViewForFakeModelWithThemeAndDocFactory, __file__ as fakesfile)

from xmantissa.website import MantissaLivePage
from axiom.plugins.mantissacmd import Mantissa

class WebViewerTestMixin(object):
    """
    Tests for implementations of L{IWebViewer}.
    """

    def setUp(self):
        """
        Create a site store containing an admin user, then do
        implementation-specific setup.
        """
        self.siteStore = Store(filesdir=self.mktemp())
        m = Mantissa()
        m.installSite(self.siteStore, u"localhost", u"", False)
        m.installAdmin(self.siteStore, u'admin', u'localhost', u'asdf')
        self.loginSystem = self.siteStore.findUnique(LoginSystem)
        self.adminStore = self.loginSystem.accountByAddress(
            u'admin', u'localhost').avatars.open()
        self.setupPageFactory()


    def assertPage(self, page):
        """
        Fail if the given object is not a nevow L{rend.Page} (or if it is an
        L{LivePage}).
        """
        self.assertIsInstance(page, Page)
        self.assertNotIsInstance(page, LivePage)


    def assertLivePage(self, page):
        """
        Fail if the given object is not a L{MantissaLivePage}
        """
        self.assertIsInstance(page, MantissaLivePage)


    def test_wrapResource(self):
        """
        An object adaptable to L{IResource} has its IResource adapter returned
        when wrapModel is called with it.
        """
        resourceable = FakeModel()
        result = self.pageFactory.wrapModel(resourceable)
        self.assertIsInstance(result, ResourceViewForFakeModel)


    def test_wrapElement(self):
        """
        An object adaptable to L{INavigableFragment}, whose adapter is an
        L{Element}, is wrapped in a shell page (containing navigation for
        the current user) when wrapModel is called on it.
        """
        elementable = FakeElementModel()
        result = self.pageFactory.wrapModel(elementable)
        self.assertPage(result)
        self.assertEqual(result.fragment.model, elementable)


    def test_wrapFragment(self):
        """
        An object adaptable to L{INavigableFragment}, whose adapter is a
        L{Fragment}, is wrapped in a shell page (containing navigation for
        the current user) when wrapModel is called on it.
        """
        fragmentable = FakeFragmentModel()
        result = self.pageFactory.wrapModel(fragmentable)
        self.assertPage(result)
        self.assertEqual(result.fragment.original, fragmentable)


    def test_wrapLiveElement(self):
        """
        An object adaptable to L{INavigableFragment}, whose adapter is a
        L{LiveElement}, is wrapped in a shell page (containing navigation for
        the current user) when wrapModel is called on it.
        """
        elementable = FakeLiveElementModel()
        result = self.pageFactory.wrapModel(elementable)
        self.assertLivePage(result)
        self.assertEqual(result.fragment.model, elementable)


    def test_wrapLiveFragment(self):
        """
        An object adaptable to L{INavigableFragment}, whose adapter is a
        L{LiveFragment}, is wrapped in a shell page (containing navigation for
        the current user) when wrapModel is called on it.
        """
        fragmentable = FakeLiveFragmentModel()
        result = self.assertWarns(
            DeprecationWarning,
            '[v0.10] LiveFragment has been superceded by LiveElement.',
            fakesfile,
            self.pageFactory.wrapModel, fragmentable)
        self.assertLivePage(result)
        self.assertEqual(result.fragment.original, fragmentable)


    def stubThemeList(self, themes):
        """
        Replace the global themes list with the given list of themes for the
        duration of this test.  This relies on the implementation details of
        the global theme cache; please update if the theme cache implementation
        changes.
        """
        theThemeCache._getInstalledThemesCache[self.siteStore] = themes
        self.addCleanup(theThemeCache.emptyCache)


    def test_docFactoryFromFragmentName(self):
        """
        If the L{INavigableFragment} provider provides a C{fragmentName}
        attribute, it should be looked up via the theme system and assigned to
        the C{docFactory} attribute of the L{INavigableFragment} provider.
        """
        fakeDocFactory = FakeLoader('fake')
        self.stubThemeList([FakeTheme('theme',
                    {ElementViewForFakeModelWithTheme.fragmentName:
                         fakeDocFactory})])
        elementable = FakeElementModelWithTheme()
        result = self.pageFactory.wrapModel(elementable)
        self.assertEqual(result.fragment.docFactory, fakeDocFactory)


    def test_dontThrowOutTheBabyWithTheBathwater(self):
        """
        If the L{INavigableFragment} provider provides a C{docFactory}
        attribute, neither lack of a C{fragmentName} attribute, a
        C{fragmentName} that is None, nor a C{fragmentName} for which there is
        no loader in any theme, should change its C{docFactory} to C{None}.
        """
        fakeDocFactory = FakeLoader('fake')
        self.stubThemeList([FakeTheme('theme', {})])
        model = FakeElementModelWithDocFactory(fakeDocFactory)
        modelWithFragmentName = FakeElementModelWithThemeAndDocFactory('wrong',
                                                                       fakeDocFactory)

        result = self.pageFactory.wrapModel(model)
        self.assertEqual(result.fragment.docFactory, fakeDocFactory)

        result = self.pageFactory.wrapModel(modelWithFragmentName)
        self.assertEqual(result.fragment.docFactory, fakeDocFactory)


    def test_noLoaderAnywhere(self):
        """
        If the L{INavigableFragment}provider provides no C{docFactory} or
        C{fragmentName} attribute, then L{_AuthenticatedWebViewer.wrapModel}
        should raise L{CouldNotLoadFromThemes}.
        """
        model = FakeElementModelWithThemeAndDocFactory(None, None)
        aFakeTheme = FakeTheme('fake', {})
        self.stubThemeList([aFakeTheme])
        exc = self.assertRaises(
            CouldNotLoadFromThemes, self.pageFactory.wrapModel, model)
        self.assertIsInstance(exc.element, ElementViewForFakeModelWithThemeAndDocFactory)
        self.assertIdentical(exc.element.model, model)
        self.assertEquals(exc.themes, [aFakeTheme])
        self.assertEquals(
            repr(exc),
            'CouldNotLoadFromThemes: %r (fragment name %r) has no docFactory. Searched these themes: %r' %
            (exc.element, exc.element.fragmentName, [aFakeTheme]))


    def test_navFragmentHasLocateChild(self, beLive=False):
        """
        The L{IResource} returned by L{IWebViewer.wrapModel} must have a
        C{locateChild} which forwards to its wrapped L{INavigableFragment}.
        """
        expectChild = object()
        elementable = FakeElementModelWithLocateChildView([expectChild], beLive=beLive)
        result = self.pageFactory.wrapModel(elementable)
        resultChild = result.locateChild(FakeRequest(), [''])
        self.assertIdentical(resultChild, expectChild)


    def test_navFragmentHasLiveLocateChild(self):
        """
        The same as L{test_navFragmentHasLiveLocateChild}, but for the Athena
        implementation of the resource adapters.
        """
        self.test_navFragmentHasLocateChild(True)


    def test_navFragmentHasNoChildMethods(self, beLive=False):
        """
        The L{IResource} returned by L{IWebViewer.wrapModel} must have a
        C{locateChild} which returns NotFound in the case where its wrapped
        L{INavigableFragment} does not have a C{locateChild} method.
        """
        if beLive:
            elementable = FakeLiveElementModel()
        else:
            elementable = FakeElementModel()
        result = self.pageFactory.wrapModel(elementable)
        resultChild = result.locateChild(FakeRequest(), [''])
        self.assertEqual(resultChild, NotFound)


    def test_navFragmentHasNoLiveChildMethods(self):
        """
        The same as L{test_navFragmentHasNoChildMethods} but for the Athena
        implementation of the resource adapters.
        """
        self.test_navFragmentHasNoChildMethods(True)


    def _renderHead(self, result):
        """
        Go through all the gyrations necessary to get the head contents
        produced by the page rendering process.
        """
        site = ISiteURLGenerator(self.siteStore)
        t = tags.invisible()
        ctx = WovenContext(tag=t)
        req = FakeRequest()
        ctx.remember(req, IRequest)
        expected = [th.head(req, site)
                    for th in self.pageFactory._preferredThemes()]
        head = result.render_head(ctx, None)
        return t, expected


    def test_renderHeadNoHeadMethod(self):
        """
        Rendering the <head> tag in the shell template for a non-athena
        L{INavigableFragment} without a C{head()} method should result in each
        theme adding its external content (stylesheets, etc) to the <head>.
        """
        elementable = FakeElementModel()
        result = self.pageFactory.wrapModel(elementable)
        t, expected = self._renderHead(result)
        self.assertStanEqual(list(t.children), expected)


    def test_renderHeadWithHeadMethod(self):
        """
        Rendering the <head> tag in the shell template for a non-athena
        L{INavigableFragment} with a C{head()} method should result in each
        theme adding its external content (stylesheets, etc) to the <head>,
        followed by the contents provided by the L{INavigableFragment}.
        """
        h = tags.div["some stuff"]
        model = FakeElementModelWithHead(h)
        result = self.pageFactory.wrapModel(model)
        t, expected = self._renderHead(result)
        self.assertStanEqual(list(t.children), expected + [h])


    def _instaString(self, x):
        """
        Convert a new-style-renderable thing into a string, raising an
        exception if any deferred rendering took place.
        """
        e = Element(docFactory=stan(x))
        l = []
        d = deferflatten(None, e, False, False, l.append)
        return ''.join(l)


    def assertStanEqual(self, stan1, stan2):
        """
        Assert that two chunks of Nevow-renderable stuff will result in the
        same XML.
        """
        a = self._instaString(stan1)
        b = self._instaString(stan2)
        self.assertEqual(a, b)
