# -*- test-case-name: xmantissa.test.test_publicweb -*-
# Copyright 2008 Divmod, Inc. See LICENSE file for details
"""
This module contains code for the publicly-visible areas of a Mantissa
server's web interface.
"""

from warnings import warn

from zope.interface import implements

from twisted.internet import defer

from nevow.inevow import IRequest, IResource
from nevow import rend, tags, inevow
from nevow.url import URL

from axiom.iaxiom import IPowerupIndirector
from axiom import item, attributes, upgrade, userbase
from axiom.dependency import dependsOn, requiresFromSite

from xmantissa import ixmantissa, website, offering
from xmantissa._webutil import (MantissaViewHelper, SiteRootMixin,
                                WebViewerHelper)
from xmantissa.webtheme import (ThemedDocumentFactory, getInstalledThemes,
                                SiteTemplateResolver)
from xmantissa.ixmantissa import (
    IStaticShellContent, ISiteRootPlugin, IMantissaSite, IWebViewer,
    INavigableFragment)
from xmantissa.webnav import startMenu, settingsLink, applicationNavigation
from xmantissa.websharing import UserIndexPage, SharingIndex, getDefaultShareID
from xmantissa.sharing import getEveryoneRole, NoSuchShare


def getLoader(*a, **kw):
    """
    Deprecated.  Don't use this.
    """
    warn("xmantissa.publicweb.getLoader is deprecated, use "
         "PrivateApplication.getDocFactory or SiteTemplateResolver."
         "getDocFactory.", category=DeprecationWarning, stacklevel=2)
    from xmantissa.webtheme import getLoader
    return getLoader(*a, **kw)



def renderShortUsername(ctx, username):
    """
    Render a potentially shortened version of the user's login identifier,
    depending on how the user is viewing it.  For example, if bob@example.com
    is viewing http://example.com/private/, then render 'bob'.  If bob instead
    signed up with only his email address (bob@hotmail.com), and is viewing a
    page at example.com, then render the full address, 'bob@hotmail.com'.

    @param ctx: a L{WovenContext} which has remembered IRequest.

    @param username: a string of the form localpart@domain.

    @return: a L{Tag}, the given context's tag, with the appropriate username
    appended to it.
    """
    if username is None:
        return ''
    req = inevow.IRequest(ctx)
    localpart, domain = username.split('@')
    host = req.getHeader('Host').split(':')[0]
    if host == domain or host.endswith("." + domain):
        username = localpart
    return ctx.tag[username]



class PublicWeb(item.Item, website.PrefixURLMixin):
    """
    Fixture for site-wide public-facing content.

    I implement ISiteRootPlugin and use PrefixURLMixin; see the documentation
    for each of those for a detailed explanation of my usage.

    I wrap a L{websharing.SharingIndex} around an app store. I am installed in
    an app store when it is created.
    """
    implements(ISiteRootPlugin,
               ixmantissa.ISessionlessSiteRootPlugin)

    typeName = 'mantissa_public_web'
    schemaVersion = 3

    prefixURL = attributes.text(
        doc="""
        The prefix of the URL where objects represented by this fixture will
        appear.  For the front page this is u'', for other pages it is their
        respective URLs.
        """, allowNone=False)

    application = attributes.reference(
        doc="""
        A L{SubStore} for an application store.
        """,
        allowNone=False)

    installedOn = attributes.reference(
        doc="""
        """)

    sessioned = attributes.boolean(
        doc="""
        Will this resource be provided to clients with a session?  Defaults to
        False.
        """,
        default=False)

    sessionless = attributes.boolean(
        doc="""
        Will this resource be provided without a session to clients without a
        session?  Defaults to False.
        """,
        default=False)


    def createResource(self):
        """
        When invoked by L{PrefixURLMixin}, return a L{websharing.SharingIndex}
        for my application.
        """
        pp = ixmantissa.IPublicPage(self.application, None)
        if pp is not None:
            warn(
            "Use the sharing system to provide public pages, not IPublicPage",
            category=DeprecationWarning,
            stacklevel=2)
            return pp.getResource()
        return SharingIndex(self.application.open())


