# -*- test-case-name: xmantissa.test.test_website -*-
# Copyright 2005 Divmod, Inc.
# See LICENSE file for details

"""
Mantissa web presence.
"""

from zope.interface import implements

from twisted.python.filepath import FilePath
from twisted.internet.defer import maybeDeferred
from twisted.cred.portal import Portal
from twisted.cred.checkers import AllowAnonymousAccess

from nevow.inevow import IRequest, IResource
from nevow.url import URL
from nevow.appserver import NevowSite, NevowRequest
from nevow.rend import NotFound
from nevow.static import File
from nevow.athena import LivePage

from epsilon.structlike import record

from axiom.item import Item
from axiom.attributes import path, text
from axiom.dependency import dependsOn
from axiom.userbase import LoginSystem

from xmantissa.ixmantissa import ISiteURLGenerator, IProtocolFactoryFactory, IOfferingTechnician, ISessionlessSiteRootPlugin
from xmantissa.port import TCPPort, SSLPort
from xmantissa.cachejs import theHashModuleProvider
from xmantissa.websession import PersistentSessionWrapper


class AxiomRequest(NevowRequest):
    def __init__(self, store, *a, **kw):
        NevowRequest.__init__(self, *a, **kw)
        self.store = store

    def process(self, *a, **kw):
        return self.store.transact(NevowRequest.process, self, *a, **kw)



class AxiomSite(NevowSite):
    def __init__(self, store, *a, **kw):
        NevowSite.__init__(self, *a, **kw)
        self.store = store
        self.requestFactory = lambda *a, **kw: AxiomRequest(self.store, *a, **kw)



class SiteConfiguration(Item):
    """
    Configuration object for a Mantissa HTTP server.
    """
    powerupInterfaces = (ISiteURLGenerator, IProtocolFactoryFactory)
    implements(*powerupInterfaces)

    loginSystem = dependsOn(LoginSystem)

    # I don't really want this to have a default value at all, but an Item
    # which can't be instantiated with only a store parameter can't be used as
    # a siteRequirement in an Offering.  See #538 about offering configuration.
    # -exarkun
    hostname = text(
        doc="""
        The primary hostname by which this website will be accessible.  This
        will be superceded by a one-to-many relationship in the future,
        allowing a host to have multiple recognized hostnames.  See #2501.
        """, allowNone=False, default=u"localhost")

    httpLog = path(default=None)


    def _root(self, scheme, hostname, portObj, standardPort):
        # TODO - real unicode support (but punycode is so bad)
        if portObj is None:
            return None

        portNumber = portObj.portNumber
        port = portObj.listeningPort

        if hostname is None:
            hostname = self.hostname
        else:
            hostname = hostname.split(':')[0].encode('ascii')

        if portNumber == 0:
            if port is None:
                return None
            else:
                portNumber = port.getHost().port

        # At some future point, we may want to make pathsegs persistently
        # configurable - perhaps scheme and hostname as well - in order to
        # easily support reverse proxying configurations, particularly where
        # Mantissa is being "mounted" somewhere other than /.  See also rootURL
        # which has some overlap with this method (the difference being
        # universal vs absolute URLs - rootURL may want to call cleartextRoot
        # or encryptedRoot in the future).  See #417 and #2309.
        pathsegs = ['']
        if portNumber != standardPort:
            hostname = '%s:%d' % (hostname, portNumber)
        return URL(scheme, hostname, pathsegs)


    def _getPort(self, portType):
        return self.store.findFirst(
            portType, portType.factory == self, default=None)


    def cleartextRoot(self, hostname=None):
        """
        Return a string representing the HTTP URL which is at the root of this
        site.

        @param hostname: An optional unicode string which, if specified, will
            be used as the hostname in the resulting URL, regardless of the
            C{hostname} attribute of this item.
        """
        return self._root('http', hostname, self._getPort(TCPPort), 80)


    def encryptedRoot(self, hostname=None):
        """
        Return a string representing the HTTPS URL which is at the root of this
        site.

        @param hostname: An optional unicode string which, if specified, will
        be used as the hostname in the resulting URL, regardless of the
        C{hostname} attribute of this item.
        """
        return self._root('https', hostname, self._getPort(SSLPort), 443)


    def rootURL(self, request):
        """
        Return the URL for the root of this website which is appropriate to use
        in links generated in response to the given request.

        @type request: L{twisted.web.http.Request}
        @param request: The request which is being responded to.

        @rtype: L{URL}
        @return: The location at which the root of the resource hierarchy for
            this website is available.
        """
        host = request.getHeader('host') or self.hostname
        if ':' in host:
            host = host.split(':', 1)[0]
        if (host == self.hostname or
            host.startswith('www.') and host[len('www.'):] == self.hostname):
            return URL(scheme='', netloc='', pathsegs=[''])
        else:
            if request.isSecure():
                return self.encryptedRoot(self.hostname)
            else:
                return self.cleartextRoot(self.hostname)


    def getFactory(self):
        """
        Create an L{AxiomSite} which supports authenticated and anonymous
        access.
        """
        checkers = [self.loginSystem, AllowAnonymousAccess()]
        guardedRoot = PersistentSessionWrapper(
            self.store,
            Portal(self.loginSystem, checkers),
            domains=[self.hostname])
        unguardedRoot = UnguardedWrapper(self.store, guardedRoot)
        securingRoot = SecuringWrapper(self, unguardedRoot)
        logPath = None
        if self.httpLog is not None:
            logPath = self.httpLog.path
        return AxiomSite(self.store, securingRoot, logPath=logPath)




