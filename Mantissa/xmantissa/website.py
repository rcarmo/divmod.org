# -*- test-case-name: xmantissa.test.test_website -*-

"""
This module defines the basic engine for web sites and applications using
Mantissa.  It defines the basic in-database web server, and an authentication
binding using nevow.guard.

To interact with the code defined here, create a web site using the
command-line 'axiomatic' program using the 'web' subcommand.
"""

import warnings

from zope.interface import implements

try:
    from cssutils import CSSParser
    CSSParser
except ImportError:
    CSSParser = None



from epsilon.structlike import record

from nevow.inevow import IRequest, IResource
from nevow.rend import Page, Fragment
from nevow import inevow
from nevow.static import File
from nevow.url import URL
from nevow import url
from nevow import athena

from axiom.iaxiom import IPowerupIndirector
from axiom import upgrade
from axiom.item import Item, _PowerupConnector, declareLegacyItem
from axiom.attributes import AND, integer, text, reference, bytes, boolean
from axiom.userbase import LoginSystem, getAccountNames
from axiom.dependency import installOn, uninstallFrom, installedOn

from xmantissa.ixmantissa import (
    ISiteRootPlugin, ISessionlessSiteRootPlugin,
    ISiteURLGenerator)
from xmantissa.port import TCPPort, SSLPort
from xmantissa.web import SiteConfiguration
from xmantissa.cachejs import theHashModuleProvider
from xmantissa._webutil import SiteRootMixin


class MantissaLivePage(athena.LivePage):
    """
    An L{athena.LivePage} which supports the global JavaScript modules
    collection that Mantissa provides as a root resource.

    All L{athena.LivePage} usages within and derived from Mantissa should
    subclass this.

    @ivar webSite: a L{WebSite} instance which provides site configuration
        information for generating links.

    @ivar hashCache: a cache which maps JS module names to
        L{xmantissa.cachejs.CachedJSModule} objects.
    @type hashCache: L{xmantissa.cachejs.HashedJSModuleProvider}

    @type _moduleRoot: L{URL}
    @ivar _moduleRoot: The base location for script tags which load Athena
        modules required by this page and widgets on this page.  This is set
        based on the I{Host} header in the request, so it is C{None} until
        the instance is actually rendered.
    """

    hashCache = theHashModuleProvider

    _moduleRoot = None

    def __init__(self, webSite, *a, **k):
        """
        Create a L{MantissaLivePage}.

        @param webSite: a L{WebSite} with a usable secure port implementation.
        """
        self.webSite = webSite
        athena.LivePage.__init__(self, transportRoot=url.root.child('live'),
                                 *a, **k)
        self._jsDepsMemo = self.hashCache.depsMemo


    def beforeRender(self, ctx):
        """
        Before rendering, retrieve the hostname from the request being
        responded to and generate an URL which will serve as the root for
        all JavaScript modules to be loaded.
        """
        request = IRequest(ctx)
        root = self.webSite.rootURL(request)
        self._moduleRoot = root.child('__jsmodule__')


    def getJSModuleURL(self, moduleName):
        """
        Retrieve an L{URL} object which references the given module name.

        This makes a 'best effort' guess as to an fully qualified HTTPS URL
        based on the hostname provided during rendering and the configuration
        of the site.  This is to avoid unnecessary duplicate retrieval of the
        same scripts from two different URLs by the browser.

        If such configuration does not exist, however, it will simply return an
        absolute path URL with no hostname or port.

        @raise NotImplementedError: if rendering has not begun yet and
        therefore beforeRender has not provided us with a usable hostname.
        """
        if self._moduleRoot is None:
            raise NotImplementedError(
                "JS module URLs cannot be requested before rendering.")
        moduleHash = self.hashCache.getModule(moduleName).hashValue
        return self._moduleRoot.child(moduleHash).child(moduleName)



JUST_SLASH = ('',)

