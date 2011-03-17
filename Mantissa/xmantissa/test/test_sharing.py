
"""
Unit tests for the L{xmantissa.sharing} module.
"""

from zope.interface import Interface, implements

from epsilon.hotfix import require

require("twisted", "trial_assertwarns")

from twisted.trial import unittest

from twisted.python.components import registerAdapter

from twisted.protocols.amp import Command, Box, parseString

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer, boolean
from axiom.test.util import QueryCounter
from axiom.userbase import LoginMethod, LoginAccount

from xmantissa import sharing

class IPrivateThing(Interface):
    def mutateSomeState():
        pass

class IExternal(Interface):
    """
    This is an interface for functionality defined externally to an item.
    """
    def doExternal():
        """
        Do something external.
        """


class IExtraExternal(IExternal):
    """
    This is an interface for functionality defined externally to an item.
    """

    def doExternalExtra():
        """
        Do something _extra_ and external.
        """


class IConflicting(Interface):
    """
    This is an interface with a name that conflicts with IExternal.
    """
    def doExternal():
        """
        Conflicts with IExternal.doExternal.
        """



class IReadOnly(Interface):
    def retrieveSomeState():
        """
        Retrieve the data.
        """


class PrivateThing(Item):
    implements(IPrivateThing, IReadOnly)
    publicData = integer(indexed=True)
    externalized = boolean()
    typeName = 'test_sharing_private_thing'
    schemaVersion = 1

    def mutateSomeState(self):
        self.publicData += 5

    def retrieveSomeState(self):
        """
        Retrieve my public data.
        """
        return self.publicData


class ExtraPrivateThing(Item):
    """
    Private class which supports extra operations / adaptations.
    """
    privateData = integer(indexed=True)
    def doPrivateThing(self):
        """
        A method, that does a thing.
        """



class ExternalThing(object):
    implements(IExternal)

    def __init__(self, priv):
        self.privateThing = priv

    def doExternal(self):
        """
        Do an external thing.
        """
        self.privateThing.externalized = True
        return "external"



class ExtraExternalThing(object):
    """
    Adapter for ExtraPrivateThing.
    """
    implements(IExtraExternal)

    def __init__(self, extraPrivateThing):
        self.extraPrivateThing = extraPrivateThing

    # WARNING WARNING WARNING WARNING WARNING

    # The following two methods are shared methods on a shared interfaces which
    # return 'self' as one of the parts of their return value.  IN NORMAL
    # APPLICATION CODE THIS IS A SECURITY RISK!  One of the major features of
    # the sharing system is that it makes programs secure in the face of errors
    # such as accessing an attribute that you are not technically supposed to
    # access from the view.  However, if you give back 'self' to some view code
    # that is asking externally, you are telling the view that it has FULL
    # ACCESS to this object and may call methods on it with impunity.  DO NOT
    # DO THIS IN NORMAL APPLICATION CODE, IT IS ONLY FOR TESTING!!!

    def doExternal(self):
        """
        Do something external and return a 2-tuple of a marker value to indicate
        that this adapter class was used and an identifier to confirm the
        adapter's identity.
        """
        return ("external", self)


    def doExternalExtra(self):
        """
        Similar to doExternal, but a different method
        """
        return ("external-extra", self)

    # DANGER DANGER DANGER DANGER DANGER



registerAdapter(ExternalThing, PrivateThing, IExternal)
registerAdapter(ExtraExternalThing, ExtraPrivateThing, IExtraExternal)


class IPublicThing(Interface):
    def callMethod():
        pass

    def isMethodAvailable(self):
        pass

class PublicFacingAdapter(object):

    implements(IPublicThing)

    def __init__(self, thunk):
        self.thunk = thunk

    def isMethodAvailable(self):
        return IPrivateThing.providedBy(self.thunk)

    def callMethod(self):
        return self.thunk.mutateSomeState()

registerAdapter(PublicFacingAdapter, IReadOnly, IPublicThing)