def upgradePublicWeb1To2(oldWeb):
    newWeb = oldWeb.upgradeVersion(
        'mantissa_public_web', 1, 2,
        prefixURL=oldWeb.prefixURL,
        application=oldWeb.application,
        installedOn=oldWeb.installedOn)
    newWeb.installedOn.powerUp(newWeb, ixmantissa.ICustomizablePublicPage)
    return newWeb
upgrade.registerUpgrader(upgradePublicWeb1To2, 'mantissa_public_web', 1, 2)

def upgradePublicWeb2To3(oldWeb):
    newWeb = oldWeb.upgradeVersion(
        'mantissa_public_web', 2, 3,
        prefixURL=oldWeb.prefixURL,
        application=oldWeb.application,
        installedOn=oldWeb.installedOn,
        # There was only one PublicWeb before, and it definitely
        # wanted to be sessioned.
        sessioned=True)
    newWeb.installedOn.powerDown(newWeb, ixmantissa.ICustomizablePublicPage)
    other = newWeb.installedOn
    newWeb.installedOn = None
    newWeb.installOn(other)
    return newWeb
upgrade.registerUpgrader(upgradePublicWeb2To3, 'mantissa_public_web', 2, 3)



class _AnonymousWebViewer(WebViewerHelper):
    """
    An implementation of L{IWebViewer} for anonymous users.

    @ivar _siteStore: A site store that contains an L{AnonymousSite} and
        L{SiteConfiguration}.

    @ivar _getDocFactory: the L{SiteTemplateResolver.getDocFactory} method that
        will resolve themes for my site store.
    """
    implements(IWebViewer)

    def __init__(self, siteStore):
        """
        Create an L{_AnonymousWebViewer} for browsing a given site store.
        """
        WebViewerHelper.__init__(
            self,
            SiteTemplateResolver(siteStore).getDocFactory,
            lambda : getInstalledThemes(siteStore))
        self._siteStore = siteStore


    # IWebViewer
    def roleIn(self, userStore):
        """
        Return only the 'everyone' role in the given user- or app-store, since
        the user represented by this object is anonymous.
        """
        return getEveryoneRole(userStore)


    # Complete WebViewerHelper implementation
    def _wrapNavFrag(self, frag, useAthena):
        """
        Wrap the given L{INavigableFragment} in the appropriate type of
        L{_PublicPageMixin}.
        """
        if useAthena:
            return PublicAthenaLivePage(self._siteStore, frag)
        else:
            return PublicPage(None, self._siteStore, frag, None, None)



class _CustomizingResource(object):
    """
    _CustomizingResource is a wrapping resource used to implement
    CustomizedPublicPage.

        There is an implementation assumption here, which is that the top
        _CustomizingResource is always at "/", and locateChild will always be
        invoked at least once.  If this doesn't hold, this render method might
        be invoked on the top level _CustomizingResource, which would cause it
        to be rendered without customization.  If you're going to use this
        class directly for some reason, please keep this in mind.
    """
    implements(inevow.IResource)

    def __repr__(self):
        return '<Customizing Resource %r: %r>' % (self.forWho, self.currentResource)


    def __init__(self, topResource, forWho):
        """
        Create a _CustomizingResource.

        @param topResource: an L{inevow.IResource} provider, who may also
        provide L{ixmantissa.ICustomizable} if it wishes to be customized.

        @param forWho: the external ID of the currently logged-in user.
        @type forWho: unicode
        """
        self.currentResource = topResource
        self.forWho = forWho


    def locateChild(self, ctx, segments):
        """
        Return a Deferred which will fire with the customized version of the
        resource being located.
        """
        D = defer.maybeDeferred(
            self.currentResource.locateChild, ctx, segments)

        def finishLocating((nextRes, nextPath)):
            custom = ixmantissa.ICustomizable(nextRes, None)
            if custom is not None:
                return (custom.customizeFor(self.forWho), nextPath)
            self.currentResource = nextRes
            if nextRes is None:
                return (nextRes, nextPath)
            return (_CustomizingResource(nextRes, self.forWho), nextPath)

        return D.addCallback(finishLocating)


    def renderHTTP(self, ctx):
        """
        Render the resource I was provided at construction time.
        """
        if self.currentResource is None:
            return rend.FourOhFour()
        return self.currentResource # nevow will automatically adapt to
                                    # IResource and call rendering methods.


