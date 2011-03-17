from zope.interface import implements

from twisted.trial.unittest import TestCase
from twisted.internet import defer

from epsilon.structlike import record

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer
from axiom.substore import SubStore
from axiom.dependency import installOn
from axiom.plugins.axiom_plugins import Create
from axiom.plugins.mantissacmd import Mantissa

from nevow.athena import LiveElement
from nevow import rend
from nevow.rend import WovenContext
from nevow.testutil import FakeRequest
from nevow.inevow import IRequest, IResource

from xmantissa.ixmantissa import (
    ITemplateNameResolver, ISiteURLGenerator, IWebViewer, INavigableElement)

from xmantissa.offering import InstalledOffering
from xmantissa.webtheme import theThemeCache
from xmantissa.webnav import Tab
from xmantissa.sharing import (getSelfRole, getAuthenticatedRole,
                               getPrimaryRole)

from xmantissa.webapp import (
    PrivateApplication, _AuthenticatedWebViewer, _PrivateRootPage,
    GenericNavigationAthenaPage)

from xmantissa.test.test_publicweb import AuthenticatedNavigationTestMixin

from xmantissa.test.fakes import (
    FakeTheme, FakeCustomizableElementModel, FakeLoader,
    ElementViewForFakeModelWithTheme, FakeElementModelWithTheme)

from xmantissa.test.test_webshell import WebViewerTestMixin


class AuthenticatedWebViewerTests(WebViewerTestMixin, TestCase):
    """
    Tests for L{_AuthenticatedWebViewer}.
    """

    def setupPageFactory(self):
        """
        Create the page factory used by the tests.
        """
        self.privapp = self.adminStore.findUnique(PrivateApplication)
        self.pageFactory = _AuthenticatedWebViewer(self.privapp)


    def assertPage(self, page):
        """
        Fail if the given object is not a nevow L{rend.Page} (or if it is an
        L{LivePage}). Also fail if the username is wrong.
        """
        WebViewerTestMixin.assertPage(self, page)
        self.assertEqual(page.username, u'admin@localhost')


    def assertLivePage(self, page):
        """
        Fail if the given object is not a L{MantissaLivePage}, or if the
        username is wrong.
        """
        WebViewerTestMixin.assertLivePage(self, page)
        self.assertEqual(page.username, u'admin@localhost')



    def test_docFactoryFromFragmentNameWithPreference(self):
        """
        When an L{INavigableFragment} provider provides a C{fragmentName}
        attribute, the theme to load it should be discovered according to the
        user's preference.
        """
        preferredDocFactory = FakeLoader('good')
        otherDocFactory = FakeLoader('bad')
        fn = ElementViewForFakeModelWithTheme.fragmentName
        self.stubThemeList(
            [FakeTheme(u'alpha', {fn: otherDocFactory}),
             FakeTheme(u'beta', {fn: preferredDocFactory})])
        self.privapp.preferredTheme = u'beta'
        elementable = FakeElementModelWithTheme()
        result = self.pageFactory.wrapModel(elementable)
        self.assertEqual(result.fragment.docFactory, preferredDocFactory)


    def test_customizableCustomizeFor(self):
        """
        L{INavigableFragment} providers who have a 'customizeFor' method will
        have it called with a username when they are wrapped for authenticated
        rendering.
        """
        elementable = FakeCustomizableElementModel()
        result = self.pageFactory.wrapModel(elementable)
        self.assertEqual(elementable.username, u'admin@localhost')


    def test_roleInMyStore(self):
        """
        L{_AuthenticatedWebViewer} should always return the 'self' role for
        users looking at their own stores.
        """
        role = getSelfRole(self.adminStore)
        self.assertIdentical(self.pageFactory.roleIn(self.adminStore),
                             role)


    def test_roleInSomebodyElsesStoreWhoDoesntKnowMe(self):
        """
        L{_AuthenticatedWebViewer} should return the authenticated role for
        users with no specific role to map.
        """
        someStore = self.loginSystem.addAccount(
            u'someguy', u'localhost', u'asdf').avatars.open()
        role = getAuthenticatedRole(someStore)
        self.assertIdentical(self.pageFactory.roleIn(someStore),
                             role)


    def test_roleInSomebodyElsesStoreDoesKnowMe(self):
        """
        L{_AuthenticatedWebViewer} should return the authenticated role for
        users with no specific role to map.
        """
        someStore = self.loginSystem.addAccount(
            u'someguy', u'localhost', u'asdf').avatars.open()
        role = getPrimaryRole(someStore, u'admin@localhost', True)
        self.assertIdentical(self.pageFactory.roleIn(someStore),
                             role)



class FakeResourceItem(Item):
    unused = integer()
    implements(IResource)

class FakeModelItem(Item):
    unused = integer()