class PrefixURLMixin(object):
    """
    Mixin for use by I[Sessionless]SiteRootPlugin implementors; provides a
    resourceFactory method which looks for an C{prefixURL} string on self,
    and calls and returns self.createResource().

    C{prefixURL} is a '/'-separated unicode string; it must be set before
    calling installOn.  To respond to the url C{http://example.com/foo/bar},
    use the prefixURL attribute u'foo/bar'.

    @ivar sessioned: Boolean indicating whether this object should
    powerup for L{ISiteRootPlugin}.  Note: this is only tested when
    L{installOn} is called.  If you change it later, it will have no
    impact.

    @ivar sessionless: Boolean indicating whether this object should
    powerup for ISessionlessSiteRootPlugin.  This is tested at the
    same time as L{sessioned}.
    """

    sessioned = False
    sessionless = False

    def __str__(self):
        return '/%s => item(%s)' % (self.prefixURL, self.__class__.__name__)


    def createResourceWith(self, webViewer):
        """
        Create and return an IResource.  This will only be invoked if
        the request matches the prefixURL specified on this object.
        May also return None to indicate that this object does not
        actually want to handle this request.

        Note that this will only be invoked for L{ISiteRootPlugin} powerups;
        L{ISessionlessSiteRootPlugin} powerups will only have C{createResource}
        invoked.
        """
        raise NotImplementedError(
            "PrefixURLMixin.createResourceWith(webViewer) should be "
            "implemented by subclasses (%r didn't)" % (
                self.__class__.__name__,))


    # ISiteRootPlugin
    def produceResource(self, request, segments, webViewer):
        """
        Return a C{(resource, subsegments)} tuple or None, depending on whether
        I wish to return an L{IResource} provider for the given set of segments
        or not.
        """
        def thunk():
            cr = getattr(self, 'createResource', None)
            if cr is not None:
                return cr()
            else:
                return self.createResourceWith(webViewer)
        return self._produceIt(segments, thunk)


    # ISessionlessSiteRootPlugin
    def sessionlessProduceResource(self, request, segments):
        """
        Return a C{(resource, subsegments)} tuple or None, depending on whether
        I wish to return an L{IResource} provider for the given set of segments
        or not.
        """
        return self._produceIt(segments, self.createResource)


    def _produceIt(self, segments, thunk):
        """
        Underlying implmeentation of L{PrefixURLMixin.produceResource} and
        L{PrefixURLMixin.sessionlessProduceResource}.

        @param segments: the URL segments to dispatch.

        @param thunk: a 0-argument callable which returns an L{IResource}
        provider, or None.

        @return: a 2-tuple of C{(resource, remainingSegments)}, or L{None}.
        """
        if not self.prefixURL:
            needle = ()
        else:
            needle = tuple(self.prefixURL.split('/'))
        S = len(needle)
        if segments[:S] == needle:
            if segments == JUST_SLASH:
                # I *HATE* THE WEB
                subsegments = segments
            else:
                subsegments = segments[S:]
            res = thunk()
            # Even though the URL matched up, sometimes we might still
            # decide to not handle this request (eg, some prerequisite
            # for our function is not met by the store).  Allow None
            # to be returned by createResource to indicate this case.
            if res is not None:
                return res, subsegments


    def __getPowerupInterfaces__(self, powerups):
        """
        Install me on something (probably a Store) that will be queried for
        ISiteRootPlugin providers.
        """

        #First, all the other powerups
        for x in powerups:
            yield x

        # Only 256 segments are allowed in URL paths.  We want to make sure
        # that static powerups always lose priority ordering to dynamic
        # powerups, since dynamic powerups will have information
        pURL = self.prefixURL
        priority = (pURL.count('/') - 256)
        if pURL == '':
            # Did I mention I hate the web?  Plugins at / are special in 2
            # ways.  Their segment length is kinda-sorta like 0 most of the
            # time, except when it isn't.  We subtract from the priority here
            # to make sure that [''] is lower-priority than ['foo'] even though
            # they are technically the same number of segments; the reason for
            # this is that / is special in that it pretends to be the parent of
            # everything and will score a hit for *any* URL in the hierarchy.
            # Above, we special-case JUST_SLASH to make sure that the other
            # half of this special-casing holds true.
            priority -= 1

        if not self.sessioned and not self.sessionless:
            warnings.warn(
                "Set either sessioned or sessionless on %r!  Falling back to "
                "deprecated providedBy() behavior" % (self.__class__.__name__,),
                DeprecationWarning,
                stacklevel=2)
            for iface in ISessionlessSiteRootPlugin, ISiteRootPlugin:
                if iface.providedBy(self):
                    yield (iface, priority)
        else:
            if self.sessioned:
                yield (ISiteRootPlugin, priority)
            if self.sessionless:
                yield (ISessionlessSiteRootPlugin, priority)


