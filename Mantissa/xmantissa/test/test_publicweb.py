# Copyright 2008 Divmod, Inc. See LICENSE file for details

from zope.interface import implements

from twisted.trial.unittest import TestCase
from twisted.trial.util import suppress as SUPPRESS
from twisted.python.usage import UsageError
from twisted.python.components import registerAdapter

from axiom.store import Store
from axiom.item import Item
from axiom.substore import SubStore
from axiom.userbase import LoginSystem
from axiom.attributes import boolean, integer, inmemory
from axiom.plugins.axiom_plugins import Create
from axiom.plugins.mantissacmd import Mantissa
from axiom.plugins.offeringcmd import SetFrontPage
from axiom.dependency import installOn

from axiom.test.util import CommandStubMixin

from nevow import rend, context, inevow
from nevow.inevow import IResource
from nevow.page import Element
from nevow.rend import NotFound
from nevow.flat import flatten
from nevow.tags import title, div, span, h1, h2
from nevow.testutil import FakeRequest

from xmantissa.ixmantissa import (
    IPublicPage, ITemplateNameResolver, INavigableElement, ISiteURLGenerator,
    IOfferingTechnician, INavigableFragment, ISiteRootPlugin, IWebViewer)
from xmantissa import signup
from xmantissa.website import APIKey, WebSite
from xmantissa.webapp import (PrivateApplication,
                              _AuthenticatedWebViewer)
from xmantissa.prefs import PreferenceAggregator
from xmantissa.port import SSLPort
from xmantissa.webnav import Tab
from xmantissa.offering import Offering, InstalledOffering, installOffering
from xmantissa.webtheme import theThemeCache
from xmantissa.sharing import shareItem, getEveryoneRole
from xmantissa.websharing import getDefaultShareID, UserIndexPage
from xmantissa.publicweb import (
    _AnonymousWebViewer, FrontPage, PublicAthenaLivePage,
    PublicNavAthenaLivePage, _PublicFrontPage, getLoader, AnonymousSite,
    _OfferingsFragment, _CustomizingResource, PublicPage, LoginPage)

from xmantissa.signup import PasswordResetResource
from xmantissa.test.test_offering import FakeOfferingTechnician
from xmantissa.test.test_websharing import TestAppPowerup, ITest
from xmantissa.test.test_webshell import WebViewerTestMixin
from xmantissa.test.test_website import SiteTestsMixin

class TestAppElement(Element):
    """
    View class for TestAppPowerup.
    """
    docFactory = object()       # masquerade as a valid Element, for the
                                # purposes of theme lookup.
    def __init__(self, original):
        self.original = original
        Element.__init__(self)

registerAdapter(TestAppElement, ITest, INavigableFragment)


class FakeTheme(object):
    """
    Trivial implementation of L{ITemplateNameResolver} which returns document
    factories from an in-memory dictionary.
    @ivar docFactories: C{dict} mapping fragment names to document factory
        objects.
    """
    def __init__(self, docFactories):
        self.docFactories = docFactories


    def getDocFactory(self, fragmentName, default=None):
        """
        Return the document factory for the given name, or the default value if
        the given name is unknown.
        """
        return self.docFactories.get(fragmentName, default)



class AnonymousWebViewerTests(WebViewerTestMixin, TestCase):
    """
    Tests for L{_AnonymousWebViewer}.
    """

    def setupPageFactory(self):
        """
        Create the page factory used by the tests.
        """
        self.pageFactory = _AnonymousWebViewer(self.siteStore)


    def test_roleIn(self):
        """
        L{_AnonymousWebViewer} should provide the Everyone role in the store it
        is asked about.
        """
        theRole = getEveryoneRole(self.adminStore)
        self.assertIdentical(
            self.pageFactory.roleIn(self.adminStore),
            theRole)



class FakeNavigableElement(Item):
    """
    Navigation contributing powerup tests can use to verify the behavior of the
    navigation renderers.
    """
    powerupInterfaces = (INavigableElement,)
    implements(*powerupInterfaces)

    dummy = integer()
    tabs = inmemory(
        doc="""
        The object which will be returned by L{getTabs}.
        """)

    def getTabs(self):
        """
        Return whatever tabs object has been set.
        """
        return self.tabs