class CustomizedPublicPage(item.Item):
    """
    L{CustomizedPublicPage} is what allows logged-in users to see dynamic
    resources present in the site store.  Although static resources (under
    http://your-domain.example.com/static) are available to everyone, any user
    who should be able to see content such as http://yoursite/users/some-user/
    when they are logged in must have this installed.
    """
    implements(ISiteRootPlugin)

    typeName = 'mantissa_public_customized'
    schemaVersion = 2

    installedOn = attributes.reference(
        doc="""
        The Avatar for which this item will attempt to retrieve a customized
        page.
        """)

    powerupInterfaces = [(ISiteRootPlugin, -257)]

    publicSiteRoot = requiresFromSite(IMantissaSite, lambda ignored: None)

    def produceResource(self, request, segments, webViewer):
        """
        Produce a resource that traverses site-wide content, passing down the
        given webViewer.  This delegates to the site store's
        L{IMantissaSite} adapter, to avoid a conflict with the
        L{ISiteRootPlugin} interface.

        This method will typically be given an L{_AuthenticatedWebViewer}, which
        can build an appropriate resource for an authenticated shell page,
        whereas the site store's L{IWebViewer} adapter would show an anonymous
        page.

        The result of this method will be a L{_CustomizingResource}, to provide
        support for resources which may provide L{ICustomizable}.  Note that
        Mantissa itself no longer implements L{ICustomizable} anywhere, though.
        All application code should phase out inspecting the string passed to
        ICustomizable in favor of getting more structured information from the
        L{IWebViewer}.  However, it has not been deprecated yet because
        the interface which allows application code to easily access the
        L{IWebViewer} from view code has not yet been developed; it is
        forthcoming.

        See ticket #2707 for progress on this.
        """
        mantissaSite = self.publicSiteRoot
        if mantissaSite is not None:
            for resource, domain in userbase.getAccountNames(self.store):
                username = '%s@%s' % (resource, domain)
                break
            else:
                username = None
            bottomResource, newSegments = mantissaSite.siteProduceResource(
                request, segments, webViewer)
            return (_CustomizingResource(bottomResource, username), newSegments)
        return None



def customizedPublicPage1To2(oldPage):
    newPage = oldPage.upgradeVersion(
        'mantissa_public_customized', 1, 2,
        installedOn=oldPage.installedOn)
    newPage.installedOn.powerDown(newPage, ISiteRootPlugin)
    newPage.installedOn.powerUp(newPage, ISiteRootPlugin, -257)
    return newPage
upgrade.registerUpgrader(customizedPublicPage1To2, 'mantissa_public_customized', 1, 2)