class StaticSite(PrefixURLMixin, Item):
    implements(ISessionlessSiteRootPlugin,     # implements both so that it
               ISiteRootPlugin)                # works in both super and sub
                                               # stores.
    typeName = 'static_web_site'
    schemaVersion = 2

    prefixURL = text()
    staticContentPath = text()

    sessioned = boolean(default=False)
    sessionless = boolean(default=True)

    def __str__(self):
        return '/%s => file(%s)' % (self.prefixURL, self.staticContentPath)

    def createResource(self):
        return File(self.staticContentPath)

    def installSite(self):
        """
        Not using the dependency system for this class because it's only
        installed via the command line, and multiple instances can be
        installed.
        """
        for iface, priority in self.__getPowerupInterfaces__([]):
            self.store.powerUp(self, iface, priority)

def upgradeStaticSite1To2(oldSite):
    newSite = oldSite.upgradeVersion(
        'static_web_site', 1, 2,
        staticContentPath=oldSite.staticContentPath,
        prefixURL=oldSite.prefixURL,
        sessionless=True)
    for pc in newSite.store.query(_PowerupConnector,
                                  AND(_PowerupConnector.powerup == newSite,
                                      _PowerupConnector.interface == u'xmantissa.ixmantissa.ISiteRootPlugin')):
        pc.item.powerDown(newSite, ISiteRootPlugin)
    return newSite
upgrade.registerUpgrader(upgradeStaticSite1To2, 'static_web_site', 1, 2)


class StaticRedirect(Item, PrefixURLMixin):
    implements(inevow.IResource,
               ISessionlessSiteRootPlugin,
               ISiteRootPlugin)

    schemaVersion = 2
    typeName = 'web_static_redirect'

    targetURL = text(allowNone=False)

    prefixURL = text(allowNone=False)

    sessioned = boolean(default=True)
    sessionless = boolean(default=True)

    def __str__(self):
        return '/%s => url(%s)' % (self.prefixURL, self.targetURL)

    def locateChild(self, ctx, segments):
        return self, ()

    def renderHTTP(self, ctx):
        return URL.fromContext(ctx).click(self.targetURL)

    def createResource(self):
        return self

def upgradeStaticRedirect1To2(oldRedirect):
    newRedirect = oldRedirect.upgradeVersion(
        'web_static_redirect', 1, 2,
        targetURL=oldRedirect.targetURL,
        prefixURL=oldRedirect.prefixURL)
    if newRedirect.prefixURL == u'':
        newRedirect.sessionless = False
        for pc in newRedirect.store.query(_PowerupConnector,
                                          AND(_PowerupConnector.powerup == newRedirect,
                                              _PowerupConnector.interface == u'xmantissa.ixmantissa.ISessionlessSiteRootPlugin')):
            pc.item.powerDown(newRedirect, ISessionlessSiteRootPlugin)
    return newRedirect
upgrade.registerUpgrader(upgradeStaticRedirect1To2, 'web_static_redirect', 1, 2)