class FakeTemplateNameResolver(object):
    """
    Template name resolver which knows about one template.

    @ivar correctName: The name of the template this resolver knows about.

    @ivar correctFactory: The template which will be returned for
        C{correctName}.
    """
    implements(ITemplateNameResolver)

    def __init__(self, correctName, correctFactory):
        self.correctName = correctName
        self.correctFactory = correctFactory


    def getDocFactory(self, name, default=None):
        """
        Return the default for all names other than C{self.correctName}.
        Return C{self.correctFactory} for that.
        """
        if name == self.correctName:
            return self.correctFactory
        return default



class FakePublicItem(Item):
    """
    Some item that is to be shared on an app store.
    """
    dummy = integer()



class FakeApplication(Item):
    """
    Fake implementation of an application installed by an offering.
    """
    implements(IPublicPage)

    index = boolean(doc="""
    Flag indicating whether this application wants to be included on the front
    page.
    """)



class TestHonorInstalledThemes(TestCase):
    """
    Various classes should be using template resolvers to determine which theme
    to use based on a site store.
    """
    def setUp(self):
        self.correctDocumentFactory = object()
        self.store = Store()
        self.fakeResolver = FakeTemplateNameResolver(
            None, self.correctDocumentFactory)

        def fakeConform(interface):
            if interface is ITemplateNameResolver:
                return self.fakeResolver
            return None
        self.store.__conform__ = fakeConform


    def test_offeringsFragmentLoader(self):
        """
        L{_OfferingsFragment.docFactory} is the I{front-page} template loaded
        from the store's ITemplateNameResolver.
        """
        self.fakeResolver.correctName = 'front-page'
        frontPage = FrontPage(store=self.store)
        offeringsFragment = _OfferingsFragment(frontPage)
        self.assertIdentical(
            offeringsFragment.docFactory, self.correctDocumentFactory)


    def test_loginPageLoader(self):
        """
        L{LoginPage.fragment} is the I{login} template loaded from the store's
        ITemplateNameResolver.
        """
        self.fakeResolver.correctName = 'login'
        page = LoginPage(self.store)
        self.assertIdentical(
            page.fragment, self.correctDocumentFactory)


    def test_passwordResetLoader(self):
        """
        L{PasswordResetResource.fragment} is the I{login} template loaded from
        the store's ITemplateNameResolver.
        """
        self.fakeResolver.correctName = 'reset'
        resetPage = PasswordResetResource(self.store)
        self.assertIdentical(
            resetPage.fragment, self.correctDocumentFactory)


class OfferingsFragmentTestCase(TestCase):
    """
    Tests for L{_OfferingsFragment}.
    """
    def setUp(self):
        """
        Set up stores and an offering.
        """
        store = Store(dbdir=self.mktemp())
        appStore1 = SubStore.createNew(store, ("app", "test1.axiom"))
        appStore2 = SubStore.createNew(store, ("app", "test2.axiom"))
        self.firstOffering = Offering(u'first offering', None, None, None, None,
                                      None, [])
        firstInstalledOffering = InstalledOffering(
            store=store, application=appStore1,
            offeringName=self.firstOffering.name)
        ss1 = appStore1.open()
        self.installApp(ss1)
        # (bypass Item.__setattr__)
        object.__setattr__(
            firstInstalledOffering, 'getOffering',
            lambda: self.firstOffering)

        secondOffering = Offering(u'second offering', None, None, None, None,
                                  None, [])
        secondInstalledOffering = InstalledOffering(
            store=store, application=appStore2,
            offeringName=secondOffering.name)
        # (bypass Item.__setattr__)
        object.__setattr__(secondInstalledOffering, 'getOffering',
                           lambda: secondOffering)

        self.fragment = _OfferingsFragment(FrontPage(store=store))


    def installApp(self, ss1):
        """
        Create a public item and share it as the default.
        """
        fpi = FakePublicItem(store=ss1)
        shareItem(fpi, toRole=getEveryoneRole(ss1),
                  shareID=getDefaultShareID(ss1))


    def test_offerings(self):
        """
        L{_OfferingsFragment.data_offerings} returns a generator of C{dict}
        mapping C{'name'} to the name of an installed offering with a
        shared item that requests a link on the default public page.
        """

        self.assertEqual(
            list(self.fragment.data_offerings(None, None)),
            [{'name': self.firstOffering.name}])



