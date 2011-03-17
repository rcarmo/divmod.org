# -*- test-case-name: xmantissa.test.test_sharing -*-

"""
This module provides various abstractions for sharing public data in Axiom.
"""

import os
import warnings

from zope.interface import implementedBy, directlyProvides, Interface

from twisted.python.reflect import qual, namedAny
from twisted.protocols.amp import Argument, Box, parseString

from epsilon.structlike import record

from axiom import userbase
from axiom.item import Item
from axiom.attributes import reference, text, AND
from axiom.upgrade import registerUpgrader


ALL_IMPLEMENTED_DB = u'*'
ALL_IMPLEMENTED = object()


class NoSuchShare(Exception):
    """
    User requested an object that doesn't exist, was not allowed.
    """



class ConflictingNames(Exception):
    """
    The same name was defined in two separate interfaces.
    """



class RoleRelationship(Item):
    """
    RoleRelationship is a bridge record linking member roles with group roles
    that they are members of.
    """
    schemaVersion = 1
    typeName = 'sharing_relationship'

    member = reference(
        doc="""
        This is a reference to a L{Role} which is a member of my 'group' attribute.
        """)

    group = reference(
        doc="""
        This is a reference to a L{Role} which represents a group that my 'member'
        attribute is a member of.
        """)


def _entuple(r):
    """
    Convert a L{record} to a tuple.
    """
    return tuple(getattr(r, n) for n in r.__names__)



class Identifier(record('shareID localpart domain')):
    """
    A fully-qualified identifier for an entity that can participate in a
    message either as a sender or a receiver.
    """

    @classmethod
    def fromSharedItem(cls, sharedItem):
        """
        Return an instance of C{cls} derived from the given L{Item} that has
        been shared.

        Note that this API does not provide any guarantees of which result it
        will choose.  If there are are multiple possible return values, it will
        select and return only one.  Items may be shared under multiple
        L{shareID}s.  A user may have multiple valid account names.  It is
        sometimes impossible to tell from context which one is appropriate, so
        if your application has another way to select a specific shareID you
        should use that instead.

        @param sharedItem: an L{Item} that should be shared.

        @return: an L{Identifier} describing the C{sharedItem} parameter.

        @raise L{NoSuchShare}: if the given item is not shared or its store
        does not contain any L{LoginMethod} items which would identify a user.
        """
        localpart = None
        for (localpart, domain) in userbase.getAccountNames(sharedItem.store):
            break
        if localpart is None:
            raise NoSuchShare()
        for share in sharedItem.store.query(Share,
                                            Share.sharedItem == sharedItem):
            break
        else:
            raise NoSuchShare()
        return cls(
            shareID=share.shareID,
            localpart=localpart, domain=domain)


    def __cmp__(self, other):
        """
        Compare this L{Identifier} to another object.
        """
        # Note - might be useful to have this usable by arbitrary L{record}
        # objects.  It can't be the default, but perhaps a mixin?
        if not isinstance(other, Identifier):
            return NotImplemented
        return cmp(_entuple(self), _entuple(other))



class IdentifierArgument(Argument):
    """
    An AMP argument which can serialize and deserialize an L{Identifier}.
    """

    def toString(self, obj):
        """
        Convert the given L{Identifier} to a string.
        """
        return Box(shareID=obj.shareID.encode('utf-8'),
                   localpart=obj.localpart.encode('utf-8'),
                   domain=obj.domain.encode('utf-8')).serialize()


    def fromString(self, inString):
        """
        Convert the given string to an L{Identifier}.
        """
        box = parseString(inString)[0]
        return Identifier(shareID=box['shareID'].decode('utf-8'),
                          localpart=box['localpart'].decode('utf-8'),
                          domain=box['domain'].decode('utf-8'))