class InterfaceUtils(unittest.TestCase):
    """
    Test cases for private zope interface utility functionality.
    """
    class A(Interface):
        "A root interface."
    class B(A):
        "A->B"
    class C(B):
        "A->B->C"
    class D(C):
        "A->B->C->D"

    class Q(Interface):
        "Another root interface, unrelated to A"

    class W(B):
        """
        A->B->...
           |
           +->W
        """
    class X(W):
        "A->B->W->X"
    class Y(X):
        "A->B->W->X->Y"
    class Z(Y):
        "A->B->W->X->Y->Z"

    def test_commonParent(self):
        """
        Verify the function which determines the common parent of two interfaces.
        """
        self.assertEquals(sharing._commonParent(self.Z, self.D), self.B)


    def test_noCommonParent(self):
        """
        _commonParent should return None for two classes which do not have a common
        parent.
        """
        self.assertIdentical(sharing._commonParent(self.A, self.Q), None)


    def test_commonParentOfYourself(self):
        """
        The common parent of the same object is itself.
        """
        self.assertIdentical(sharing._commonParent(self.A, self.A), self.A)


class SimpleSharing(unittest.TestCase):


    def setUp(self):
        self.store = Store()


    def test_differentUserSameID(self):
        """
        Verify that if different facets of the same item are shared to different
        users with the same shareID, each user will receive the correct
        respective facet with only the correct methods exposed.
        """
        t = PrivateThing(store=self.store, publicData=789)
        toBob = sharing.shareItem(t, toName=u'bob@example.com',
                                  interfaces=[IReadOnly])
        toAlice = sharing.shareItem(t, toName=u'alice@example.com',
                                    shareID=toBob.shareID,
                                    interfaces=[IPrivateThing])
        # Sanity check.
        self.assertEquals(toBob.shareID, toAlice.shareID)
        asBob = sharing.getShare(self.store,
                                 sharing.getPrimaryRole(
                self.store, u'bob@example.com'),
                                 toBob.shareID)
        asAlice = sharing.getShare(self.store,
                                 sharing.getPrimaryRole(
                self.store, u'alice@example.com'),
                                 toBob.shareID)
        self.assertEquals(asBob.retrieveSomeState(), 789)
        self.assertRaises(AttributeError, lambda : asBob.mutateSomeState)
        self.assertRaises(AttributeError, lambda : asAlice.retrieveSomeState)
        asAlice.mutateSomeState()
        # Make sure they're both seeing the same item.
        self.assertEquals(asBob.retrieveSomeState(), 789+5)


    def test_simpleShareMethods(self):
        """
        Verify that an item which is shared with Role.shareItem can be
        retrieved and manipulated with Role.getShare.  This is the new-style
        API, which isn't yet widely used, but should be preferred in new code.
        """
        t = PrivateThing(store=self.store, publicData=456)
        bob = sharing.getPrimaryRole(self.store, u'bob@example.com',
                                     createIfNotFound=True)
        shareItemResult = bob.shareItem(t)
        gotShare = bob.getShare(shareItemResult.shareID)
        gotShare.mutateSomeState()
        self.assertEquals(t.publicData, 456 + 5)


    def test_simpleShare(self):
        """
        Verify that an item which is shared with shareItem can be retrieved and
        manipulated with getShare.  This is an older-style API, on its way to
        deprecation.
        """
        t = PrivateThing(store=self.store, publicData=456)
        shareItemResult = self.assertWarns(
            PendingDeprecationWarning,
            "Use Role.shareItem() instead of sharing.shareItem().",
            __file__,
            lambda : sharing.shareItem(t, toName=u'bob@example.com'))
        bob = sharing.getPrimaryRole(self.store, u'bob@example.com')
        gotShare = self.assertWarns(
            PendingDeprecationWarning,
            "Use Role.getShare() instead of sharing.getShare().",
            __file__,
            lambda :
                sharing.getShare(self.store, bob, shareItemResult.shareID))
        gotShare.mutateSomeState()
        self.assertEquals(t.publicData, 456 + 5)


    def test_invalidShareID(self):
        """
        Verify that NoSuchShare is raised when getShare is called without sharing
        anything first.
        """
        self.assertRaises(sharing.NoSuchShare,
                          sharing.getShare,
                          self.store,
                          sharing.getPrimaryRole(self.store,
                                                 u'nobody@example.com'),
                          u"not a valid shareID")

    def test_unauthorizedAccessNoShare(self):
        """
        Verify that NoSuchShare is raised when getShare is called with a user who
        is not allowed to access a shared item.
        """
        t = PrivateThing(store=self.store, publicData=345)
        theShare = sharing.shareItem(t, toName=u'somebody@example.com')
        self.assertRaises(sharing.NoSuchShare,
                          sharing.getShare,
                          self.store,
                          sharing.getPrimaryRole(self.store,
                                                 u'nobody@example.com'),
                          theShare.shareID)


    def test_deletedOriginalNoShare(self):
        """
        NoSuchShare should be raised when getShare is called with an item who is
        not allowed to access a shared item.
        """
        t = PrivateThing(store=self.store, publicData=234)
        theShare = sharing.shareItem(t, toName=u'somebody@example.com')
        t.deleteFromStore()
        self.assertRaises(sharing.NoSuchShare,
                          sharing.getShare,
                          self.store,
                          sharing.getPrimaryRole(self.store,
                                                 u'somebody@example.com'),
                          theShare.shareID)


    def test_shareAndAdapt(self):
        """
        Verify that when an item is shared to a particular user with a particular
        interface, retrieving it for that user results in methods on the given
        interface being callable and other methods being restricted.
        """
        t = PrivateThing(store=self.store, publicData=789)

        # Sanity check.
        self.failUnless(IPublicThing(t).isMethodAvailable())

        shared = sharing.shareItem(t, toName=u'testshare', interfaces=[IReadOnly])
        proxy = sharing.getShare(self.store,
                                 sharing.getPrimaryRole(self.store, u'testshare'),
                                 shared.shareID)
        self.assertFalse(IPublicThing(proxy).isMethodAvailable())
        self.assertRaises(AttributeError, IPublicThing(proxy).callMethod)


    def test_getShareProxyWithAdapter(self):
        """
        When you share an item with an interface that has an adapter for that
        interface, the object that results from getShare should provide the
        interface by exposing the adapter rather than the original item.
        """
        privateThing = PrivateThing(store=self.store)
        shared = sharing.shareItem(privateThing, toName=u'testshare',
                                   interfaces=[IExternal])
        proxy = sharing.getShare(self.store,
                                 sharing.getPrimaryRole(self.store, u'testshare'),
                                 shared.shareID)
        proxy.doExternal()
        self.assertTrue(privateThing.externalized)


    def test_conflictingNamesException(self):
        """
        When you share an item with two interfaces that contain different
        adapters with conflicting names, an exception should be raised alerting
        you to this conflict.
        """
        extraPrivateThing = ExtraPrivateThing(store=self.store)
        self.assertRaises(sharing.ConflictingNames,
                          sharing.shareItem, extraPrivateThing, toName=u'testshare',
                          interfaces=[IExternal, IConflicting])


    def test_coalesceInheritedAdapters(self):
        """
        If multiple interfaces that are part of the same inheritance hierarchy are
        specified, only the leaf interfaces should be adapted to, and provided
        for all interfaces it inherits from.
        """

        extraPrivateThing = ExtraPrivateThing(store=self.store)
        role = sharing.getPrimaryRole(self.store, u'testshare')
        extraProxy = sharing.getShare(
            self.store, role, sharing.shareItem(
                extraPrivateThing,
                toRole=role, interfaces=[IExternal,
                                      IExtraExternal]).shareID)

        externalTag, externalObj = extraProxy.doExternal()
        extraExternalTag, extraExternalObj = extraProxy.doExternalExtra()
        self.assertIdentical(externalObj, extraExternalObj)
        self.assertEquals(externalTag, 'external')
        self.assertEquals(extraExternalTag, 'external-extra')



