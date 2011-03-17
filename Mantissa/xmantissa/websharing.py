# -*- test-case-name: xmantissa.test.test_websharing -*-
# Copyright 2008 Divmod, Inc. See LICENSE file for details
"""
This module provides web-based access to objects shared with the
xmantissa.sharing module.

Users' publicly shared objects are exposed at the url::

    http://your-server/users/<user>@<hostname>/<share-id>

Applications' publicly shared objects are exposed at the url::

    http://your-server/<app-name>/<share-id>

where "app-name" is the name of the offering the application was installed
from.

To share an item publicly, share it with the "everyone" role. To place it at
the root URL of the share location, call L{addDefaultShareID} with its share
ID.

Example::
  sharing.getEveryoneRole(yourItem.store).shareItem(yourItem, shareID=u'bob')

If this is in an app store named 'foo', this object is now shared on the URL
http://your-server/foo/bob. To share it at the root, as
http://your-server/foo/, make it the default::
  websharing.addDefaultShareID(yourItem.store, u'bob', 1)

"""

from zope.interface import implements

from axiom import userbase, attributes
from axiom.item import Item
from axiom.attributes import text, integer

from nevow import inevow, url, rend

from xmantissa.offering import isAppStore

from xmantissa import sharing

class _DefaultShareID(Item):
    """
    Item which holds a default share ID for a user's store.  Default share IDs
    are associated with a priority, and the highest-priority ID identifies the
    share which will be selected if the user browsing a substore doesn't
    provide their own share ID.
    """
    shareID = text(doc="""
    A default share ID for the store this item lives in.
    """, allowNone=False)

    priority = integer(doc="""
    The priority of this default.  Higher means more important.
    """)



def addDefaultShareID(store, shareID, priority):
    """
    Add a default share ID to C{store}, pointing to C{shareID} with a
    priority C{priority}.  The highest-priority share ID identifies the share
    that will be retrieved when a user does not explicitly provide a share ID
    in their URL (e.g. /host/users/username/).

    @param shareID: A share ID.
    @type shareID: C{unicode}

    @param priority: The priority of this default.  Higher means more
    important.
    @type priority: C{int}
    """
    _DefaultShareID(store=store, shareID=shareID, priority=priority)



def getDefaultShareID(store):
    """
    Get the highest-priority default share ID for C{store}.

    @return: the default share ID, or u'' if one has not been set.
    @rtype: C{unicode}
    """
    defaultShareID = store.findFirst(
        _DefaultShareID, sort=_DefaultShareID.priority.desc)
    if defaultShareID is None:
        return u''
    return defaultShareID.shareID



class _ShareURL(url.URL):
    """
    An L{url.URL} subclass which inserts share ID as a path segment in the URL
    just before the first call to L{child} modifies it.
    """
    def __init__(self, shareID, *a, **k):
        """
        @param shareID: The ID of the share we are generating a URL for.
        @type shareID: C{unicode}.
        """
        self._shareID = shareID
        url.URL.__init__(self, *a, **k)


    def child(self, path):
        """
        Override the base implementation to inject the share ID our
        constructor was passed.
        """
        if self._shareID is not None:
            self = url.URL.child(self, self._shareID)
            self._shareID = None
        return url.URL.child(self, path)


    def cloneURL(self, scheme, netloc, pathsegs, querysegs, fragment):
        """
        Override the base implementation to pass along the share ID our
        constructor was passed.
        """
        return self.__class__(
            self._shareID, scheme, netloc, pathsegs, querysegs, fragment)


    # there is no point providing an implementation of any these methods which
    # accepts a shareID argument; they don't really mean anything in this
    # context.

    def fromString(cls, string):
        """
        Override the base implementation to throw L{NotImplementedError}.

        @raises L{NotImplementedError}: always.
        """
        raise NotImplementedError(
            'fromString is not implemented on %r' % (cls.__name__,))
    fromString = classmethod(fromString)


    def fromRequest(cls, req):
        """
        Override the base implementation to throw L{NotImplementedError}.

        @raises L{NotImplementedError}: always.
        """
        raise NotImplementedError(
            'fromRequest is not implemented on %r' % (cls.__name__,))
    fromRequest = classmethod(fromRequest)


    def fromContext(cls, ctx):
        """
        Override the base implementation to throw L{NotImplementedError}.

        @raises L{NotImplementedError}: always.
        """
        raise NotImplementedError(
            'fromContext is not implemented on %r' % (cls.__name__,))
    fromContext = classmethod(fromContext)