class Role(Item):
    """
    A Role is an identifier for a group or individual which has certain
    permissions.

    Items shared within the sharing system are always shared with a particular
    role.
    """

    schemaVersion = 1
    typeName = 'sharing_role'

    externalID = text(
        doc="""
        This is the external identifier which the role is known by.  This field is
        used to associate users with their primary role.  If a user logs in as
        bob@divmod.com, the sharing system will associate his primary role with
        the pre-existing role with the externalID of 'bob@divmod.com', or
        'Everybody' if no such role exists.

        For group roles, the externalID is not currently used except as a
        display identifier.  Group roles should never have an '@' character in
        them, however, to avoid confusion with user roles.
        """, allowNone=False)

    # XXX TODO: In addition to the externalID, we really need to have something
    # that identifies what protocol the user for the role is expected to log in
    # as, and a way to identify the way that their role was associated with
    # their login.  For example, it might be acceptable for some security
    # applications (e.g. spam prevention) to simply use an HTTP cookie.  For
    # others (accounting database manipulation) it should be possible to
    # require more secure methods of authentication, like a signed client
    # certificate.

    description = text(
        doc="""
        This is a free-form descriptive string for use by users to explain the
        purpose of the role.  Since the externalID is used by security logic
        and must correspond to a login identifier, this can be used to hold a
        user's real name.
        """)


    def becomeMemberOf(self, groupRole):
        """
        Instruct this (user or group) Role to become a member of a group role.

        @param groupRole: The role that this group should become a member of.
        """
        self.store.findOrCreate(RoleRelationship,
                                group=groupRole,
                                member=self)


    def allRoles(self, memo=None):
        """
        Identify all the roles that this role is authorized to act as.

        @param memo: used only for recursion.  Do not pass this.

        @return: an iterator of all roles that this role is a member of,
        including itself.
        """
        if memo is None:
            memo = set()
        elif self in memo:
            # this is bad, but we have successfully detected and prevented the
            # only really bad symptom, an infinite loop.
            return
        memo.add(self)
        yield self
        for groupRole in self.store.query(Role,
                                          AND(RoleRelationship.member == self,
                                              RoleRelationship.group == Role.storeID)):
            for roleRole in groupRole.allRoles(memo):
                yield roleRole


    def shareItem(self, sharedItem, shareID=None, interfaces=ALL_IMPLEMENTED):
        """
        Share an item with this role.  This provides a way to expose items to
        users for later retrieval with L{Role.getShare}.

        @param sharedItem: an item to be shared.

        @param shareID: a unicode string.  If provided, specify the ID under which
        the shared item will be shared.

        @param interfaces: a list of Interface objects which specify the methods
        and attributes accessible to C{toRole} on C{sharedItem}.

        @return: a L{Share} which records the ability of the given role to
        access the given item.
        """
        if shareID is None:
            shareID = genShareID(sharedItem.store)
        return Share(store=self.store,
                     shareID=shareID,
                     sharedItem=sharedItem,
                     sharedTo=self,
                     sharedInterfaces=interfaces)


    def getShare(self, shareID):
        """
        Retrieve a proxy object for a given shareID, previously shared with
        this role or one of its group roles via L{Role.shareItem}.

        @return: a L{SharedProxy}.  This is a wrapper around the shared item
        which only exposes those interfaces explicitly allowed for the given
        role.

        @raise: L{NoSuchShare} if there is no item shared to the given role for
        the given shareID.
        """
        shares = list(
            self.store.query(Share,
                             AND(Share.shareID == shareID,
                                 Share.sharedTo.oneOf(self.allRoles()))))
        interfaces = []
        for share in shares:
            interfaces += share.sharedInterfaces
        if shares:
            return SharedProxy(shares[0].sharedItem,
                               interfaces,
                               shareID)
        raise NoSuchShare()


    def asAccessibleTo(self, query):
        """
        @param query: An Axiom query describing the Items to retrieve, which this
        role can access.
        @type query: an L{iaxiom.IQuery} provider.

        @return: an iterable which yields the shared proxies that are available
        to the given role, from the given query.
        """
        # XXX TODO #2371: this method really *should* be returning an L{IQuery}
        # provider as well, but that is kind of tricky to do.  Currently, doing
        # queries leaks authority, because the resulting objects have stores
        # and "real" items as part of their interface; having this be a "real"
        # query provider would obviate the need to escape the L{SharedProxy}
        # security constraints in order to do any querying.
        allRoles = list(self.allRoles())
        count = 0
        unlimited = query.cloneQuery(limit=None)
        for result in unlimited:
            allShares = list(query.store.query(
                    Share,
                    AND(Share.sharedItem == result,
                        Share.sharedTo.oneOf(allRoles))))
            interfaces = []
            for share in allShares:
                interfaces += share.sharedInterfaces
            if allShares:
                count += 1
                yield SharedProxy(result, interfaces, allShares[0].shareID)
                if count == query.limit:
                    return