class AxiomPage(Page):
    def renderHTTP(self, ctx):
        return self.store.transact(Page.renderHTTP, self, ctx)



class AxiomFragment(Fragment):
    def rend(self, ctx, data):
        return self.store.transact(Fragment.rend, self, ctx, data)



class StylesheetFactory(record('installedOfferingNames rootURL')):
    """
    Factory which creates resources for stylesheets which will rewrite URLs in
    them to be rooted at a particular location.

    @ivar installedOfferingNames: A C{list} of C{unicode} giving the names of
        the offerings which are installed and have a static content path.
        These are the offerings for which C{StaticContent} will find children,
        so these are the only offerings URLs pointed at which should be
        rewritten.

    @ivar rootURL: A one-argument callable which takes a request and returns an
        L{URL} which is to be used as the root of all URLs served by resources
        this factory creates.
    """
    def makeStylesheetResource(self, path, registry):
        """
        Return a resource for the css at the given path with its urls rewritten
        based on self.rootURL.
        """
        return StylesheetRewritingResourceWrapper(
            File(path), self.installedOfferingNames, self.rootURL)



class StylesheetRewritingResourceWrapper(
    record('resource installedOfferingNames rootURL')):
    """
    Resource which renders another resource using a request which rewrites CSS
    URLs.

    @ivar resource: Another L{IResource} which will be used to generate the
        response.

    @ivar installedOfferingNames: See L{StylesheetFactory.installedOfferingNames}

    @ivar rootURL: See L{StylesheetFactory.rootURL}
    """
    implements(IResource)

    def renderHTTP(self, context):
        """
        Render C{self.resource} through a L{StylesheetRewritingRequestWrapper}.
        """
        request = IRequest(context)
        request = StylesheetRewritingRequestWrapper(
            request, self.installedOfferingNames, self.rootURL)
        context.remember(request, IRequest)
        return self.resource.renderHTTP(context)



class StylesheetRewritingRequestWrapper(object):
    """
    Request which intercepts the response body, parses it as CSS, rewrites its
    URLs, and sends the serialized result.

    @ivar request: Another L{IRequest} object, methods of which will be used to
        implement this request.

    @ivar _buffer: A list of C{str} which have been passed to the write method.

    @ivar installedOfferingNames: See L{StylesheetFactory.installedOfferingNames}

    @ivar rootURL: See L{StylesheetFactory.rootURL}.
    """
    def __init__(self, request, installedOfferingNames, rootURL):
        self.request = request
        self._buffer = []
        self.installedOfferingNames = installedOfferingNames
        self.rootURL = rootURL


    def __getattr__(self, name):
        """
        Pass attribute lookups on to the wrapped request object.
        """
        return getattr(self.request, name)


    def write(self, bytes):
        """
        Buffer the given bytes for later processing.
        """
        self._buffer.append(bytes)


    def _replace(self, url):
        """
        Change URLs with absolute paths so they are rooted at the correct
        location.
        """
        segments = url.split('/')
        if segments[0] == '':
            root = self.rootURL(self.request)
            if segments[1] == 'Mantissa':
                root = root.child('static').child('mantissa-base')
                segments = segments[2:]
            elif segments[1] in self.installedOfferingNames:
                root = root.child('static').child(segments[1])
                segments = segments[2:]
            for seg in segments:
                root = root.child(seg)
            return str(root)
        return url


    def finish(self):
        """
        Parse the buffered response body, rewrite its URLs, write the result to
        the wrapped request, and finish the wrapped request.
        """
        stylesheet = ''.join(self._buffer)
        parser = CSSParser()
        css = parser.parseString(stylesheet)
        css.replaceUrls(self._replace)
        self.request.write(css.cssText)
        return self.request.finish()