class _PublicPageMixin(MantissaViewHelper):
    """
    Mixin for use by C{Page} or C{LivePage} subclasses that are visible to
    unauthenticated clients.

    @ivar store: The site store.
    """
    fragment = None
    username = None


    def _getViewerPrivateApplication(self):
        """
        Get the L{PrivateApplication} object for the logged-in user who is
        viewing this resource, as indicated by its C{username} attribute.

        This is highly problematic because it precludes the possibility of
        separating the stores of the viewer and the viewee into separate
        processes, and it is only here until we can get rid of it.  The reason
        it remains is that some application code still imports things which
        subclass L{PublicAthenaLivePage} and L{PublicPage} and uses them with
        usernames specified.  See ticket #2702 for progress on this goal.

        However, Mantissa itself will no longer set this class's username
        attribute to anything other than None, because authenticated users'
        pages will be generated using
        L{xmantissa.webapp._AuthenticatedWebViewer}.  This method is used only
        to render content in the shell template, and those classes have a direct
        reference to the requisite object.

        @rtype: L{PrivateApplication}
        """
        ls = self.store.findUnique(userbase.LoginSystem)
        substore = ls.accountByAddress(*self.username.split('@')).avatars.open()
        from xmantissa.webapp import PrivateApplication
        return substore.findUnique(PrivateApplication)


    def render_authenticateLinks(self, ctx, data):
        """
        For unauthenticated users, add login and signup links to the given tag.
        For authenticated users, remove the given tag from the output.

        When necessary, the I{signup-link} pattern will be loaded from the tag.
        Each copy of it will have I{prompt} and I{url} slots filled.  The list
        of copies will be added as children of the tag.
        """
        if self.username is not None:
            return ''
        # there is a circular import here which should probably be avoidable,
        # since we don't actually need signup links on the signup page.  on the
        # other hand, maybe we want to eventually put those there for
        # consistency.  for now, this import is easiest, and although it's a
        # "friend" API, which I dislike, it doesn't seem to cause any real
        # problems...  -glyph
        from xmantissa.signup import _getPublicSignupInfo

        IQ = inevow.IQ(ctx.tag)
        signupPattern = IQ.patternGenerator('signup-link')

        signups = []
        for (prompt, url) in _getPublicSignupInfo(self.store):
            signups.append(signupPattern.fillSlots(
                    'prompt', prompt).fillSlots(
                    'url', url))

        return ctx.tag[signups]


    def render_startmenu(self, ctx, data):
        """
        For authenticated users, add the start-menu style navigation to the
        given tag.  For unauthenticated users, remove the given tag from the
        output.

        @see L{xmantissa.webnav.startMenu}
        """
        if self.username is None:
            return ''
        translator = self._getViewerPrivateApplication()
        pageComponents = translator.getPageComponents()
        return startMenu(translator, pageComponents.navigation, ctx.tag)


    def render_settingsLink(self, ctx, data):
        """
        For authenticated users, add the URL of the settings page to the given
        tag.  For unauthenticated users, remove the given tag from the output.
        """
        if self.username is None:
            return ''
        translator = self._getViewerPrivateApplication()
        return settingsLink(
            translator,
            translator.getPageComponents().settings,
            ctx.tag)


    def render_applicationNavigation(self, ctx, data):
        """
        For authenticated users, add primary application navigation to the
        given tag.  For unauthenticated users, remove the given tag from the
        output.

        @see L{xmantissa.webnav.applicationNavigation}
        """
        if self.username is None:
            return ''
        translator = self._getViewerPrivateApplication()
        return applicationNavigation(
            ctx,
            translator,
            translator.getPageComponents().navigation)


    def render_search(self, ctx, data):
        """
        Render some UI for performing searches, if we know about a search
        aggregator.
        """
        if self.username is None:
            return ''
        translator = self._getViewerPrivateApplication()
        searchAggregator = translator.getPageComponents().searchAggregator
        if searchAggregator is None or not searchAggregator.providers():
            return ''
        return ctx.tag.fillSlots(
            'form-action', translator.linkTo(searchAggregator.storeID))


    def render_username(self, ctx, data):
        return renderShortUsername(ctx, self.username)


    def render_logout(self, ctx, data):
        if self.username is None:
            return ''
        return ctx.tag


    def render_title(self, ctx, data):
        """
        Return the current context tag containing C{self.fragment}'s C{title}
        attribute, or "Divmod".
        """
        return ctx.tag[getattr(self.fragment, 'title', 'Divmod')]


    def render_rootURL(self, ctx, data):
        """
        Add the WebSite's root URL as a child of the given tag.
        """
        return ctx.tag[
            ixmantissa.ISiteURLGenerator(self.store).rootURL(IRequest(ctx))]


    def render_header(self, ctx, data):
        """
        Render any required static content in the header, from the C{staticContent}
        attribute of this page.
        """
        if self.staticContent is None:
            return ctx.tag

        header = self.staticContent.getHeader()
        if header is not None:
            return ctx.tag[header]
        else:
            return ctx.tag


    def render_footer(self, ctx, data):
        """
        Render any required static content in the footer, from the C{staticContent}
        attribute of this page.
        """
        if self.staticContent is None:
            return ctx.tag

        header = self.staticContent.getFooter()
        if header is not None:
            return ctx.tag[header]
        else:
            return ctx.tag


    def render_urchin(self, ctx, data):
        """
        Render the code for recording Google Analytics statistics, if so
        configured.
        """
        key = website.APIKey.getKeyForAPI(self.store, website.APIKey.URCHIN)
        if key is None:
            return ''
        return ctx.tag.fillSlots('urchin-key', key.apiKey)


    def render_content(self, ctx, data):
        """
        This renderer, which is used for the visual bulk of the page, provides
        self.fragment renderer.
        """
        return ctx.tag[self.fragment]


    def getHeadContent(self, req):
        """
        Retrieve a list of header content from all installed themes on the site
        store.
        """
        site = ixmantissa.ISiteURLGenerator(self.store)
        for t in getInstalledThemes(self.store):
            yield t.head(req, site)


    def render_head(self, ctx, data):
        """
        This renderer calculates content for the <head> tag by concatenating the
        values from L{getHeadContent} and the overridden L{head} method.
        """
        req = inevow.IRequest(ctx)
        more = getattr(self.fragment, 'head', None)
        if more is not None:
            fragmentHead = more()
        else:
            fragmentHead = None
        return ctx.tag[filter(None, list(self.getHeadContent(req)) +
                              [fragmentHead])]