def linkTo(sharedProxyOrItem):
    """
    Generate the path part of a URL to link to a share item or its proxy.

    @param sharedProxy: a L{sharing.SharedProxy} or L{sharing.Share}

    @return: a URL object, which when converted to a string will look
        something like '/users/user@host/shareID'.

    @rtype: L{nevow.url.URL}

    @raise: L{RuntimeError} if the store that the C{sharedProxyOrItem} is
        stored in is not accessible via the web, for example due to the fact
        that the store has no L{LoginMethod} objects to indicate who it is
        owned by.
    """
    if isinstance(sharedProxyOrItem, sharing.SharedProxy):
        userStore = sharing.itemFromProxy(sharedProxyOrItem).store
    else:
        userStore = sharedProxyOrItem.store
    appStore = isAppStore(userStore)
    if appStore:
        # This code-path should be fixed by #2703; PublicWeb is deprecated.
        from xmantissa.publicweb import PublicWeb
        substore = userStore.parent.getItemByID(userStore.idInParent)
        pw = userStore.parent.findUnique(PublicWeb, PublicWeb.application == substore)
        path = [pw.prefixURL.encode('ascii')]
    else:
        for lm in userbase.getLoginMethods(userStore):
            if lm.internal:
                path = ['users', lm.localpart.encode('ascii')]
                break
        else:
            raise RuntimeError(
                "Shared item is in a user store with no"
                " internal username -- can't generate a link.")
    if (sharedProxyOrItem.shareID == getDefaultShareID(userStore)):
        shareID = sharedProxyOrItem.shareID
        path.append('')
    else:
        shareID = None
        path.append(sharedProxyOrItem.shareID)
    return _ShareURL(shareID, scheme='', netloc='', pathsegs=path)



def _storeFromUsername(store, username):
    """
    Find the user store of the user with username C{store}

    @param store: site-store
    @type store: L{axiom.store.Store}

    @param username: the name a user signed up with
    @type username: C{unicode}

    @rtype: L{axiom.store.Store} or C{None}
    """
    lm = store.findUnique(
            userbase.LoginMethod,
            attributes.AND(
                userbase.LoginMethod.localpart == username,
                userbase.LoginMethod.internal == True),
            default=None)
    if lm is not None:
        return lm.account.avatars.open()



class UserIndexPage(object):
    """
    This is the resource accessible at "/users"

    See L{xmantissa.publicweb.AnonymousSite.child_users} for the integration
    point with the rest of the system.
    """
    implements(inevow.IResource)

    def __init__(self, loginSystem, webViewer):
        """
        Create a UserIndexPage which draws users from a given
        L{userbase.LoginSystem}.

        @param loginSystem: the login system to look up users in.
        @type loginSystem: L{userbase.LoginSystem}
        """
        self.loginSystem = loginSystem
        self.webViewer = webViewer


    def locateChild(self, ctx, segments):
        """
        Retrieve a L{SharingIndex} for a particular user, or rend.NotFound.
        """
        store = _storeFromUsername(
            self.loginSystem.store, segments[0].decode('utf-8'))
        if store is None:
            return rend.NotFound
        return (SharingIndex(store, self.webViewer), segments[1:])


    def renderHTTP(self, ctx):
        """
        Return a sarcastic string to the user when they try to list the index of
        users by hitting '/users' by itself.

        (This should probably do something more helpful.  There might be a very
        large number of users so returning a simple listing is infeasible, but
        one might at least present a search page or something.)
        """
        return 'Keep trying.  You are almost there.'



class SharingIndex(object):
    """
    A SharingIndex is an http resource which provides a view onto a user's
    store, for another user.
    """
    implements(inevow.IResource)

    def __init__(self, userStore, webViewer):
        """
        Create a SharingIndex.

        @param userStore: an L{axiom.store.Store} to be viewed.

        @param webViewer: an L{IWebViewer} which represents the
        viewer.
        """
        self.userStore = userStore
        self.webViewer = webViewer


    def renderHTTP(self, ctx):
        """
        When this resource itself is rendered, redirect to the default shared
        item.
        """
        return url.URL.fromContext(ctx).child('')


    def locateChild(self, ctx, segments):
        """
        Look up a shared item for the role viewing this SharingIndex and return a
        L{PublicAthenaLivePage} containing that shared item's fragment to the
        user.

        These semantics are UNSTABLE.  This method is adequate for simple uses,
        but it should be expanded in the future to be more consistent with
        other resource lookups.  In particular, it should allow share
        implementors to adapt their shares to L{IResource} directly rather than
        L{INavigableFragment}, to allow for simpler child dispatch.

        @param segments: a list of strings, the first of which should be the
        shareID of the desired item.

        @param ctx: unused.

        @return: a L{PublicAthenaLivePage} wrapping a customized fragment.
        """
        shareID = segments[0].decode('utf-8')

        role = self.webViewer.roleIn(self.userStore)

        # if there is an empty segment
        if shareID == u'':
            # then we want to return the default share.  if we find one, then
            # let's use that
            defaultShareID = getDefaultShareID(self.userStore)
            try:
                sharedItem = role.getShare(defaultShareID)
            except sharing.NoSuchShare:
                return rend.NotFound
        # otherwise the user is trying to access some other share
        else:
            # let's see if it's a real share
            try:
                sharedItem = role.getShare(shareID)
            # oops it's not
            except sharing.NoSuchShare:
                return rend.NotFound

        return (self.webViewer.wrapModel(sharedItem),
                segments[1:])
