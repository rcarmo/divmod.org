# Copyright 2008 Divmod, Inc. See LICENSE file for details
# -*- test-case-name: xmantissa.test.test_webapp,xmantissa.test.test_publicweb,xmantissa.test.test_website -*-

"""
This unfortunate module exists to contain code that would create an ugly
dependency loop if it were somewhere else.
"""
from zope.interface import implements

from twisted.cred.portal import IRealm

from epsilon.structlike import record

from axiom.userbase import getDomainNames

from nevow import athena
from nevow.rend import NotFound
from nevow.inevow import IResource, IRequest

from xmantissa.ixmantissa import (IWebViewer, INavigableFragment,
                                  ISiteRootPlugin)

from xmantissa.websharing import UserIndexPage

from xmantissa.error import CouldNotLoadFromThemes


class WebViewerHelper(object):
    """
    This is a mixin for the common logic in the two providers of
    L{IWebViewer} included with Mantissa,
    L{xmantissa.publicweb._AnonymousWebViewer} and
    L{xmantissa.webapp._AuthenticatedWebViewer}.

    @ivar _getDocFactory: a 1-arg callable which returns a nevow loader.

    @ivar _preferredThemes: a 0-arg callable which returns a list of nevow
        themes.
    """
    def __init__(self, _getDocFactory, _preferredThemes):
        """
        """
        self._getDocFactory = _getDocFactory
        self._preferredThemes = _preferredThemes


    def _wrapNavFrag(self, fragment, useAthena):
        """
        Subclasses must implement this to wrap a fragment.

        @param fragment: an L{INavigableFragment} provider that should be
            wrapped in the resulting page.

        @param useAthena: Whether the resulting L{IResource} should be a
            L{LivePage}.

        @type useAthena: L{bool}

        @return: a fragment to display to the user.

        @rtype: L{IResource}
        """


    def wrapModel(self, model):
        """
        Converts application-provided model objects to L{IResource} providers.
        """
        res = IResource(model, None)
        if res is None:
            frag = INavigableFragment(model)
            fragmentName = getattr(frag, 'fragmentName', None)
            if fragmentName is not None:
                fragDocFactory = self._getDocFactory(fragmentName)
                if fragDocFactory is not None:
                    frag.docFactory = fragDocFactory
            if frag.docFactory is None:
                raise CouldNotLoadFromThemes(frag, self._preferredThemes())
            useAthena = isinstance(frag, (athena.LiveFragment, athena.LiveElement))
            return self._wrapNavFrag(frag, useAthena)
        else:
            return res



class MantissaViewHelper(object):
    """
    This is the superclass of all Mantissa resources which act as a wrapper
    around an L{INavigableFragment} provider.  This must be mixed in to some
    hierarchy with a C{locateChild} method, since it expects to cooperate in
    such a hierarchy.

    Due to infelicities in the implementation of some (pre-existing)
    subclasses, there is no __init__; but subclasses must set the 'fragment'
    attribute in theirs.
    """
    fragment = None

    def locateChild(self, ctx, segments):
        """
        Attempt to locate the child via the '.fragment' attribute, then fall
        back to normal locateChild behavior.
        """
        if self.fragment is not None:
            # There are still a bunch of bogus subclasses of this class, which
            # are used in a variety of distasteful ways.  'fragment' *should*
            # always be set to something that isn't None, but there's no way to
            # make sure that it will be for the moment.  Every effort should be
            # made to reduce public use of subclasses of this class (instead
            # preferring to wrap content objects with
            # IWebViewer.wrapModel()), so that the above check can be
            # removed. -glyph
            lc = getattr(self.fragment, 'locateChild', None)
            if lc is not None:
                x = lc(ctx, segments)
                if x is not NotFound:
                    return x
        return super(MantissaViewHelper, self).locateChild(ctx, segments)



class SiteRootMixin(object):
    """
    Common functionality for L{AnonymousSite} and L{WebSite}.
    """

    def locateChild(self, context, segments):
        """
        Return a statically defined child or a child defined by a site root
        plugin or an avatar from guard.
        """
        request = IRequest(context)
        webViewer = IWebViewer(self.store, None)
        childAndSegments = self.siteProduceResource(request, segments, webViewer)
        if childAndSegments is not None:
            return childAndSegments
        return NotFound


    # IMantissaSite
    def siteProduceResource(self, req, segments, webViewer):
        """
        Retrieve a child resource and segments from rootChild_ methods on this
        object and SiteRootPlugins.

        @return: a 2-tuple of (resource, segments), suitable for return from
        locateChild.

        @param req: an L{IRequest} provider.

        @param segments: a tuple of L{str}s, the segments from the request.

        @param webViewer: an L{IWebViewer}, to be propagated through the child
        lookup process.
        """

        # rootChild_* is not the same as child_, because its signature is
        # different.  Maybe this should be done some other way.
        shortcut = getattr(self, 'rootChild_' + segments[0], None)
        if shortcut:
            res = shortcut(req, webViewer)
            if res is not None:
                return res, segments[1:]

        for plg in self.store.powerupsFor(ISiteRootPlugin):
            produceResource = getattr(plg, 'produceResource', None)
            if produceResource is not None:
                childAndSegments = produceResource(req, segments, webViewer)
            else:
                childAndSegments = plg.resourceFactory(segments)
            if childAndSegments is not None:
                return childAndSegments
        return None


    # IPowerupIndirector
    def indirect(self, interface):
        """
        Create a L{VirtualHostWrapper} so it can have the first chance to
        handle web requests.
        """
        if interface is IResource:
            siteStore = self.store.parent
            if self.store.parent is None:
                siteStore = self.store
            return VirtualHostWrapper(
                siteStore,
                IWebViewer(self.store),
                self)
        return self



class VirtualHostWrapper(record('siteStore webViewer wrapped')):
    """
    Resource wrapper which implements per-user virtual subdomains.  This should
    be wrapped around any resource which sits at the root of the hierarchy.  It
    will examine requests for their hostname and, when appropriate, redirect
    handling of the query to the appropriate sharing resource.

    @type siteStore: L{Store}
    @ivar siteStore: The site store which will be queried to determine which
        hostnames are associated with this server.

    @type webViewer: L{IWebViewer}
    @ivar webViewer: The web viewer representing the user.

    @type wrapped: L{IResource} provider
    @ivar wrapped: A resource to which traversal will be delegated if the
        request is not for a user subdomain.
    """
    implements(IResource)

    def subdomain(self, hostname):
        """
        Determine of which known domain the given hostname is a subdomain.

        @return: A two-tuple giving the subdomain part and the domain part or
            C{None} if the domain is not a subdomain of any known domain.
        """
        hostname = hostname.split(":")[0]
        for domain in getDomainNames(self.siteStore):
            if hostname.endswith("." + domain):
                username = hostname[:-len(domain) - 1]
                if username != "www":
                    return username, domain
        return None


    def locateChild(self, context, segments):
        """
        Delegate dispatch to a sharing resource if the request is for a user
        subdomain, otherwise fall back to the wrapped resource's C{locateChild}
        implementation.
        """
        request = IRequest(context)
        hostname = request.getHeader('host')

        info = self.subdomain(hostname)
        if info is not None:
            username, domain = info
            index = UserIndexPage(IRealm(self.siteStore),
                                  self.webViewer)
            resource = index.locateChild(None, [username])[0]
            return resource, segments
        return self.wrapped.locateChild(context, segments)