class PublicPage(_PublicPageMixin, rend.Page):
    """
    PublicPage is a utility superclass for implementing static pages which have
    theme support and authentication trimmings.
    """
    docFactory = ThemedDocumentFactory('shell', 'templateResolver')

    def __init__(self, original, store, fragment, staticContent, forUser,
                 templateResolver=None):
        """
        Create a public page.

        @param original: any object

        @param store: a site store containing a L{WebSite}.
        @type store: L{axiom.store.Store}.

        @param fragment: a L{rend.Fragment} to display in the content area of
        the page.

        @param staticContent: some stan, to include in the header of the page.

        @param forUser: a string, the external ID of a user to customize for.

        @param templateResolver: a template resolver instance that will return
        the appropriate doc factory.
        """
        if templateResolver is None:
            templateResolver = ixmantissa.ITemplateNameResolver(store)
        super(PublicPage, self).__init__(original)
        self.store = store
        self.fragment = fragment
        self.staticContent = staticContent
        self.templateResolver = templateResolver
        if forUser is not None:
            assert isinstance(forUser, unicode), forUser
        self.username = forUser



class _OfferingsFragment(rend.Fragment):
    """
    This fragment provides the list of installed offerings as a data generator.
    This is used to display the list of app stores on the default front page.

    @ivar templateResolver: An L{ITemplateNameResolver} which will be used
        to load the document factory.
    """
    implements(INavigableFragment)
    docFactory = ThemedDocumentFactory('front-page', 'templateResolver')

    def __init__(self, original, templateResolver=None):
        """
        Create an _OfferingsFragment with an item from a site store.

        @param original: a L{FrontPage} item.

        @param templateResolver: An L{ITemplateNameResolver} from which to
            load the document factory.  If not specified, the Store of
            C{original} will be adapted to L{ITemplateNameResolver} and used
            for this purpose.  It is recommended that you pass a value for
            this parameter.
        """
        if templateResolver is None:
            templateResolver = ixmantissa.ITemplateNameResolver(original.store)
        self.templateResolver = templateResolver
        super(_OfferingsFragment, self).__init__(original)


    def data_offerings(self, ctx, data):
        """
        Generate a list of installed offerings.

        @return: a generator of dictionaries mapping 'name' to the name of an
        offering installed on the store.
        """
        for io in self.original.store.query(offering.InstalledOffering):
            pp = ixmantissa.IPublicPage(io.application, None)
            if pp is not None and getattr(pp, 'index', True):
                warn("Use the sharing system to provide public pages,"
                     " not IPublicPage",
                     category=DeprecationWarning,
                     stacklevel=2)
                yield {'name': io.offeringName}
            else:
                s = io.application.open()
                try:
                    pp = getEveryoneRole(s).getShare(getDefaultShareID(s))
                    yield {'name': io.offeringName}
                except NoSuchShare:
                    continue