class AccessibilityQuery(unittest.TestCase):

    def setUp(self):
        self.i = 0
        self.store = Store()
        self.things = []
        self.bobThings = []
        self.aliceThings = []
        self.bob = sharing.getPrimaryRole(self.store, u'bob@example.com',
                                          createIfNotFound=True)
        self.alice = sharing.getPrimaryRole(self.store, u'alice@example.com',
                                            createIfNotFound=True)


    def test_twoInterfacesTwoGroups(self):
        """
        Verify that when an item is shared to two roles that a user is a member of,
        they will have access to both interfaces when it is retrieved with
        getShare.
        """
        self.addSomeThings()
        us = sharing.getPrimaryRole(self.store, u'us', True)
        them = sharing.getPrimaryRole(self.store, u'them', True)
        self.bob.becomeMemberOf(us)
        self.bob.becomeMemberOf(them)
        it = PrivateThing(store=self.store, publicData=1234)
        sharing.shareItem(it, toRole=us, shareID=u'q', interfaces=[IPrivateThing])
        sharing.shareItem(it, toRole=them, shareID=u'q', interfaces=[IReadOnly])
        that = sharing.getShare(self.store, self.bob, u'q')
        self.assertEquals(that.retrieveSomeState(), 1234)
        that.mutateSomeState()
        self.assertEquals(that.retrieveSomeState(), 1239)


    def test_twoInterfacesTwoGroupsQuery(self):
        """
        Verify that when an item is shared to two roles that a user is a member of,
        and then retrieved by an asAccessibleTo query, both interfaces will be
        accessible on each object in the query result, and the same number of
        items will be accessible in the query as were shared.
        """
        us = sharing.getPrimaryRole(self.store, u'us', True)
        them = sharing.getPrimaryRole(self.store, u'them', True)
        self.bob.becomeMemberOf(us)
        self.bob.becomeMemberOf(them)
        for x in range(3):
            it = PrivateThing(store=self.store, publicData=x)
            sharing.shareItem(it, toRole=us, shareID=u'q',
                              interfaces=[IPrivateThing])
            sharing.shareItem(it, toRole=them, shareID=u'q',
                              interfaces=[IReadOnly])
        # sanity check
        self.assertEquals(self.store.query(PrivateThing).count(), 3)
        aat = list(sharing.asAccessibleTo(self.bob, self.store.query(
                    PrivateThing, sort=PrivateThing.publicData.descending)))
        aat2 = list(sharing.asAccessibleTo(self.bob, self.store.query(
                    PrivateThing, sort=PrivateThing.publicData.ascending)))
        # sanity check x2
        for acc in aat:
            acc.mutateSomeState()
        expectedData = [x + 5 for x in reversed(range(3))]
        self.assertEquals([acc.retrieveSomeState() for acc in aat],
                          expectedData)
        self.assertEquals([acc.retrieveSomeState() for acc in aat2],
                          list(reversed(expectedData)))


    def test_twoInterfacesTwoGroupsUnsortedQuery(self):
        """
        Verify that when duplicate shares exist for the same item and an
        asAccessibleTo query is made with no specified sort, the roles are
        still deduplicated properly.
        """
        us = sharing.getPrimaryRole(self.store, u'us', True)
        them = sharing.getPrimaryRole(self.store, u'them', True)
        self.bob.becomeMemberOf(us)
        self.bob.becomeMemberOf(them)
        for x in range(3):
            it = PrivateThing(store=self.store, publicData=x)
            sharing.shareItem(it, toRole=us, shareID=u'q',
                              interfaces=[IPrivateThing])
            sharing.shareItem(it, toRole=them, shareID=u'q',
                              interfaces=[IReadOnly])
        # sanity check
        self.assertEquals(self.store.query(PrivateThing).count(), 3)
        aat = list(sharing.asAccessibleTo(self.bob, self.store.query(
                    PrivateThing)))
        # sanity check x2
        for acc in aat:
            acc.mutateSomeState()
        expectedData = [x + 5 for x in range(3)]
        aat.sort(key=lambda i: i.retrieveSomeState())
        self.assertEquals([acc.retrieveSomeState() for acc in aat],
                          expectedData)


    def addSomeThings(self):
        privateThing = PrivateThing(store=self.store, publicData=-self.i)
        self.i += 1
        self.things.append(privateThing)
        self.bobThings.append(sharing.shareItem(
                privateThing, toName=u'bob@example.com',
                interfaces=[IReadOnly]))
        self.aliceThings.append(sharing.shareItem(
                privateThing,
                toName=u'alice@example.com',
                interfaces=[IPrivateThing]))


    def test_asAccessibleTo(self):
        """
        Ensure that L{Role.asAccessibleTo} returns only items actually
        accessible to the given role.
        """
        for i in range(10):
            self.addSomeThings()

        query = self.store.query(PrivateThing)
        aliceQuery = list(self.alice.asAccessibleTo(query))
        bobQuery = list(self.bob.asAccessibleTo(query))

        self.assertEqual(map(sharing.itemFromProxy, bobQuery),
                         map(lambda x: x.sharedItem, self.bobThings))
        self.assertEqual(map(sharing.itemFromProxy, aliceQuery),
                         map(lambda x: x.sharedItem, self.aliceThings))

        self.assertEqual([p.sharedInterfaces
                          for p in aliceQuery], [[IPrivateThing]] * 10)
        self.assertEqual([p.sharedInterfaces
                          for p in bobQuery], [[IReadOnly]] * 10)




    def test_accessibilityQuery(self):
        """
        Ensure that asAccessibleTo returns only items actually accessible to
        the given role.
        """
        for i in range(10):
            self.addSomeThings()

        query = self.store.query(PrivateThing)
        aliceQuery = self.assertWarns(
            PendingDeprecationWarning,
            "Use Role.asAccessibleTo() instead of sharing.asAccessibleTo().",
            __file__,
            lambda : list(sharing.asAccessibleTo(self.alice, query)))
        bobQuery = list(sharing.asAccessibleTo(self.bob, query))

        self.assertEqual(map(sharing.itemFromProxy, bobQuery),
                         map(lambda x: x.sharedItem, self.bobThings))
        self.assertEqual(map(sharing.itemFromProxy, aliceQuery),
                         map(lambda x: x.sharedItem, self.aliceThings))

        self.assertEqual([p.sharedInterfaces
                          for p in aliceQuery], [[IPrivateThing]] * 10)
        self.assertEqual([p.sharedInterfaces
                          for p in bobQuery], [[IReadOnly]] * 10)


    def test_sortOrdering(self):
        """
        Ensure that asAccessibleTo respects query sort order.
        """
        for i in range(10):
            self.addSomeThings()

        query = self.store.query(PrivateThing,
                                 sort=PrivateThing.publicData.ascending)
        # Sanity check.
        self.assertEquals([x.publicData for x in query], range(-9, 1, 1))
        bobQuery = list(sharing.asAccessibleTo(self.bob, query))
        self.assertEquals([x.retrieveSomeState() for x in bobQuery],
                          range(-9, 1, 1))
        query2 = self.store.query(PrivateThing,
                                  sort=PrivateThing.publicData.descending)
        # Sanity check #2
        self.assertEquals([x.publicData for x in query2], range(-9, 1, 1)[::-1])
        bobQuery2 = list(sharing.asAccessibleTo(self.bob, query2))
        self.assertEquals([x.retrieveSomeState() for x in bobQuery2], range(-9, 1, 1)[::-1])


    def test_limit(self):
        """
        Ensure that asAccessibleTo respects query limits.
        """
        for i in range(10):
            self.addSomeThings()

        query = self.store.query(PrivateThing, limit=3)
        bobQuery = list(sharing.asAccessibleTo(self.bob, query))
        self.assertEquals(len(bobQuery), 3)


    def test_limitGetsAllInterfaces(self):
        """
        asAccessibleTo should always collate interfaces together, regardless of
        its limit parameter.
        """
        t = PrivateThing(store=self.store, publicData=self.i)
        sharing.shareItem(t, toName=u'bob@example.com',
                          interfaces=[IPrivateThing], shareID=u'test')
        sharing.shareItem(t, toName=u'Everyone',
                          interfaces=[IReadOnly], shareID=u'test')
        L = list(sharing.asAccessibleTo(
                self.bob, self.store.query(PrivateThing, limit=1)))
        self.assertEquals(len(L), 1)
        self.assertEquals(set(L[0].sharedInterfaces),
                          set([IReadOnly, IPrivateThing]))


    def test_limitMultiShare(self):
        """
        asAccessibleTo should stop after yielding the limit number of results,
        even if there are more shares examined than results.
        """
        L = []
        for x in range(10):
            t = PrivateThing(store=self.store, publicData=self.i)
            L.append(t)
            self.i += 1
            sharing.shareItem(t, toName=u'bob@example.com',
                              interfaces=[IPrivateThing],
                              shareID=unicode(x))
            sharing.shareItem(t, toName=u'Everyone', interfaces=[IReadOnly],
                              shareID=unicode(x))
        proxies = list(sharing.asAccessibleTo(
                self.bob,
                self.store.query(PrivateThing, limit=5,
                                 sort=PrivateThing.publicData.ascending)))
        self.assertEquals(map(sharing.itemFromProxy, proxies), L[:5])
        for proxy in proxies:
            self.assertEquals(set(proxy.sharedInterfaces),
                              set([IPrivateThing, IReadOnly]))


    def test_limitWithPrivateStuff(self):
        """
        Verify that a limited query with some un-shared items will return up to
        the provided limit number of shared items.
        """
        L = []

        def makeThing(shared):
            t = PrivateThing(store=self.store, publicData=self.i)
            self.i += 1
            if shared:
                sharing.shareItem(
                    t, toRole=self.bob, interfaces=[IPrivateThing],
                    shareID=unicode(self.i))
            L.append(t)
        # 0, 1, 2: shared
        for x in range(3):
            makeThing(True)
        # 3, 4, 5: private
        for x in range(3):
            makeThing(False)
        # 6, 7, 8: shared again
        for x in range(3):
            makeThing(True)

        self.assertEquals(
            map(sharing.itemFromProxy,
                sharing.asAccessibleTo(
                    self.bob, self.store.query(
                        PrivateThing, limit=5))),
            [L[0], L[1], L[2], L[6], L[7]])


    def test_limitEfficiency(self):
        """
        Verify that querying a limited number of shared items does not become
        slower as more items are shared.
        """
        zomg = QueryCounter(self.store)

        for i in range(10):
            self.addSomeThings()

        query = self.store.query(
            PrivateThing, limit=3, sort=PrivateThing.publicData.ascending)
        checkit = lambda : list(sharing.asAccessibleTo(self.bob, query))
        before = zomg.measure(checkit)

        for i in range(10):
            self.addSomeThings()

        after = zomg.measure(checkit)
        self.assertEquals(before, after)
    test_limitEfficiency.todo = (
        'currently gets too many results because we should be using paginate')