class UnguardedWrapper(record('siteStore guardedRoot')):
    """
    Resource which wraps the top of the Mantissa resource hierarchy and adds
    resources which must be available to all clients all the time.

    @ivar siteStore: The site L{Store} for the resource hierarchy being
        wrapped.
    @ivar guardedRoot: The root resource of the hierarchy being wrapped.
    """
    implements(IResource)

    def child_live(self, ctx):
        """
        The 'live' namespace is reserved for Athena LivePages.  By default in
        Athena applications these resources are child resources of whatever URL
        the live page ends up at, but this root URL is provided so that the
        reliable message queuing logic can sidestep all resource traversal, and
        therefore, all database queries.  This is an important optimization,
        since Athena's implementation assumes that HTTP hits to the message
        queue resource are cheap.

        @return: an L{athena.LivePage} instance.
        """
        return LivePage(None, None)


    def child___jsmodule__(self, ignored):
        """
        __jsmodule__ child which provides support for Athena applications to
        use a centralized URL to deploy JavaScript code.
        """
        return theHashModuleProvider


    def child_Mantissa(self, ctx):
        """
        Serve files from C{xmantissa/static/} at the URL C{/Mantissa}.
        """
        # Cheating!  It *looks* like there's an app store, but there isn't
        # really, because this is the One Store To Bind Them All.

        # We shouldn't really cheat here.  It would be better to have one real
        # Mantissa offering that has its static content served up the same way
        # every other offering's content is served.  There's already a
        # /static/mantissa-static/.  This child definition is only still here
        # because some things still reference this URL.  For example,
        # JavaScript files and any CSS file which uses Mantissa content but is
        # from an Offering which does not provide a staticContentPath.
        # See #2469.  -exarkun
        return File(FilePath(__file__).sibling("static").path)


    def child_static(self, context):
        """
        Serve a container page for static content for Mantissa and other
        offerings.
        """
        offeringTech = IOfferingTechnician(self.siteStore)
        installedOfferings = offeringTech.getInstalledOfferings()
        offeringsWithContent = dict([
                (offering.name, offering.staticContentPath)
                for offering
                in installedOfferings.itervalues()
                if offering.staticContentPath])

        # If you wanted to do CSS rewriting for all CSS files served beneath
        # /static/, you could do it by passing a processor for ".css" here.
        # eg:
        #
        # website = IResource(self.store)
        # factory = StylesheetFactory(
        #     offeringsWithContent.keys(), website.rootURL)
        # StaticContent(offeringsWithContent, {
        #               ".css": factory.makeStylesheetResource})
        return StaticContent(offeringsWithContent, {})


    def locateChild(self, context, segments):
        """
        Return a statically defined child or a child defined by a sessionless
        site root plugin or an avatar from guard.
        """
        shortcut = getattr(self, 'child_' + segments[0], None)
        if shortcut:
            res = shortcut(context)
            if res is not None:
                return res, segments[1:]

        req = IRequest(context)
        for plg in self.siteStore.powerupsFor(ISessionlessSiteRootPlugin):
            spr = getattr(plg, 'sessionlessProduceResource', None)
            if spr is not None:
                childAndSegments = spr(req, segments)
            else:
                childAndSegments = plg.resourceFactory(segments)
            if childAndSegments is not None:
                return childAndSegments

        return self.guardedRoot.locateChild(context, segments)