class _really(object):
    """
    A dynamic proxy for dealing with 'private' attributes on L{SharedProxy},
    which overrides C{__getattribute__} itself.  This is pretty syntax to avoid
    ugly references to __dict__ and super and object.__getattribute__() in
    dynamic proxy implementations.
    """

    def __init__(self, orig):
        """
        Create a _really object with a dynamic proxy.

        @param orig: an object that overrides __getattribute__, probably
        L{SharedProxy}.
        """
        self.orig = orig


    def __setattr__(self, name, value):
        """
        Set an attribute on my original, unless my original has not yet been set,
        in which case set it on me.
        """
        try:
            orig = object.__getattribute__(self, 'orig')
        except AttributeError:
            object.__setattr__(self, name, value)
        else:
            object.__setattr__(orig, name, value)


    def __getattribute__(self, name):
        """
        Get an attribute present on my original using L{object.__getattribute__},
        not the overridden version.
        """
        return object.__getattribute__(object.__getattribute__(self, 'orig'),
                                       name)



ALLOWED_ON_PROXY = ['__provides__', '__dict__']

class SharedProxy(object):
    """
    A shared proxy is a dynamic proxy which provides exposes methods and
    attributes declared by shared interfaces on a given Item.  These are
    returned from L{Role.getShare} and yielded from L{Role.asAccessibleTo}.

    Shared proxies are unlike regular items because they do not have 'storeID'
    or 'store' attributes (unless explicitly exposed).  They are designed
    to make security easy to implement: if you have a shared proxy, you can
    access any attribute or method on it without having to do explicit
    permission checks.

    If you *do* want to perform an explicit permission check, for example, to
    render some UI associated with a particular permission, it can be performed
    as a functionality check instead.  For example, C{if getattr(proxy,
    'feature', None) is None:} or, more formally,
    C{IFeature.providedBy(proxy)}.  If your interfaces are all declared and
    implemented properly everywhere, these checks will work both with shared
    proxies and with the original Items that they represent (but of course, the
    original Items will always provide all of their features).

    (Note that object.__getattribute__ still lets you reach inside any object,
    so don't imagine this makes you bulletproof -- you have to cooperate with
    it.)
    """

    def __init__(self, sharedItem, sharedInterfaces, shareID):
        """
        Create a shared proxy for a given item.

        @param sharedItem: The original item that was shared.

        @param sharedInterfaces: a list of interfaces which C{sharedItem}
        implements that this proxy should allow access to.

        @param shareID: the external identifier that the shared item was shared
        as.
        """
        rself = _really(self)
        rself._sharedItem = sharedItem
        rself._shareID = shareID
        rself._adapterCache = {}
        # Drop all duplicate shared interfaces.
        uniqueInterfaces = list(sharedInterfaces)
        # XXX there _MUST_ Be a better algorithm for this
        for left in sharedInterfaces:
            for right in sharedInterfaces:
                if left.extends(right) and right in uniqueInterfaces:
                    uniqueInterfaces.remove(right)
        for eachInterface in uniqueInterfaces:
            if not eachInterface.providedBy(sharedItem):
                impl = eachInterface(sharedItem, None)
                if impl is not None:
                    rself._adapterCache[eachInterface] = impl
        rself._sharedInterfaces = uniqueInterfaces
        # Make me look *exactly* like the item I am proxying for, at least for
        # the purposes of adaptation
        # directlyProvides(self, providedBy(sharedItem))
        directlyProvides(self, uniqueInterfaces)


    def __repr__(self):
        """
        Return a pretty string representation of this shared proxy.
        """
        rself = _really(self)
        return 'SharedProxy(%r, %r, %r)' % (
            rself._sharedItem,
            rself._sharedInterfaces,
            rself._shareID)


    def __getattribute__(self, name):
        """
        @return: attributes from my shared item, present in the shared interfaces
        list for this proxy.

        @param name: the name of the attribute to retrieve.

        @raise AttributeError: if the attribute was not found or access to it was
        denied.
        """
        if name in ALLOWED_ON_PROXY:
            return object.__getattribute__(self, name)
        rself = _really(self)
        if name == 'sharedInterfaces':
            return rself._sharedInterfaces
        elif name == 'shareID':
            return rself._shareID
        for iface in rself._sharedInterfaces:
            if name in iface:
                if iface in rself._adapterCache:
                    return getattr(rself._adapterCache[iface], name)
                return getattr(rself._sharedItem, name)
        raise AttributeError("%r has no attribute %r" % (self, name))


    def __setattr__(self, name, value):
        """
        Set an attribute on the shared item.  If the name of the attribute is in
        L{ALLOWED_ON_PROXY}, set it on this proxy instead.

        @param name: the name of the attribute to set

        @param value: the value of the attribute to set

        @return: None
        """
        if name in ALLOWED_ON_PROXY:
            self.__dict__[name] = value
        else:
            raise AttributeError("unsettable: "+repr(name))