class _PublicFrontPage(object):
    """
    This is the implementation of the default Mantissa front page.  It renders
    a list of offering names, displays the user's name, and lists signup
    mechanisms.  It also provides various top-level URLs.
    """
    implements(IResource)

    def __init__(self, frontPageItem, webViewer):
        """
        Create a _PublicFrontPage.

        @param frontPageItem: a L{FrontPage} item, which we use primarily to
        get at a Store.

        @param webViewer: an L{IWebViewer} that represents the
        user viewing this front page.
        """
        self.frontPageItem = frontPageItem
        self.webViewer = webViewer


    def locateChild(self, ctx, segments):
        """
        Look up children in the normal manner, but then customize them for the
        authenticated user if they support the L{ICustomizable} interface.  If
        the user is attempting to access a private URL, redirect them.
        """
        result = self._getAppStoreResource(ctx, segments[0])
        if result is not None:
            child, segments = result, segments[1:]
            return child, segments

        if segments[0] == '':
            result = self.child_(ctx)
            if result is not None:
                child, segments = result, segments[1:]
                return child, segments

        # If the user is trying to access /private/*, then his session has
        # expired or he is otherwise not logged in. Redirect him to /login,
        # preserving the URL segments, rather than giving him an obscure 404.
        if segments[0] == 'private':
            u = URL.fromContext(ctx).click('/').child('login')
            for seg in segments:
                u = u.child(seg)
            return u, ()

        return rend.NotFound


    def _getAppStoreResource(self, ctx, name):
        """
        Customize child lookup such that all installed offerings on the site
        store that this page is viewing are given an opportunity to display
        their own page.
        """
        offer = self.frontPageItem.store.findFirst(
            offering.InstalledOffering,
            offering.InstalledOffering.offeringName == unicode(name, 'ascii'))
        if offer is not None:
            pp = ixmantissa.IPublicPage(offer.application, None)
            if pp is not None:
                warn("Use the sharing system to provide public pages,"
                     " not IPublicPage",
                     category=DeprecationWarning,
                     stacklevel=2)
                return pp.getResource()
            return SharingIndex(offer.application.open(),
                                self.webViewer)
        return None


    def child_(self, ctx):
        """
        If the root resource is requested, return the primary
        application's front page, if a primary application has been
        chosen.  Otherwise return 'self', since this page can render a
        simple index.
        """
        if self.frontPageItem.defaultApplication is None:
            return self.webViewer.wrapModel(
                _OfferingsFragment(self.frontPageItem))
        else:
            return SharingIndex(self.frontPageItem.defaultApplication.open(),
                                self.webViewer).locateChild(ctx, [''])[0]