class SecuringWrapper(record('urlGenerator wrappedResource')):
    """
    Resource wrapper which enforces HTTPS under certain circumstances.

    If a child resource ultimately obtained from this wrapper is going to be
    rendered, if it has a C{needsSecure} attribute set to a true value and
    there is an HTTPS server available and the request was made over HTTP, the
    client will be redirected to an HTTPS location first.  Otherwise the
    resource will be rendered as usual.

    @ivar urlGenerator: The L{ISiteURLGenerator} which will provide an HTTPS
        URL.
    @ivar wrappedResource: The resource which will be used to locate children
        or which will be rendered.
    """
    implements(IResource)

    def locateChild(self, context, segments):
        """
        Unwrap the wrapped resource if HTTPS is already being used, otherwise
        wrap it in a helper which will preserve the wrapping all the way down
        to the final resource.
        """
        request = IRequest(context)
        if request.isSecure():
            return self.wrappedResource, segments
        return _SecureWrapper(self.urlGenerator, self.wrappedResource), segments


    def renderHTTP(self, context):
        """
        Render the wrapped resource if HTTPS is already being used, otherwise
        invoke a helper which may generate a redirect.
        """
        request = IRequest(context)
        if request.isSecure():
            renderer = self.wrappedResource
        else:
            renderer = _SecureWrapper(self.urlGenerator, self.wrappedResource)
        return renderer.renderHTTP(context)



class _SecureWrapper(record('urlGenerator wrappedResource')):
    """
    Helper class for L{SecuringWrapper} which preserves wrapping to the
    ultimate resource and which implements HTTPS redirect logic if necessary.

    @ivar urlGenerator: The L{ISiteURLGenerator} which will provide an HTTPS
        URL.
    @ivar wrappedResource: The resource which will be used to locate children
        or which will be rendered.
    """
    implements(IResource)

    def __init__(self, *a, **k):
        super(_SecureWrapper, self).__init__(*a, **k)
        self.wrappedResource = IResource(self.wrappedResource)


    def locateChild(self, context, segments):
        """
        Delegate child lookup to the wrapped resource but wrap whatever results
        in another instance of this wrapper.
        """
        childDeferred = maybeDeferred(
            self.wrappedResource.locateChild, context, segments)
        def childLocated((resource, segments)):
            if (resource, segments) == NotFound:
                return NotFound
            return _SecureWrapper(self.urlGenerator, resource), segments
        childDeferred.addCallback(childLocated)
        return childDeferred


    def renderHTTP(self, context):
        """
        Check to see if the wrapped resource wants to be rendered over HTTPS
        and generate a redirect if this is so, if HTTPS is available, and if
        the request is not already over HTTPS.
        """
        if getattr(self.wrappedResource, 'needsSecure', False):
            request = IRequest(context)
            url = self.urlGenerator.encryptedRoot()
            if url is not None:
                for seg in request.prepath:
                    url = url.child(seg)
                return url
        return self.wrappedResource.renderHTTP(context)



class StaticContent(record('staticPaths processors')):
    """
    Parent resource for all static content provided by all installed offerings.

    This resource has a child by the name of each offering which declares a
    static content path which serves that path.

    @ivar staticPaths: A C{dict} mapping offering names to L{FilePath}
        instances for each offering which should be able to publish static
        content.

    @ivar processors: A C{dict} mapping extensions (with leading ".") to
        two-argument callables.  These processors will be attached to the
        L{nevow.static.File} returned by C{locateChild}.
    """
    implements(IResource)

    def locateChild(self, context, segments):
        """
        Find the offering with the name matching the first segment and return a
        L{File} for its I{staticContentPath}.
        """
        name = segments[0]
        try:
            staticContent = self.staticPaths[name]
        except KeyError:
            return NotFound
        else:
            resource = File(staticContent.path)
            resource.processors = self.processors
            return resource, segments[1:]
        return NotFound