def _interfacesToNames(interfaces):
    """
    Convert from a list of interfaces to a unicode string of names suitable for
    storage in the database.

    @param interfaces: an iterable of Interface objects.

    @return: a unicode string, a comma-separated list of names of interfaces.

    @raise ConflictingNames: if any of the names conflict: see
    L{_checkConflictingNames}.
    """
    if interfaces is ALL_IMPLEMENTED:
        names = ALL_IMPLEMENTED_DB
    else:
        _checkConflictingNames(interfaces)
        names = u','.join(map(qual, interfaces))
    return names



class Share(Item):
    """
    A Share is a declaration that users with a given role can access a given
    set of functionality, as described by an Interface object.

    They should be created with L{Role.shareItem} and retrieved with
    L{Role.asAccessibleTo} and L{Role.getShare}.
    """

    schemaVersion = 2
    typeName = 'sharing_share'

    shareID = text(
        doc="""
        The shareID is the externally-visible identifier for this share.  It is
        free-form text, which users may enter to access this share.

        Currently the only concrete use of this attribute is in HTTP[S] URLs, but
        in the future it will be used in menu entries.
        """,
        allowNone=False)

    sharedItem = reference(
        doc="""
        The sharedItem attribute is a reference to the item which is being
        provided.
        """,
        allowNone=False,
        whenDeleted=reference.CASCADE)

    sharedTo = reference(
        doc="""
        The sharedTo attribute is a reference to the Role which this item is shared
        with.
        """,
        allowNone=False)

    sharedInterfaceNames = text(
        doc="""
        This is an internal implementation detail of the sharedInterfaces
        attribute.
        """,
        allowNone=False)


    def __init__(self, **kw):
        """
        Create a share.

        Consider this interface private; use L{shareItem} instead.
        """
        # XXX TODO: All I really want to do here is to have enforcement of
        # allowNone happen at the _end_ of __init__; axiom should probably do
        # that by default, since there are several __init__s like this which
        # don't really do anything scattered throughout the codebase.
        kw['sharedInterfaceNames'] = _interfacesToNames(kw.pop('sharedInterfaces'))
        super(Share, self).__init__(**kw)


    def sharedInterfaces():
        """
        This attribute is the public interface for code which wishes to discover
        the list of interfaces allowed by this Share.  It is a list of
        Interface objects.
        """
        def get(self):
            if not self.sharedInterfaceNames:
                return ()
            if self.sharedInterfaceNames == ALL_IMPLEMENTED_DB:
                I = implementedBy(self.sharedItem.__class__)
                L = list(I)
                T = tuple(L)
                return T
            else:
                return tuple(map(namedAny, self.sharedInterfaceNames.split(u',')))
        def set(self, newValue):
            self.sharedAttributeNames = _interfacesToNames(newValue)
        return get, set

    sharedInterfaces = property(
        doc=sharedInterfaces.__doc__,
        *sharedInterfaces())



def upgradeShare1to2(oldShare):
    "Upgrader from Share version 1 to version 2."
    sharedInterfaces = []
    attrs = set(oldShare.sharedAttributeNames.split(u','))
    for iface in implementedBy(oldShare.sharedItem.__class__):
        if set(iface) == attrs or attrs == set('*'):
            sharedInterfaces.append(iface)

    newShare = oldShare.upgradeVersion('sharing_share', 1, 2,
                                       shareID=oldShare.shareID,
                                       sharedItem=oldShare.sharedItem,
                                       sharedTo=oldShare.sharedTo,
                                       sharedInterfaces=sharedInterfaces)
    return newShare


registerUpgrader(upgradeShare1to2, 'sharing_share', 1, 2)



def genShareID(store):
    """
    Generate a new, randomized share-ID for use as the default of shareItem, if
    none is specified.

    @return: a random share-ID.

    @rtype: unicode.
    """
    return unicode(os.urandom(16).encode('hex'), 'ascii')