class LoginPage(PublicPage):
    """
    This is the page which presents a 'login' dialog to the user, at "/login".

    This does not perform the actual login, nevow.guard does that, at the URL
    /__login__; this resource merely provides the entry field and redirection
    logic.
    """

    # Try to get SSL if possible.  See xmantissa.web.SecuringWrapper and
    # xmantissa.web.SiteConfiguration.getFactory.  This should really be
    # indicated in some other way.  See #2525 -exarkun
    needsSecure = True

    def __init__(self, store, segments=(), arguments=None,
                 templateResolver=None):
        """
        Create a login page.

        @param store: a site store containing a L{WebSite}.
        @type store: L{axiom.store.Store}.

        @param segments: a list of strings.  For example, if you hit
        /login/private/stuff, you want to log in to /private/stuff, and the
        resulting LoginPage will have the segments of ['private', 'stuff']

        @param arguments: A dictionary mapping query argument names to lists of
        values for those arguments (see IRequest.args).

        @param templateResolver: a template resolver instance that will return
        the appropriate doc factory.
        """
        if templateResolver is None:
            templateResolver = ixmantissa.ITemplateNameResolver(store)
        PublicPage.__init__(self, None, store,
                            templateResolver.getDocFactory('login'),
                            IStaticShellContent(store, None),
                            None, templateResolver)
        self.segments = segments
        if arguments is None:
            arguments = {}
        self.arguments = arguments


    def beforeRender(self, ctx):
        """
        Before rendering this page, identify the correct URL for the login to post
        to, and the error message to display (if any), and fill the 'login
        action' and 'error' slots in the template accordingly.
        """
        generator = ixmantissa.ISiteURLGenerator(self.store)
        url = generator.rootURL(IRequest(ctx))
        url = url.child('__login__')
        for seg in self.segments:
            url = url.child(seg)
        for queryKey, queryValues in self.arguments.iteritems():
            for queryValue in queryValues:
                url = url.add(queryKey, queryValue)

        req = inevow.IRequest(ctx)
        err = req.args.get('login-failure', ('',))[0]

        if 0 < len(err):
            error = inevow.IQ(
                        self.fragment).onePattern(
                                'error').fillSlots('error', err)
        else:
            error = ''

        ctx.fillSlots("login-action", url)
        ctx.fillSlots("error", error)


    def locateChild(self, ctx, segments):
        """
        Return a clone of this page that remembers its segments, so that URLs like
        /login/private/stuff will redirect the user to /private/stuff after
        login has completed.
        """
        arguments = IRequest(ctx).args
        return self.__class__(
            self.store, segments, arguments), ()


    def fromRequest(cls, store, request):
        """
        Return a L{LoginPage} which will present the user with a login prompt.

        @type store: L{Store}
        @param store: A I{site} store.

        @type request: L{nevow.inevow.IRequest}
        @param request: The HTTP request which encountered a need for
            authentication.  This will be effectively re-issued after login
            succeeds.

        @return: A L{LoginPage} and the remaining segments to be processed.
        """
        location = URL.fromRequest(request)
        segments = location.pathList(unquote=True, copy=False)
        segments.append(request.postpath[0])
        return cls(store, segments, request.args)
    fromRequest = classmethod(fromRequest)



class FrontPage(item.Item, website.PrefixURLMixin):
    """
    I am a factory for the dynamic resource L{_PublicFrontPage}.
    """
    implements(ISiteRootPlugin)
    typeName = 'mantissa_front_page'
    schemaVersion = 2

    sessioned = True

    publicViews = attributes.integer(
        doc="""
        The number of times this object has been viewed anonymously.  This
        includes renderings of the front page only.
        """,
        default=0)

    privateViews = attributes.integer(
        doc="""
        The number of times this object has been viewed non-anonymously.  This
        includes renderings of the front page only.
        """,
        default=0)

    prefixURL = attributes.text(
        doc="""
        See L{website.PrefixURLMixin}.
        """,
        default=u'',
        allowNone=False)

    defaultApplication = attributes.reference(
        doc="""
        An application L{SubStore} whose default shared item should be
        displayed on the root web resource. If None, the default index
        of applications will be displayed.
        """,
        allowNone=True)

    def createResourceWith(self, crud):
        """
        Create a L{_PublicFrontPage} resource wrapping this object.
        """
        return _PublicFrontPage(self, crud)

item.declareLegacyItem(
    FrontPage.typeName,
    1,
    dict(publicViews = attributes.integer(),
         privateViews = attributes.integer(),
         prefixURL = attributes.text(allowNone=False)))

upgrade.registerAttributeCopyingUpgrader(FrontPage, 1, 2)