class WebSite(Item, SiteRootMixin):
    """
    An IResource avatar which supports L{ISiteRootPlugin}s on user stores
    and a limited number of other statically defined children.
    """
    powerupInterfaces = (IResource,)
    implements(*powerupInterfaces + (IPowerupIndirector,))

    typeName = 'mantissa_web_powerup'
    schemaVersion = 6

    hitCount = integer(default=0)

    def cleartextRoot(self, hostname=None):
        """
        Return a string representing the HTTP URL which is at the root of this
        site.

        @param hostname: An optional unicode string which, if specified, will
        be used as the hostname in the resulting URL, regardless of the
        C{hostname} attribute of this item.
        """
        warnings.warn(
            "Use ISiteURLGenerator.rootURL instead of WebSite.cleartextRoot.",
            category=DeprecationWarning,
            stacklevel=2)
        if self.store.parent is not None:
            generator = ISiteURLGenerator(self.store.parent)
        else:
            generator = ISiteURLGenerator(self.store)
        return generator.cleartextRoot(hostname)


    def encryptedRoot(self, hostname=None):
        """
        Return a string representing the HTTPS URL which is at the root of this
        site.

        @param hostname: An optional unicode string which, if specified, will
        be used as the hostname in the resulting URL, regardless of the
        C{hostname} attribute of this item.
        """
        warnings.warn(
            "Use ISiteURLGenerator.rootURL instead of WebSite.encryptedRoot.",
            category=DeprecationWarning,
            stacklevel=2)
        if self.store.parent is not None:
            generator = ISiteURLGenerator(self.store.parent)
        else:
            generator = ISiteURLGenerator(self.store)
        return generator.encryptedRoot(hostname)


    def maybeEncryptedRoot(self, hostname=None):
        """
        Returning a string representing the HTTPS URL which is at the root of
        this site, falling back to HTTP if HTTPS service is not available.

        @param hostname: An optional unicode string which, if specified, will
        be used as the hostname in the resulting URL, regardless of the
        C{hostname} attribute of this item.
        """
        warnings.warn(
            "Use ISiteURLGenerator.rootURL instead of "
            "WebSite.maybeEncryptedRoot",
            category=DeprecationWarning,
            stacklevel=2)
        if self.store.parent is not None:
            generator = ISiteURLGenerator(self.store.parent)
        else:
            generator = ISiteURLGenerator(self.store)
        root = generator.encryptedRoot(hostname)
        if root is None:
            root = generator.cleartextRoot(hostname)
        return root


    def rootURL(self, request):
        """
        Simple utility function to provide a root URL for this website which is
        appropriate to use in links generated in response to the given request.

        @type request: L{twisted.web.http.Request}
        @param request: The request which is being responded to.

        @rtype: L{URL}
        @return: The location at which the root of the resource hierarchy for
            this website is available.
        """
        warnings.warn(
            "Use ISiteURLGenerator.rootURL instead of WebSite.rootURL.",
            category=DeprecationWarning,
            stacklevel=2)
        if self.store.parent is not None:
            generator = ISiteURLGenerator(self.store.parent)
        else:
            generator = ISiteURLGenerator(self.store)
        return generator.rootURL(request)


    def rootChild_resetPassword(self, req, webViewer):
        """
        Redirect authenticated users to their settings page (hopefully they
        have one) when they try to reset their password.

        This is the wrong way for this functionality to be implemented.  See
        #2524.
        """
        from xmantissa.ixmantissa import IWebTranslator, IPreferenceAggregator
        return URL.fromString(
            IWebTranslator(self.store).linkTo(
                IPreferenceAggregator(self.store).storeID))


    def setServiceParent(self, parent):
        """
        Compatibility hack necessary to prevent the Axiom service startup
        mechanism from barfing.  Even though this Item is no longer an IService
        powerup, it will still be found as one one more time and this method
        will be called on it.
        """


    def getFactory(self):
        """
        @see L{setServiceParent}.
        """
        return self.store.findUnique(SiteConfiguration).getFactory()


    def _getUsername(self):
        """
        Return a username, suitable for creating a L{VirtualHostWrapper} with.
        """
        return u'@'.join(getAccountNames(self.store).next())