def getEveryoneRole(store):
    """
    Get a base 'Everyone' role for this store, which is the role that every
    user, including the anonymous user, has.
    """
    return store.findOrCreate(Role, externalID=u'Everyone')



def getAuthenticatedRole(store):
    """
    Get the base 'Authenticated' role for this store, which is the role that is
    given to every user who is explicitly identified by a non-anonymous
    username.
    """
    def tx():
        def addToEveryone(newAuthenticatedRole):
            newAuthenticatedRole.becomeMemberOf(getEveryoneRole(store))
            return newAuthenticatedRole
        return store.findOrCreate(Role, addToEveryone, externalID=u'Authenticated')
    return store.transact(tx)



def getPrimaryRole(store, primaryRoleName, createIfNotFound=False):
    """
    Get Role object corresponding to an identifier name.  If the role name
    passed is the empty string, it is assumed that the user is not
    authenticated, and the 'Everybody' role is primary.  If the role name
    passed is non-empty, but has no corresponding role, the 'Authenticated'
    role - which is a member of 'Everybody' - is primary.  Finally, a specific
    role can be primary if one exists for the user's given credentials, that
    will automatically always be a member of 'Authenticated', and by extension,
    of 'Everybody'.

    @param primaryRoleName: a unicode string identifying the role to be
    retrieved.  This corresponds to L{Role}'s externalID attribute.

    @param createIfNotFound: a boolean.  If True, create a role for the given
    primary role name if no exact match is found.  The default, False, will
    instead retrieve the 'nearest match' role, which can be Authenticated or
    Everybody depending on whether the user is logged in or not.

    @return: a L{Role}.
    """
    if not primaryRoleName:
        return getEveryoneRole(store)
    ff = store.findUnique(Role, Role.externalID == primaryRoleName, default=None)
    if ff is not None:
        return ff
    authRole = getAuthenticatedRole(store)
    if createIfNotFound:
        role = Role(store=store,
                    externalID=primaryRoleName)
        role.becomeMemberOf(authRole)
        return role
    return authRole



def getSelfRole(store):
    """
    Retrieve the Role which corresponds to the user to whom the given store
    belongs.
    """
    return getAccountRole(store, userbase.getAccountNames(store))


def getAccountRole(store, accountNames):
    """
    Retrieve the first Role in the given store which corresponds an account
    name in C{accountNames}.

    Note: the implementation currently ignores all of the values in
    C{accountNames} except for the first.

    @param accountNames: A C{list} of two-tuples of account local parts and
        domains.

    @raise ValueError: If C{accountNames} is empty.

    @rtype: L{Role}
    """
    for (localpart, domain) in accountNames:
        return getPrimaryRole(store, u'%s@%s' % (localpart, domain),
                              createIfNotFound=True)
    raise ValueError("Cannot get named role for unnamed account.")



def shareItem(sharedItem, toRole=None, toName=None, shareID=None,
              interfaces=ALL_IMPLEMENTED):
    """
    Share an item with a given role.  This provides a way to expose items to
    users for later retrieval with L{Role.getShare}.

    This API is slated for deprecation.  Prefer L{Role.shareItem} in new code.

    @param sharedItem: an item to be shared.

    @param toRole: a L{Role} instance which represents the group that has
    access to the given item.  May not be specified if toName is also
    specified.

    @param toName: a unicode string which uniquely identifies a L{Role} in the
    same store as the sharedItem.

    @param shareID: a unicode string.  If provided, specify the ID under which
    the shared item will be shared.

    @param interfaces: a list of Interface objects which specify the methods
    and attributes accessible to C{toRole} on C{sharedItem}.

    @return: a L{Share} which records the ability of the given role to access
    the given item.
    """
    warnings.warn("Use Role.shareItem() instead of sharing.shareItem().",
                  PendingDeprecationWarning,
                  stacklevel=2)
    if toRole is None:
        if toName is not None:
            toRole = getPrimaryRole(sharedItem.store, toName, True)
        else:
            toRole = getEveryoneRole(sharedItem.store)
    return toRole.shareItem(sharedItem, shareID, interfaces)



def _linearize(interface):
    """
    Return a list of all the bases of a given interface in depth-first order.

    @param interface: an Interface object.

    @return: a L{list} of Interface objects, the input in all its bases, in
    subclass-to-base-class, depth-first order.
    """
    L = [interface]
    for baseInterface in interface.__bases__:
        if baseInterface is not Interface:
            L.extend(_linearize(baseInterface))
    return L