class OldOfferingsFragmentTestCase(OfferingsFragmentTestCase):
    """
    Test for deprecated behaviour of L{_OfferingsFragment}.
    """

    def installApp(self, ss1):
        """
        Install an L{IPublicPage} powerup.
        """
        fa = FakeApplication(store=ss1, index=True)
        ss1.powerUp(fa, IPublicPage)


    def test_offerings(self):
        """
        Test the deprecated case for rendering the offering list.
        """
        self.assertWarns(
            DeprecationWarning,
            "Use the sharing system to provide public pages, not IPublicPage",
            __file__,
            OfferingsFragmentTestCase.test_offerings, self)



class PublicFrontPageTests(TestCase, CommandStubMixin):
    """
    Tests for Mantissa's top-level web resource.
    """
    def setUp(self):
        """
        Set up a store with an installed offering.
        """
        self.siteStore = Store(dbdir=self.mktemp())
        Mantissa().installSite(self.siteStore, u"localhost", u"", False)
        off = Offering(
            name=u'test_offering',
            description=u'Offering for creating a sample app store',
            siteRequirements=[],
            appPowerups=[TestAppPowerup],
            installablePowerups=[],
            loginInterfaces=[],
            themes=[],
            )
        self.installedOffering = installOffering(self.siteStore, off, None)
        self.app = self.installedOffering.application
        self.substore = self.app.open()
        sharedItem = getEveryoneRole(self.substore).getShare(
            getDefaultShareID(self.substore))
        self.frontPage = self.siteStore.findUnique(FrontPage)
        self.webViewer = IWebViewer(self.siteStore)


    def test_offeringChild(self):
        """
        Installing an offering makes its shared items accessible under a child
        of L{_PublicFrontPage} with the offering's name.
        """
        frontPage = FrontPage(store=self.siteStore)
        resource = _PublicFrontPage(frontPage, self.webViewer)
        request = FakeRequest()
        result, segments = resource.locateChild(request, ('test_offering',))
        self.assertIdentical(result.userStore, self.substore)
        self.assertTrue(IWebViewer.providedBy(result.webViewer))


    def test_nonExistentChild(self):
        """
        L{_PublicFrontPage.locateChild} returns L{rend.NotFound} for a child
        segment which does not exist.
        """
        store = Store()
        frontPage = FrontPage(store=store)
        resource = _PublicFrontPage(frontPage, IWebViewer(self.siteStore))

        request = FakeRequest()
        ctx = context.WebContext()
        ctx.remember(request, inevow.IRequest)

        result = resource.locateChild(ctx, ('foo',))
        self.assertIdentical(result, rend.NotFound)


    def test_rootChild(self):
        """
        When no default offering has been selected,
        L{PublicFrontPage.locateChild} returns an L{_OfferingsFragment} wrapped by
        the L{IWebViewer}.
        """
        frontPage = FrontPage(store=self.siteStore)
        resource = _PublicFrontPage(frontPage, self.webViewer)
        request = FakeRequest()
        ctx = context.WebContext()
        ctx.remember(request, inevow.IRequest)
        result, segments = resource.locateChild(ctx, ('',))
        self.assertIsInstance(result, PublicPage)
        self.assertIsInstance(result.fragment, _OfferingsFragment)


    def test_rootChildWithDefaultApp(self):
        """
        The root resource provided by L{_PublicFrontPage} when a primary
        application has been selected is that application's L{SharingIndex}.
        """
        resource, segments = self.frontPage.produceResource(
            None, ('',), IWebViewer(self.siteStore))
        self.assertEqual(segments, ('',))
        self.frontPage.defaultApplication = self.app
        result, segments = resource.locateChild(None, ('',))
        self.assertIsInstance(result, PublicPage)
        self.assertIsInstance(result.fragment, TestAppElement)


    def getStore(self):
        return self.siteStore


    def test_switchFrontPage(self):
        """
        'axiomatic frontpage <offeringName>' switches the primary application
        (i.e., the one whose front page will be displayed on the site's root
        resource) to the one belonging to the named offering.
        """
        off2 = Offering(
            name=u'test_offering2',
            description=u'Offering for creating a sample app store',
            siteRequirements=[],
            appPowerups=[TestAppPowerup],
            installablePowerups=[],
            loginInterfaces=[],
            themes=[])
        installedOffering2 = installOffering(self.siteStore, off2, None)
        sfp = SetFrontPage()
        sfp.parent = self
        sfp.parseOptions(["test_offering"])
        resource, segments = self.frontPage.produceResource(
            None, ('',), self.webViewer)
        result, segs = resource.locateChild(None, [''])
        self.assertIdentical(result.fragment.original.store,
                             self.substore)
        self.assertEqual(segs, [])
        sfp.parseOptions(["test_offering2"])
        resource, moreSegs = self.frontPage.produceResource(None, ('',),
                                                            self.webViewer)
        result, segs = resource.locateChild(None, [''])
        self.assertEqual(segs, [])
        self.assertIdentical(result.fragment.original.store,
                             installedOffering2.application.open())

        self.assertRaises(UsageError, sfp.parseOptions, [])
        self.assertRaises(UsageError, sfp.parseOptions, ["nonexistent"])