class WebIDLocationTest(TestCase):

    def setUp(self):
        store = Store()
        ss = SubStore.createNew(store, ['test']).open()
        self.pa = PrivateApplication(store=ss)
        installOn(self.pa, ss)
        self.webViewer = IWebViewer(ss)

    def test_powersUpTemplateNameResolver(self):
        """
        L{PrivateApplication} implements L{ITemplateNameResolver} and should
        power up the store it is installed on for that interface.
        """
        self.assertIn(
            self.pa,
            self.pa.store.powerupsFor(ITemplateNameResolver))


    def test_suchWebID(self):
        """
        Verify that retrieving a webID gives the correct resource.
        """
        i = FakeResourceItem(store=self.pa.store)
        wid = self.pa.toWebID(i)
        ctx = FakeRequest()
        res = self.pa.createResourceWith(self.webViewer)
        self.assertEqual(res.locateChild(ctx, [wid]),
                         (i, []))


    def test_noSuchWebID(self):
        """
        Verify that non-existent private URLs generate 'not found' responses.
        """
        ctx = FakeRequest()
        for segments in [
            # something that looks like a valid webID
            ['0000000000000000'],
            # something that doesn't
            ["nothing-here"],
            # more than one segment
            ["two", "segments"]]:
            res = self.pa.createResourceWith(self.webViewer)
            self.assertEqual(res.locateChild(ctx, segments),
                             rend.NotFound)


    def test_webIDForFragment(self):
        """
        Retrieving a webID that specifies a fragment gives the correct
        resource.
        """
        class FakeView(record("model")):
            "A fake view that wraps a FakeModelItem."

        class FakeWebViewer(object):
            def wrapModel(self, model):
                return FakeView(model)

        i = FakeModelItem(store=self.pa.store)
        wid = self.pa.toWebID(i)
        ctx = FakeRequest()
        res = self.pa.createResourceWith(FakeWebViewer())
        child, segs = res.locateChild(ctx, [wid])
        self.assertIsInstance(child, FakeView)
        self.assertIdentical(child.model, i)



class TestElement(LiveElement):
    def head(self):
        pass

    def locateChild(self, ctx, segs):
        if segs[0] == 'child-of-fragment':
            return ('I AM A CHILD OF THE FRAGMENT', segs[1:])
        return rend.NotFound


class TestClientFactory(object):
    """
    Dummy L{LivePageFactory}.

    @ivar magicSegment: The segment for which to return L{returnValue} from
    L{getClient}.
    @type magicSegment: C{str}

    @ivar returnValue: The value to return from L{getClient} when it is passed
    L{magicSegment}.
    @type returnValue: C{str}.
    """
    def __init__(self, magicSegment, returnValue):
        self.magicSegment = magicSegment
        self.returnValue = returnValue


    def getClient(self, seg):
        if seg == self.magicSegment:
            return self.returnValue


class GenericNavigationAthenaPageTests(TestCase,
                                       AuthenticatedNavigationTestMixin):
    """
    Tests for L{GenericNavigationAthenaPage}.
    """
    def setUp(self):
        """
        Set up a site store, user store, and page instance to test with.
        """
        self.siteStore = Store(filesdir=self.mktemp())
        def siteStoreTxn():
            Mantissa().installSite(self.siteStore, u"localhost", u"", False)

            self.userStore = SubStore.createNew(
                self.siteStore, ['child', 'lookup']).open()
        self.siteStore.transact(siteStoreTxn)

        def userStoreTxn():
            self.privateApp = PrivateApplication(store=self.userStore)
            installOn(self.privateApp, self.userStore)

            self.navpage = self.createPage(None)
        self.userStore.transact(userStoreTxn)


    def createPage(self, username):
        """
        Create a L{GenericNavigationAthenaPage} for the given user.
        """
        return GenericNavigationAthenaPage(
            self.privateApp,
            TestElement(),
            self.privateApp.getPageComponents(),
            username)


    def rootURL(self, request):
        """
        Return the root URL as reported by C{self.website}.
        """
        return ISiteURLGenerator(self.siteStore).rootURL(request)


    def test_childLookup(self):
        """
        L{GenericNavigationAthenaPage} should delegate to its fragment and its
        L{LivePageFactory} when it cannot find a child itself.
        """
        self.navpage.factory = tcf = TestClientFactory(
            'client-of-livepage', 'I AM A CLIENT OF THE LIVEPAGE')

        self.assertEqual(self.navpage.locateChild(None,
                                                 ('child-of-fragment',)),
                         ('I AM A CHILD OF THE FRAGMENT', ()))
        self.assertEqual(self.navpage.locateChild(None,
                                             (tcf.magicSegment,)),
                        (tcf.returnValue, ()))


    def test_jsModuleLocation(self):
        """
        L{GenericNavigationAthenaPage.beforeRender} should should call
        L{xmantissa.website.MantissaLivePage.beforeRender}, which shares its
        Athena JavaScript module location with all other pages that use
        L{xmantissa.cachejs}, and provide links to /__jsmodule__/.
        """
        ctx = WovenContext()
        req = FakeRequest()
        ctx.remember(req, IRequest)
        self.navpage.beforeRender(ctx)
        urlObj = self.navpage.getJSModuleURL('Mantissa')
        self.assertEqual(urlObj.pathList()[0], '__jsmodule__')


    def test_beforeRenderDelegation(self):
        """
        L{GenericNavigationAthenaPage.beforeRender} should call
        C{beforeRender} on the wrapped fragment, if it's defined, and return
        its result.
        """
        contexts = []
        result = defer.succeed(None)
        def beforeRender(ctx):
            contexts.append(ctx)
            return result
        self.navpage.fragment.beforeRender = beforeRender
        ctx = WovenContext()
        ctx.remember(FakeRequest(), IRequest)
        self.assertIdentical(
            self.navpage.beforeRender(ctx), result)
        self.assertEqual(contexts, [ctx])