class HeuristicTestCases(unittest.TestCase):
    """
    These are tests for sharing APIs which heuristically determine identifying
    information about a user's store or a shared item.
    """

    def setUp(self):
        """
        Set up a store for testing.
        """
        self.store = Store()
        self.account = LoginAccount(store=self.store, password=u'1234')
        self.method = LoginMethod(store=self.store,
                                  account=self.account,
                                  localpart=u'username',
                                  domain=u'domain.example.com',
                                  internal=True,
                                  protocol=u'*',
                                  verified=True)


    def test_getSelfRole(self):
        """
        The self-role of a store should be determined by its L{LoginMethod}s.
        """
        self.assertEquals(list(self.store.query(sharing.Role)), [])
        me = sharing.getSelfRole(self.store)
        self.assertEquals(me.externalID, u'username@domain.example.com')
        self.assertEquals(me.store, self.store)
        self.assertEquals(list(me.allRoles()),
                          [me,
                           sharing.getAuthenticatedRole(self.store),
                           sharing.getEveryoneRole(self.store)])


    def test_getAccountRole(self):
        """
        L{getAccountRole} returns a L{Role} in a given store for one of the
        account names passed to it.
        """
        role = sharing.getAccountRole(
            self.store, [(u"username", u"domain.example.com")])
        self.assertEquals(role.externalID, u"username@domain.example.com")


    def test_noAccountRole(self):
        """
        L{getAccountRole} raises L{ValueError} if passed an empty list of account names.
        """
        self.assertRaises(ValueError, sharing.getAccountRole, self.store, [])


    def test_identifierFromSharedItem(self):
        """
        L{sharing.Identifier.fromSharedItem} should identify a shared Item's shareID.
        """
        t = PrivateThing(store=self.store)
        sharing.getEveryoneRole(self.store).shareItem(t, shareID=u'asdf')
        sid = sharing.Identifier.fromSharedItem(t)
        self.assertEquals(sid.shareID, u'asdf')
        self.assertEquals(sid.localpart, u'username')
        self.assertEquals(sid.domain, u'domain.example.com')


    def test_identifierFromSharedItemMulti(self):
        """
        L{sharing.Identifier.fromSharedItem} should identify a shared Item's
        shareID even if it is shared multiple times.
        """
        t = PrivateThing(store=self.store)
        sharing.getEveryoneRole(self.store).shareItem(t, shareID=u'asdf')
        sharing.getAuthenticatedRole(self.store).shareItem(t, shareID=u'jkl;')
        sid = sharing.Identifier.fromSharedItem(t)
        self.assertIn(sid.shareID, [u'asdf', u'jkl;'])
        self.assertEquals(sid.localpart, u'username')
        self.assertEquals(sid.domain, u'domain.example.com')


    def test_identifierFromSharedItemNoShares(self):
        """
        L{sharing.Identifier.fromSharedItem} should raise L{NoSuchShare} if the given
        item is not shared.
        """
        t = PrivateThing(store=self.store)
        self.assertRaises(sharing.NoSuchShare, sharing.Identifier.fromSharedItem, t)


    def test_identifierFromSharedItemNoMethods(self):
        """
        L{sharing.Identifier.fromSharedItem} should raise L{NoSuchShare} if the given
        item's store contains no L{LoginMethod} objects.
        """
        self.method.deleteFromStore()
        t = PrivateThing(store=self.store)
        sharing.getEveryoneRole(self.store).shareItem(t, shareID=u'asdf')
        self.assertRaises(sharing.NoSuchShare, sharing.Identifier.fromSharedItem, t)