class AuthenticatedNavigationTestMixin:
    """
    Mixin defining test methods for the authenticated navigation view.

    @ivar siteStore: The site Store with which the page returned by
        L{createPage} will be associated (probably by way of a user store and
        an item).
    """
    userinfo = (u'testuser', u'example.com')
    username = u'@'.join(userinfo)

    def createPage(self):
        """
        Create a subclass of L{_PublicPageMixin} to be used by tests.
        """
        raise NotImplementedError("%r did not implement createPage" % (self,))


    def rootURL(self, request):
        """
        Return the root URL for the website associated with the page returned
        by L{createPage}.
        """
        raise NotImplementedError("%r did not implement rootURL" % (self,))


    def test_headRenderer(self):
        """
        The I{head} renderer gets the head section for each installed theme by
        calling their C{head} method with the request being rendered and adds
        the result to the tag it is passed.
        """
        headCalls = []
        customHead = object()
        class CustomHeadTheme(object):
            priority = 0
            themeName = "custom"
            def head(self, request, site):
                headCalls.append((request, site))
                return customHead
            def getDocFactory(self, name, default):
                return default

        tech = FakeOfferingTechnician()
        tech.installOffering(Offering(
                name=u'fake', description=u'', siteRequirements=[],
                appPowerups=[], installablePowerups=[], loginInterfaces=[],
                themes=[CustomHeadTheme()]))
        self.siteStore.inMemoryPowerUp(tech, IOfferingTechnician)

        # Flush the cache, which is global, else the above fake-out is
        # completely ignored.
        theThemeCache.emptyCache()

        page = self.createPage(self.username)
        tag = div()
        ctx = context.WebContext(tag=tag)
        request = FakeRequest()
        ctx.remember(request, inevow.IRequest)
        result = page.render_head(ctx, None)
        self.assertEqual(result.tagName, 'div')
        self.assertEqual(result.attributes, {})
        self.assertIn(customHead, result.children)
        self.assertEqual(
            headCalls, [(request, ISiteURLGenerator(self.siteStore))])


    def test_authenticatedAuthenticateLinks(self):
        """
        The I{authenticateLinks} renderer should remove the tag it is passed
        from the output if it is called on a L{_PublicPageMixin} being rendered
        for an authenticated user.
        """
        page = self.createPage(self.username)
        authenticateLinksPattern = div()
        ctx = context.WebContext(tag=authenticateLinksPattern)
        tag = page.render_authenticateLinks(ctx, None)
        self.assertEqual(tag, '')


    def test_authenticatedStartmenu(self):
        """
        The I{startmenu} renderer should add navigation elements to the tag it
        is passed if it is called on a L{_PublicPageMixin} being rendered for an
        authenticated user.
        """
        navigable = FakeNavigableElement(store=self.userStore)
        installOn(navigable, self.userStore)
        navigable.tabs = [Tab('foo', 123, 0, [Tab('bar', 432, 0)])]

        page = self.createPage(self.username)
        startMenuTag = div[
            h1(pattern='tab'),
            h2(pattern='subtabs')]

        ctx = context.WebContext(tag=startMenuTag)
        tag = page.render_startmenu(ctx, None)
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        children = [child for child in tag.children if child.pattern is None]
        self.assertEqual(len(children), 0)
        # This structure seems overly complex.
        tabs = list(tag.slotData.pop('tabs'))
        self.assertEqual(len(tabs), 1)
        fooTab = tabs[0]
        self.assertEqual(fooTab.tagName, 'h1')
        self.assertEqual(fooTab.attributes, {})
        self.assertEqual(fooTab.children, [])
        self.assertEqual(fooTab.slotData['href'], self.privateApp.linkTo(123))
        self.assertEqual(fooTab.slotData['name'], 'foo')
        self.assertEqual(fooTab.slotData['kids'].tagName, 'h2')
        subtabs = list(fooTab.slotData['kids'].slotData['kids'])
        self.assertEqual(len(subtabs), 1)
        barTab = subtabs[0]
        self.assertEqual(barTab.tagName, 'h1')
        self.assertEqual(barTab.attributes, {})
        self.assertEqual(barTab.children, [])
        self.assertEqual(barTab.slotData['href'], self.privateApp.linkTo(432))
        self.assertEqual(barTab.slotData['name'], 'bar')
        self.assertEqual(barTab.slotData['kids'], '')


    def test_authenticatedSettingsLink(self):
        """
        The I{settingsLink} renderer should add the URL of the settings item to
        the tag it is passed if it is called on a L{_PublicPageMixin} being
        rendered for an authenticated user.
        """
        page = self.createPage(self.username)
        settingsLinkPattern = div()
        ctx = context.WebContext(tag=settingsLinkPattern)
        tag = page.render_settingsLink(ctx, None)
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        self.assertEqual(
            tag.children,
            [self.privateApp.linkTo(
                    self.userStore.findUnique(PreferenceAggregator).storeID)])


    def test_authenticatedLogout(self):
        """
        The I{logout} renderer should return the tag it is passed if it is
        called on a L{_PublicPageMixin} being rendered for an authenticated
        user.
        """
        page = self.createPage(self.username)
        logoutPattern = div()
        ctx = context.WebContext(tag=logoutPattern)
        tag = page.render_logout(ctx, None)
        self.assertIdentical(logoutPattern, tag)


    def test_authenticatedApplicationNavigation(self):
        """
        The I{applicationNavigation} renderer should add primary navigation
        elements to the tag it is passed if it is called on a
        L{_PublicPageMixin} being rendered for an authenticated user.
        """
        navigable = FakeNavigableElement(store=self.userStore)
        installOn(navigable, self.userStore)
        navigable.tabs = [Tab('foo', 123, 0, [Tab('bar', 432, 0)])]
        request = FakeRequest()

        page = self.createPage(self.username)
        navigationPattern = div[
            span(id='app-tab', pattern='app-tab'),
            span(id='tab-contents', pattern='tab-contents')]
        ctx = context.WebContext(tag=navigationPattern)
        ctx.remember(request)
        tag = page.render_applicationNavigation(ctx, None)
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        children = [child for child in tag.children if child.pattern is None]
        self.assertEqual(children, [])
        self.assertEqual(len(tag.slotData['tabs']), 1)
        fooTab = tag.slotData['tabs'][0]
        self.assertEqual(fooTab.attributes, {'id': 'app-tab'})
        self.assertEqual(fooTab.slotData['name'], 'foo')
        fooContent = fooTab.slotData['tab-contents']
        self.assertEqual(fooContent.attributes, {'id': 'tab-contents'})
        self.assertEqual(
            fooContent.slotData['href'], self.privateApp.linkTo(123))


    def test_title(self):
        """
        The I{title} renderer should add the wrapped fragment's title
        attribute, if any, or the default "Divmod".
        """
        page = self.createPage(self.username)
        titleTag = title()
        tag = page.render_title(context.WebContext(tag=titleTag), None)
        self.assertIdentical(tag, titleTag)
        flattened = flatten(tag)
        self.assertSubstring(flatten(getattr(page.fragment, 'title', 'Divmod')),
                             flattened)


    def test_rootURL(self):
        """
        The I{base} renderer should add the website's root URL to the tag it is
        passed.
        """
        page = self.createPage(self.username)
        baseTag = div()
        request = FakeRequest(headers={'host': 'example.com'})
        ctx = context.WebContext(tag=baseTag)
        ctx.remember(request, inevow.IRequest)
        tag = page.render_rootURL(ctx, None)
        self.assertIdentical(tag, baseTag)
        self.assertEqual(tag.attributes, {})
        self.assertEqual(tag.children, [self.rootURL(request)])


    def test_noUsername(self):
        """
        The I{username} renderer should remove its node from the output when
        presented with a None username.
        """
        page = self.createPage(None)
        result = page.render_username(None, None)
        self.assertEqual(result, "")


    def test_noUrchin(self):
        """
        When there's no Urchin API key installed, the I{urchin} renderer should
        remove its node from the output.
        """
        page = self.createPage(None)
        result = page.render_urchin(None, None)
        self.assertEqual(result, "")


    def test_urchin(self):
        """
        When an Urchin API key is present, the code for enabling Google
        Analytics tracking should be inserted into the shell template.
        """
        keyString = u"UA-99018-11"
        APIKey.setKeyForAPI(self.siteStore, APIKey.URCHIN, keyString)
        page = self.createPage(None)
        t = div()
        result = page.render_urchin(context.WebContext(tag=t), None)
        self.assertEqual(result.slotData['urchin-key'], keyString)


    def usernameRenderingTest(self, username, hostHeader, expectedUsername):
        """
        Verify that the username will be rendered appropriately given the host
        of the HTTP request.

        @param username: the user's full login identifier.
        @param hostHeader: the value of the 'host' header.
        @param expectedUsername: the expected value of the rendered username.
        """
        page = self.createPage(username)
        userTag = span()
        req = FakeRequest(headers={'host': hostHeader})
        ctx = context.WebContext(tag=userTag)
        ctx.remember(req, inevow.IRequest)
        tag = page.render_username(ctx, None)
        self.assertEqual(tag.tagName, 'span')
        self.assertEqual(tag.children, [expectedUsername])


    def test_localUsername(self):
        """
        The I{username} renderer should render just the username when the
        username domain is the same as the HTTP request's domain. otherwise it
        should render the full username complete with domain.
        """
        domainUser = self.username.split('@')[0]
        return self.usernameRenderingTest(
            self.username, 'example.com', domainUser)


    def test_remoteUsername(self):
        """
        The I{username} renderer should render username with the domain when
        the username domain is different than the HTTP request's domain.
        """
        return self.usernameRenderingTest(
            self.username, 'not-example.com', self.username)


    def test_usernameWithHostPort(self):
        """
        The I{username} renderer should respect ports in the host headers.
        """
        domainUser = self.username.split('@')[0]
        return self.usernameRenderingTest(
            self.username, 'example.com:8080', domainUser)


    def test_prefixedDomainUsername(self):
        """
        The I{username} renderer should render just the username in the case
        where you are viewing a subdomain as well; if bob is viewing
        'jethro.divmod.com' or 'www.divmod.com', he should still see the
        username 'bob'.
        """
        domainUser = self.username.split('@')[0]
        return self.usernameRenderingTest(
            self.username, 'www.example.com', domainUser)