class APIKey(Item):
    """
    Persistent record of a key used for accessing an external API.

    @cvar URCHIN: Constant name for the "Google Analytics" API
    (http://code.google.com/apis/maps/)
    @type URCHIN: C{unicode}
    """
    URCHIN = u'Google Analytics'

    apiName = text(
        doc="""
        L{APIKey} constant naming the API this key is for.
        """, allowNone=False)


    apiKey = text(
        doc="""
        The key.
        """, allowNone=False)


    def getKeyForAPI(cls, siteStore, apiName):
        """
        Get the API key for the named API, if one exists.

        @param siteStore: The site store.
        @type siteStore: L{axiom.store.Store}

        @param apiName: The name of the API.
        @type apiName: C{unicode} (L{APIKey} constant)

        @rtype: L{APIKey} or C{NoneType}
        """
        return siteStore.findUnique(
            cls, cls.apiName == apiName, default=None)
    getKeyForAPI = classmethod(getKeyForAPI)


    def setKeyForAPI(cls, siteStore, apiName, apiKey):
        """
        Set the API key for the named API, overwriting any existing key.

        @param siteStore: The site store to install the key in.
        @type siteStore: L{axiom.store.Store}

        @param apiName: The name of the API.
        @type apiName: C{unicode} (L{APIKey} constant)

        @param apiKey: The key for accessing the API.
        @type apiKey: C{unicode}

        @rtype: L{APIKey}
        """
        existingKey = cls.getKeyForAPI(siteStore, apiName)
        if existingKey is None:
            return cls(store=siteStore, apiName=apiName, apiKey=apiKey)
        existingKey.apiKey = apiKey
        return existingKey
    setKeyForAPI = classmethod(setKeyForAPI)



def _makeSiteConfiguration(currentVersion, oldSite, couldHavePorts):
    from xmantissa.publicweb import AnonymousSite

    newSite = oldSite.upgradeVersion(
        'mantissa_web_powerup', currentVersion, 6,
        hitCount=oldSite.hitCount)

    if newSite.store.parent is not None:
        return newSite

    # SiteConfiguration dependsOn LoginSystem.  LoginSystem was probably
    # installed by the mantissa axiomatic command.  During the dependency
    # system conversion, that command was changed to use installOn on the
    # LoginSystem.  However, no upgrader was supplied to create the new
    # dependency state.  Consequently, there may be none.  Consequently, a new
    # LoginSystem will be created if an item which dependsOn LoginSystem is
    # installed.  This would be bad.  So, set up the necessary dependency state
    # here, before instantiating SiteConfiguration. -exarkun

    # Addendum: it is almost certainly the case that there are not legitimate
    # configurations which lack a LoginSystem.  However, a large number of
    # database upgrade tests construct unrealistic databases.  One aspect of
    # the unrealism is that they lack a LoginSystem.  Therefore, rather than
    # changing all the bogus stubs and regenerating the stubs, I will just
    # support the case where LoginSystem is missing.  However, note that a
    # LoginSystem upgrader may invalidate this check and result in a duplicate
    # being created anyway. -exarkun
    loginSystem = oldSite.store.findUnique(LoginSystem, default=None)
    if loginSystem is not None and installedOn(loginSystem) is None:
        installOn(loginSystem, oldSite.store)

    uninstallFrom(oldSite.store, oldSite)

    site = SiteConfiguration(
        store=oldSite.store,
        httpLog=oldSite.store.filesdir.child('httpd.log'),
        hostname=getattr(oldSite, "hostname", None) or u"localhost")
    installOn(site, site.store)

    anonymousAvatar = AnonymousSite(store=oldSite.store)
    installOn(anonymousAvatar, oldSite.store)

    if couldHavePorts:
        for tcp in site.store.query(TCPPort, TCPPort.factory == oldSite):
            tcp.factory = site
        for ssl in site.store.query(SSLPort, SSLPort.factory == oldSite):
            ssl.factory = site
    else:
        if oldSite.portNumber is not None:
            port = TCPPort(
                store=oldSite.store,
                portNumber=oldSite.portNumber,
                factory=site)
            installOn(port, oldSite.store)

        securePortNumber = oldSite.securePortNumber
        certificateFile = oldSite.certificateFile
        if securePortNumber is not None and certificateFile:
            oldCertPath = site.store.dbdir.preauthChild(certificateFile)
            newCertPath = site.store.newFilePath('server.pem')
            oldCertPath.moveTo(newCertPath)
            port = SSLPort(
                store=site.store,
                portNumber=oldSite.securePortNumber,
                certificatePath=newCertPath,
                factory=site)
            installOn(port, site.store)

    newSite.deleteFromStore()