class CommandWithIdentifier(Command):
    """
    This command has an Identifier as one of its arguments.
    """
    arguments = [('shareIdentTest', sharing.IdentifierArgument())]



class IdentifierTestCases(unittest.TestCase):
    """
    Tests for the behavior of L{xmantissa.sharing.Identifier}
    """

    def setUp(self):
        """
        Create a few identifiers.
        """
        self.aliceObject = sharing.Identifier(u'object', u'alice', u'example.com')
        self.mostlyAlice = sharing.Identifier(u'not-the-object',
                                      u'alice', u'example.com')
        self.otherAlice = sharing.Identifier(u'object', u'alice', u'example.com')


    def test_equivalence(self):
        """
        Two L{sharing.Identifier} objects that identify the same shared item should
        compare the same.
        """
        self.assertEquals(self.aliceObject, self.otherAlice)
        self.assertFalse(self.aliceObject != self.otherAlice)


    def test_nonEquivalence(self):
        """
        Two L{sharing.Identifier} objects that identify the same shared item should
        compare as not equal.
        """
        self.assertNotEqual(self.aliceObject, self.mostlyAlice)


    def test_otherTypes(self):
        """
        Other types should not compare equal to an L{sharing.Identifier}.
        """
        self.assertNotEqual(self.aliceObject, object())