class _PublicAthenaLivePageTestMixin(AuthenticatedNavigationTestMixin):
    """
    Mixin which defines test methods which exercise functionality provided by
    the various L{xmantissa.publicweb._PublicPageMixin} subclasses, like
    L{PublicAthenaLivePage} and L{PublicNavAthenaLivePage}.
    """
    signupURL = u'sign/up'
    signupPrompt = u'sign up now'

    def setUp(self):
        self.siteStore = Store(filesdir=self.mktemp())

        def siteStoreTxn():
            Mantissa().installSite(
                self.siteStore, self.userinfo[1], u"", False)
            ticketed = signup.FreeTicketSignup(
                store=self.siteStore, prefixURL=self.signupURL,
                prompt=self.signupPrompt)
            signup._SignupTracker(store=self.siteStore, signupItem=ticketed)

            return  Create().addAccount(
                self.siteStore, self.userinfo[0],
                self.userinfo[1], u'password').avatars.open()

        self.userStore = self.siteStore.transact(siteStoreTxn)

        def userStoreTxn():
            self.privateApp = PrivateApplication(store=self.userStore)
            installOn(self.privateApp, self.userStore)
        self.userStore.transact(userStoreTxn)


    def rootURL(self, request):
        """
        Return the root URL as reported by C{self.website}.
        """
        return ISiteURLGenerator(self.siteStore).rootURL(request)


    def test_unauthenticatedAuthenticateLinks(self):
        """
        The I{authenticateLinks} renderer should add login and signup links to
        the tag it is passed, if it is called on a L{_PublicPageMixin} being
        rendered for an unauthenticated user.
        """
        page = self.createPage(None)
        authenticateLinksPattern = div[span(pattern='signup-link')]
        ctx = context.WebContext(tag=authenticateLinksPattern)
        tag = page.render_authenticateLinks(ctx, None)
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        children = [child for child in tag.children if child.pattern is None]
        self.assertEqual(len(children), 1)
        self.assertEqual(
            children[0].slotData,
            {'prompt': self.signupPrompt, 'url': '/' + self.signupURL})


    def test_unauthenticatedStartmenu(self):
        """
        The I{startmenu} renderer should remove the tag it is passed from the
        output if it is called on a L{_PublicPageMixin} being rendered for an
        unauthenticated user.
        """
        page = self.createPage(None)
        startMenuTag = div()
        ctx = context.WebContext(tag=startMenuTag)
        tag = page.render_startmenu(ctx, None)
        self.assertEqual(tag, '')


    def test_unauthenticatedSettingsLink(self):
        """
        The I{settingsLink} renderer should remove the tag it is passed from
        the output if it is called on a L{_PublicPageMixin} being rendered for
        an unauthenticated user.
        """
        page = self.createPage(None)
        settingsLinkPattern = div()
        ctx = context.WebContext(tag=settingsLinkPattern)
        tag = page.render_settingsLink(ctx, None)
        self.assertEqual(tag, '')


    def test_unauthenticatedLogout(self):
        """
        The I{logout} renderer should remove the tag it is passed from the
        output if it is called on a L{_PublicPageMixin} being rendered for an
        authenticated user.
        """
        page = self.createPage(None)
        logoutPattern = div()
        ctx = context.WebContext(tag=logoutPattern)
        tag = page.render_logout(ctx, None)
        self.assertEqual(tag, '')


    def test_unauthenticatedApplicationNavigation(self):
        """
        The I{applicationNavigation} renderer should remove the tag it is
        passed from the output if it is called on a L{_PublicPageMixin} being
        rendered for an unauthenticated user.
        """
        page = self.createPage(None)
        navigationPattern = div()
        ctx = context.WebContext(tag=navigationPattern)
        tag = page.render_applicationNavigation(ctx, None)
        self.assertEqual(tag, '')