class PrivateApplicationTestCase(TestCase):
    """
    Tests for L{PrivateApplication}.
    """
    def setUp(self):
        self.siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.siteStore, u"example.com", u"", False)

        self.userAccount = Create().addAccount(
            self.siteStore, u'testuser', u'example.com', u'password')
        self.userStore = self.userAccount.avatars.open()

        self.privapp = PrivateApplication(store=self.userStore)
        installOn(self.privapp, self.userStore)
        self.webViewer = IWebViewer(self.userStore)


    def test_createResourceUsername(self):
        """
        L{PrivateApplication.createResourceWith} should figure out the
        right username and pass it to L{_PrivateRootPage}.
        """
        rootPage = self.privapp.createResourceWith(self.webViewer)
        self.assertEqual(rootPage.username, u'testuser@example.com')


    def test_getDocFactory(self):
        """
        L{PrivateApplication.getDocFactory} finds a document factory for
        the specified template name from among the installed themes.
        """
        # Get something from the Mantissa theme
        self.assertNotIdentical(self.privapp.getDocFactory('shell'), None)

        # Get rid of the Mantissa offering and make sure the template is no
        # longer found.
        self.siteStore.query(InstalledOffering).deleteFromStore()

        # And flush the cache. :/ -exarkun
        theThemeCache.emptyCache()

        self.assertIdentical(self.privapp.getDocFactory('shell'), None)


    def test_powersUpWebViewer(self):
        """
        L{PrivateApplication} should provide an indirected L{IWebViewer}
        powerup, and its indirected powerup should be the default provider of
        that interface.
        """
        webViewer = IWebViewer(self.privapp.store)
        self.assertIsInstance(webViewer, _AuthenticatedWebViewer)
        self.assertIdentical(webViewer._privateApplication, self.privapp)


    def test_producePrivateRoot(self):
        """
        L{PrivateApplication.produceResource} should return a
        L{_PrivateRootPage} when asked for '/private'.
        """
        rsrc, segments = self.privapp.produceResource(FakeRequest(),
                                                     tuple(['private']), None)
        self.assertIsInstance(rsrc, _PrivateRootPage)
        self.assertEqual(segments, ())


    def test_produceRedirect(self):
        """
        L{_PrivateRootPage.produceResource} should return a redirect to
        '/private/<default-private-id>' when asked for '/'.

        This is a bad way to do it, because it isn't optional; all logged-in
        users are instantly redirected to their private page, even if the
        application has something interesting to display. See ticket #2708 for
        details.
        """
        item = FakeModelItem(store=self.userStore)
        class TabThingy(object):
            implements(INavigableElement)
            def getTabs(self):
                return [Tab("supertab", item.storeID, 1.0)]
        tt = TabThingy()
        self.userStore.inMemoryPowerUp(tt, INavigableElement)
        rsrc, segments = self.privapp.produceResource(
            FakeRequest(), tuple(['']), None)
        self.assertIsInstance(rsrc, _PrivateRootPage)
        self.assertEqual(segments, tuple(['']))
        url, newSegs = rsrc.locateChild(FakeRequest(), ('',))
        self.assertEqual(newSegs, ())
        req = FakeRequest()
        target = self.privapp.linkTo(item.storeID)
        self.assertEqual('/'+url.path, target)


    def test_produceNothing(self):
        """
        L{_PrivateRootPage.produceResource} should return None when asked for a
        resources other than '/' and '/private'.
        """
        self.assertIdentical(
            self.privapp.produceResource(FakeRequest(),
                                        tuple(['hello', 'world']),
                                        None),
            None)


    def test_privateRootHasWebViewer(self):
        """
        The L{_PrivateRootPage} returned from
        L{PrivateApplication.produceResource} should refer to an
        L{IWebViewer}.
        """
        webViewer = object()
        rsrc, segments = self.privapp.produceResource(
            FakeRequest(),
            tuple(['private']), webViewer)
        self.assertIdentical(webViewer,
                             rsrc.webViewer)