class IdentifierArgumentTests(unittest.TestCase):
    """
    Tests for serialization and unserialization of
    L{xmantissa.sharing.Identifier} using
    L{xmantissa.sharing.IdentifierArgument}.
    """

    def setUp(self):
        """
        Set up an identifier and its expected serialized form.
        """
        self.identifier = sharing.Identifier(
            u'\u1234object', u'alice', u'example.com')
        self.expectedData = Box(
            shareIdentTest=Box(shareID=u'\u1234object'.encode('utf-8'),
                               localpart=u'alice'.encode('utf-8'),
                               domain=u'example.com'.encode('utf-8')
                               ).serialize()
            ).serialize()


    def test_parse(self):
        """
        L{sharing.IdentifierArgument} should be able to serialize an
        L{Identifier} as an AMP argument to a box.
        """
        outputBox = CommandWithIdentifier.makeArguments(
            dict(shareIdentTest=self.identifier),
            None)
        outputData = outputBox.serialize()
        # Assert on the intermediate / serialized state to make sure the
        # protocol remains stable.
        self.assertEquals(self.expectedData, outputData)


    def test_unparse(self):
        """
        L{sharing.IdentifierArgument} should be able to unserialize an
        L{Identifier} from a serialized box.
        """
        argDict = CommandWithIdentifier.parseArguments(
            parseString(self.expectedData)[0], None)
        self.assertEquals(argDict, dict(shareIdentTest=self.identifier))