class TestFragment(rend.Fragment):
    title = u'a test fragment'



class PublicAthenaLivePageTestCase(_PublicAthenaLivePageTestMixin, TestCase):
    """
    Tests for L{PublicAthenaLivePage}.
    """
    def createPage(self, forUser):
        return PublicAthenaLivePage(
            self.siteStore, TestFragment(), forUser=forUser)



class PublicNavAthenaLivePageTestCase(_PublicAthenaLivePageTestMixin, TestCase):
    """
    Tests for L{PublicNavAthenaLivePage}.
    """
    suppress = [SUPPRESS(category=DeprecationWarning)]

    def createPage(self, forUser):
        return PublicNavAthenaLivePage(
            self.siteStore, TestFragment(), forUser=forUser)



class GetLoaderTests(TestCase):
    """
    Tests for L{xmantissa.publicweb.getLoader}.
    """
    def test_deprecated(self):
        """
        Calling L{getLoader} emits a deprecation warning.
        """
        self.assertWarns(
            DeprecationWarning,
            "xmantissa.publicweb.getLoader is deprecated, use "
            "PrivateApplication.getDocFactory or SiteTemplateResolver."
            "getDocFactory.",
            __file__,
            lambda: getLoader("shell"))



class CustomizedPublicPageTests(TestCase):
    """
    Tests for L{CustomizedPublicPage}.

    Let's say you've got a normal Mantissa database.  There's an
    L{AnonymousSite} in the site store, powering it up for L{IResource}.
    There's a user, that has a user store, which has a L{WebSite} as their
    L{IResource} avatar, plus a L{PrivateApplication} and a
    L{CustomizedPublicPage} as L{ISiteRootPlugin}s.

    L{CustomizedPublicPage}'s purpose is to make sure that when the user views
    the public site, their L{IWebViewer} is propagated to children of
    the global L{AnonymousSite}.
    """


    def setUp(self):
        """
        Create a store as described in the test case docstring.
        """
        site = Store(self.mktemp())
        Mantissa().installSite(site, u"example.com", u"", False)
        Mantissa().installAdmin(site, u'admin', u'example.com', u'asdf')
        anonsite = site.findUnique(AnonymousSite)
        user = site.findUnique(LoginSystem).accountByAddress(
            u"admin",u"example.com").avatars.open()
        self.website = user.findUnique(WebSite)
        self.privapp = user.findUnique(PrivateApplication)
        self.site = site


    def test_propagateNavigationToSlashUsers(self):
        """
        When the 'users' child is requested through a CustomizedPublicPage,
        L{AnonymousSite.rootChild_users} method should be invoked to produce a
        L{UserIndexPage} for the given user's L{PrivateApplication}.
        """
        wrapper, resultSegs = self.website.locateChild(
            FakeRequest(headers={"host": "example.com"}),
            ('users',))
        self.assertIsInstance(wrapper, _CustomizingResource)
        self.assertIsInstance(wrapper.currentResource, UserIndexPage)
        self.assertIsInstance(wrapper.currentResource.webViewer,
                              _AuthenticatedWebViewer)
        self.assertIdentical(wrapper.currentResource.webViewer._privateApplication,
                             self.privapp)


    def test_propagateNavigationToPlugins(self):
        """
        The site store has an L{ISiteRootPlugin} which provides some other
        application-defined resource - we'll call that 'AppSitePlugin'.

        L{CustomizedPublicPage}'s whole purpose is to make sure that when
        'AppSitePlugin' wants to return a resource, that resource is
        appropriately decorated so that its shell template will appear
        appropriate to the logged-in user.  In order to do that,
        'AppSitePlugin' must receive as its C{webViewer} argument the same
        one that L{CustomizedPublicPage} does.
        """
        # Stock configuration now set up, let's introduce a site plugin...

        result = object()
        calledWith = []
        class AppSitePlugin(object):
            implements(ISiteRootPlugin)
            def produceResource(self, request, segments, webViewer):
                calledWith.append([request, segments, webViewer])
                return result, ()

        self.site.inMemoryPowerUp(AppSitePlugin(), ISiteRootPlugin)
        req = FakeRequest(headers={"host": "example.com"})
        wrapper, resultSegs = self.website.locateChild(req, ("foo", "bar"))

        [(inreq, segs, webViewer)] = calledWith
        self.assertIdentical(inreq, req)
        self.assertEqual(segs, ('foo', 'bar'))
        self.assertIsInstance(webViewer, _AuthenticatedWebViewer)
        self.assertEqual(webViewer._privateApplication, self.privapp)

        self.assertIsInstance(wrapper, _CustomizingResource)
        self.assertIdentical(wrapper.currentResource, result)
        self.assertIdentical(resultSegs, ())