def _commonParent(zi1, zi2):
    """
    Locate the common parent of two Interface objects.

    @param zi1: a zope Interface object.

    @param zi2: another Interface object.

    @return: the rightmost common parent of the two provided Interface objects,
    or None, if they have no common parent other than Interface itself.
    """
    shorter, longer = sorted([_linearize(x)[::-1] for x in zi1, zi2],
                             key=len)
    for n in range(len(shorter)):
        if shorter[n] != longer[n]:
            if n == 0:
                return None
            return shorter[n-1]
    return shorter[-1]


def _checkConflictingNames(interfaces):
    """
    Raise an exception if any of the names present in the given interfaces
    conflict with each other.

    @param interfaces: a list of Zope Interface objects.

    @return: None

    @raise ConflictingNames: if any of the attributes of the provided
    interfaces are the same, and they do not have a common base interface which
    provides that name.
    """
    names = {}
    for interface in interfaces:
        for name in interface:
            if name in names:
                otherInterface = names[name]
                parent = _commonParent(interface, otherInterface)
                if parent is None or name not in parent:
                    raise ConflictingNames("%s conflicts with %s over %s" % (
                            interface, otherInterface, name))
            names[name] = interface



def getShare(store, role, shareID):
    """
    Retrieve the accessible facet of an Item previously shared with
    L{shareItem}.

    This method is pending deprecation, and L{Role.getShare} should be
    preferred in new code.

    @param store: an axiom store (XXX must be the same as role.store)

    @param role: a L{Role}, the primary role for a user attempting to retrieve
    the given item.

    @return: a L{SharedProxy}.  This is a wrapper around the shared item which
    only exposes those interfaces explicitly allowed for the given role.

    @raise: L{NoSuchShare} if there is no item shared to the given role for the
    given shareID.
    """
    warnings.warn("Use Role.getShare() instead of sharing.getShare().",
                  PendingDeprecationWarning,
                  stacklevel=2)
    return role.getShare(shareID)



def asAccessibleTo(role, query):
    """
    Return an iterable which yields the shared proxies that are available to
    the given role, from the given query.

    This method is pending deprecation, and L{Role.asAccessibleTo} should be
    preferred in new code.

    @param role: The role to retrieve L{SharedProxy}s for.

    @param query: An Axiom query describing the Items to retrieve, which this
    role can access.
    @type query: an L{iaxiom.IQuery} provider.
    """
    warnings.warn(
        "Use Role.asAccessibleTo() instead of sharing.asAccessibleTo().",
        PendingDeprecationWarning,
        stacklevel=2)
    return role.asAccessibleTo(query)



def itemFromProxy(obj):
    """
    Retrieve the real, underlying Item based on a L{SharedProxy} object, so
    that you can access all of its attributes and methods.

    This function is provided because sometimes it's hard to figure out how to
    cleanly achieve some behavior, especially running a query which relates to
    a shared proxy which you have retrieved.  However, if you find yourself
    calling it a lot, that's a very bad sign: calling this method is implicitly
    a breach of the security that the sharing system tries to provide.
    Normally, if your code is acting as an agent of role X, it has access to a
    L{SharedProxy} that only provides interfaces explicitly allowed to X.  If
    you make a mistake and call a method that the user is not supposed to be
    able to access, the user will receive an exception rather than be allowed
    to violate the system's security constraints.

    However, once you have retrieved the underlying item, all bets are off, and
    you have to perform your own security checks.  This is error-prone, and
    should be avoided.  We suggest, instead, adding explicitly allowed methods
    for performing any queries which your objects need.

    @param obj: a L{SharedProxy} instance

    @return: the underlying Item instance of the given L{SharedProxy}, with all
    of its methods and attributes exposed.
    """
    return object.__getattribute__(obj, '_sharedItem')



def unShare(sharedItem):
    """
    Remove all instances of this item from public or shared view.
    """
    sharedItem.store.query(Share, Share.sharedItem == sharedItem).deleteFromStore()



def randomEarlyShared(store, role):
    """
    If there are no explicitly-published public index pages to display, find a
    shared item to present to the user as first.
    """
    for r in role.allRoles():
        share = store.findFirst(Share, Share.sharedTo == r,
                                sort=Share.storeID.ascending)
        if share is not None:
            return share.sharedItem
    raise NoSuchShare("Why, that user hasn't shared anything at all!")