class PublicAthenaLivePage(_PublicPageMixin, website.MantissaLivePage):
    """
    PublicAthenaLivePage is a publicly viewable Athena-enabled page which slots
    a single fragment into the center of the page.
    """
    docFactory = ThemedDocumentFactory('shell', 'templateResolver')
    unsupportedBrowserLoader = ThemedDocumentFactory(
        'athena-unsupported', 'templateResolver')

    fragment = None

    def __init__(self, store, fragment, staticContent=None, forUser=None,
                 templateResolver=None,
                 *a, **kw):
        """
        Create a PublicAthenaLivePage.

        @param store: a site store containing an L{AnonymousSite} and
            L{SiteConfiguration}.

        @type store: L{axiom.store.Store}.

        @param fragment: The L{INavigableFragment} provider which will be
            displayed on this page.

        @param templateResolver: a template resolver instance that will return
            the appropriate doc factory.

        This page draws its HTML from the 'shell' template in the active theme.
        If loaded in a browser that does not support Athena, the page provided
        by the 'athena-unsupported' template will be displayed instead.
        """
        self.store = store
        if templateResolver is None:
            templateResolver = ixmantissa.ITemplateNameResolver(self.store)
        self.templateResolver = templateResolver
        super(PublicAthenaLivePage, self).__init__(ixmantissa.ISiteURLGenerator(self.store), *a, **kw)
        if fragment is not None:
            self.fragment = fragment
            # everybody who calls this has a different idea of what 'fragment'
            # means - let's just be super-lenient for now
            if getattr(fragment, 'setFragmentParent', False):
                fragment.setFragmentParent(self)
            else:
                fragment.page = self
        self.staticContent = staticContent
        self.username = forUser


    def render_head(self, ctx, data):
        """
        Put liveglue content into the header of this page to activate it, but
        otherwise delegate to my parent's renderer for <head>.
        """
        ctx.tag[tags.invisible(render=tags.directive('liveglue'))]
        return _PublicPageMixin.render_head(self, ctx, data)



class PublicNavAthenaLivePage(PublicAthenaLivePage):
    """
    DEPRECATED!  Use PublicAthenaLivePage.

    A L{PublicAthenaLivePage} which optionally includes a menubar and
    navigation if the viewer is authenticated.
    """
    def __init__(self, *a, **kw):
        PublicAthenaLivePage.__init__(self, *a, **kw)
        warn(
            "Use PublicAthenaLivePage instead of PublicNavAthenaLivePage",
            category=DeprecationWarning,
            stacklevel=2)



class AnonymousSite(item.Item, SiteRootMixin):
    """
    Root IResource implementation for unauthenticated users.

    This resource allows users to login, reset their passwords, or access
    content provided by any site root plugins.
    """
    powerupInterfaces = (IResource, IMantissaSite, IWebViewer)
    implements(*powerupInterfaces + (IPowerupIndirector,))

    schemaVersion = 2

    loginSystem = dependsOn(userbase.LoginSystem)


    def rootChild_resetPassword(self, req, webViewer):
        """
        Return a page which will allow the user to re-set their password.
        """
        from xmantissa.signup import PasswordResetResource
        return PasswordResetResource(self.store)


    def rootChild_login(self, req, webViewer):
        """
        Return a login page.
        """
        return LoginPage(self.store)


    def rootChild_users(self, req, webViewer):
        """
        Return a child resource to provide access to items shared by users.

        @return: a resource whose children will be private pages of individual
        users.

        @rtype L{xmantissa.websharing.UserIndexPage}
        """
        return UserIndexPage(self.loginSystem, webViewer)


    def _getUsername(self):
        """
        Inform L{VirtualHostWrapper} that it's being accessed anonymously.
        """
        return None


    # IPowerupIndirector
    def indirect(self, interface):
        """
        Indirect the implementation of L{IWebViewer} to L{_AnonymousWebViewer}.
        """
        if interface == IWebViewer:
            return _AnonymousWebViewer(self.store)
        return super(AnonymousSite, self).indirect(interface)



AnonymousSite1 = item.declareLegacyItem(
    'xmantissa_publicweb_anonymoussite', 1,
    dict(
        loginSystem=attributes.reference(),
    ))


def _installV2Powerups(anonymousSite):
    """
    Install the given L{AnonymousSite} for the powerup interfaces it was given
    in version 2.
    """
    anonymousSite.store.powerUp(anonymousSite, IWebViewer)
    anonymousSite.store.powerUp(anonymousSite, IMantissaSite)
upgrade.registerAttributeCopyingUpgrader(AnonymousSite, 1, 2, _installV2Powerups)