class AnonymousSiteTests(SiteTestsMixin, TestCase):
    """
    Tests for L{AnonymousSite}.
    """
    def setUp(self):
        """
        Set up a store with a valid offering to test against.
        """
        SiteTestsMixin.setUp(self)
        self.store = self.siteStore
        self.site = ISiteURLGenerator(self.store)
        self.resource = IResource(self.store)


    def test_powersUpWebViewer(self):
        """
        L{AnonymousSite} provides an indirected L{IWebViewer}
        powerup, and its indirected powerup should be the default provider of
        that interface.
        """
        webViewer = IWebViewer(self.store)
        self.assertIsInstance(webViewer, _AnonymousWebViewer)
        self.assertIdentical(webViewer._siteStore, self.store)


    def test_login(self):
        """
        L{AnonymousSite} has a I{login} child which returns a L{LoginPage}
        instance.
        """
        host = 'example.org'
        port = 1234
        netloc = '%s:%d' % (host, port)

        request = FakeRequest(
            headers={'host': netloc},
            uri='/login/foo',
            currentSegments=[],
            isSecure=False)

        self.site.hostname = host.decode('ascii')
        SSLPort(store=self.store, portNumber=port, factory=self.site)

        resource, segments = self.resource.locateChild(request, ("login",))
        self.assertTrue(isinstance(resource, LoginPage))
        self.assertIdentical(resource.store, self.store)
        self.assertEqual(resource.segments, ())
        self.assertEqual(resource.arguments, {})
        self.assertEqual(segments, ())


    def test_resetPassword(self):
        """
        L{AnonymousSite} has a I{resetPassword} child which returns a
        L{PasswordResetResource} instance.
        """
        resource, segments = self.resource.locateChild(
            FakeRequest(headers={"host": "example.com"}),
            ("resetPassword",))
        self.assertTrue(isinstance(resource, PasswordResetResource))
        self.assertIdentical(resource.store, self.store)
        self.assertEqual(segments, ())


    def test_users(self):
        """
        L{AnonymousSite} has a I{users} child which returns a L{UserIndexPage}
        instance.
        """
        resource, segments = self.resource.locateChild(
            FakeRequest(headers={"host": "example.com"}), ("users",))
        self.assertTrue(isinstance(resource, UserIndexPage))
        self.assertIdentical(
            resource.loginSystem, self.store.findUnique(LoginSystem))
        self.assertEqual(segments, ())


    def test_notFound(self):
        """
        L{AnonymousSite.locateChild} returns L{NotFound} for requests it cannot
        find another response for.
        """
        result = self.resource.locateChild(
            FakeRequest(headers={"host": "example.com"}),
            ("foo", "bar"))
        self.assertIdentical(result, NotFound)