declareLegacyItem(
    WebSite.typeName, 1, dict(
        hitCount = integer(default=0),
        installedOn = reference(),
        portNumber = integer(default=0),
        securePortNumber = integer(default=0),
        certificateFile = bytes(default=None)))

def upgradeWebSite1To6(oldSite):
    return _makeSiteConfiguration(1, oldSite, False)
upgrade.registerUpgrader(upgradeWebSite1To6, 'mantissa_web_powerup', 1, 6)

declareLegacyItem(
    WebSite.typeName, 2, dict(
        hitCount = integer(default=0),
        installedOn = reference(),
        portNumber = integer(default=0),
        securePortNumber = integer(default=0),
        certificateFile = bytes(default=None),
        httpLog = bytes(default=None)))

def upgradeWebSite2to6(oldSite):
    # This is dumb and we should have a way to run procedural upgraders.
    newSite = _makeSiteConfiguration(2, oldSite, False)
    staticMistake = newSite.store.findUnique(StaticSite,
                                             StaticSite.prefixURL == u'static/mantissa',
                                             default=None)
    if staticMistake is not None:
        # Ugh, need cascading deletes
        staticMistake.store.powerDown(staticMistake, ISessionlessSiteRootPlugin)
        staticMistake.deleteFromStore()

    return newSite
upgrade.registerUpgrader(upgradeWebSite2to6, 'mantissa_web_powerup', 2, 6)

declareLegacyItem(
    WebSite.typeName, 3, dict(
        hitCount = integer(default=0),
        installedOn = reference(),
        portNumber = integer(default=0),
        securePortNumber = integer(default=0),
        certificateFile = bytes(default=None),
        httpLog = bytes(default=None)))

def upgradeWebsite3to6(oldSite):
    return _makeSiteConfiguration(3, oldSite, False)
upgrade.registerUpgrader(upgradeWebsite3to6, 'mantissa_web_powerup', 3, 6)

declareLegacyItem(
    WebSite.typeName, 4, dict(
        hitCount=integer(default=0),
        installedOn=reference(),
        hostname=text(default=None),
        portNumber=integer(default=0),
        securePortNumber=integer(default=0),
        certificateFile=bytes(default=0),
        httpLog=bytes(default=None)))

def upgradeWebsite4to6(oldSite):
    return _makeSiteConfiguration(4, oldSite, False)
upgrade.registerUpgrader(upgradeWebsite4to6, 'mantissa_web_powerup', 4, 6)

declareLegacyItem(
    WebSite.typeName, 5, dict(
        hitCount=integer(default=0),
        installedOn=reference(),
        hostname=text(default=None),
        httpLog=bytes(default=None)))

def upgradeWebsite5to6(oldSite):
    """
    Create a L{SiteConfiguration} if this is a site store's L{WebSite}.
    """
    return _makeSiteConfiguration(5, oldSite, True)
upgrade.registerUpgrader(upgradeWebsite5to6, WebSite.typeName, 5, 6)
