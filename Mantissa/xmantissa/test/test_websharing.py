"""
Tests for L{xmantissa.websharing} and L{xmantissa.publicweb}.
"""
from zope.interface import Interface, Attribute, implements

from twisted.python.components import registerAdapter

from twisted.trial.unittest import TestCase

from nevow import rend, url
from nevow.athena import LiveElement

from epsilon.structlike import record

from axiom.item import Item
from axiom.attributes import integer, text
from axiom.store import Store
from axiom.userbase import LoginSystem, LoginMethod
from axiom.dependency import installOn
from axiom.plugins.mantissacmd import Mantissa

from xmantissa import (
    websharing, sharing, signup, offering, product, ixmantissa)



class _TemplateNameResolver(Item):
    """
    An L{ixmantissa.ITemplateNameResolver} with an implementation of
    L{getDocFactory} which doesn't require the presence any disk templates.
    """
    powerupInterfaces = (ixmantissa.ITemplateNameResolver,)

    magicTemplateName = text(doc="""
    L{magicDocFactoryValue} will be returned by L{getDocFactory} if it is passed
    this string as the first argument.""")

    magicDocFactoryValue = text(doc="""
    The string value to be returned from L{getDocFactory} when the name it is
    passed matches L{magicTemplateName}."""
    # if anything starts to care too much about what the docFactory is, we
    # won't be able to get away with just using a string.
    )

    # ITemplateNameResolver
    def getDocFactory(self, name, default=None):
        """
        If C{name} matches L{self.magicTemplateName}, return
        L{self.magicTemplateName}, otherwise return C{default}.
        """
        if name == self.magicTemplateName:
            return self.magicDocFactoryValue
        return default

class ITest(Interface):
    """
    Interface for L{TestAppPowerup} to be shared on.
    """
    store = Attribute("expose 'store' for testing")

class TestAppPowerup(Item):
    implements(ITest)
    attr = integer()

    def installed(self):
        """
        Share this item once installed.
        """
        shareid = u'test'
        sharing.getEveryoneRole(self.store
                        ).shareItem(self,
                          shareID=shareid)
        websharing.addDefaultShareID(self.store, shareid, 0)



class WebSharingTestCase(TestCase):
    """
    Tests for L{xmantissa.websharing.linkTo}
    """
    def setUp(self):
        """
        Set up some state.
        """
        self.s = Store()
        self.ls = LoginSystem(store=self.s)
        installOn(self.ls, self.s)
        acct = self.ls.addAccount(
            u'right', u'host', u'', verified=True, internal=True)
        acct.addLoginMethod(
            u'wrong', u'host', internal=False, verified=False)
        self.share = sharing.shareItem(self.ls, shareID=u'loginsystem')


    def test_noLoginMethods(self):
        """
        L{websharing.linkTo} raises a L{RuntimeError} when the shared item is
        in a store with no internal L{LoginMethod}s.
        """
        for lm in self.s.query(LoginMethod):
            lm.internal = False
        self.assertRaises(RuntimeError, websharing.linkTo, self.share)


    def test_linkToShare(self):
        """
        Test that L{xmantissa.websharing.linkTo} generates a URL using the
        localpart of the account's internal L{axiom.userbase.LoginMethod}
        """
        self._verifyPath(websharing.linkTo(self.share))


    def _verifyPath(self, linkURL):
        """
        Verify that the given url matches the test's expectations.
        """
        self.failUnless(isinstance(linkURL, url.URL),
                        "linkTo should return a nevow.url.URL, not %r" %
                        (type(linkURL)))
        self.assertEquals(str(linkURL), '/users/right/loginsystem')


    def test_linkToProxy(self):
        """
        Test that L{xmantissa.websharing.linkTo} generates a URL that I can
        link to.
        """
        self._verifyPath(
            websharing.linkTo(sharing.getShare(self.s, sharing.getEveryoneRole(
                        self.s), u'loginsystem')))


    def test_shareURLInjectsShareID(self):
        """
        Test that L{xmantissa.websharing._ShareURL} injects the share ID the
        constructor is passed when C{child} is called.
        """
        for (shareID, urlID) in [(u'a', 'a'), (u'\xe9', '%C3%A9')]:
            shareURL = websharing._ShareURL(shareID, netloc='', scheme='')
            self.assertEqual(str(shareURL.child('c')), '/%s/c' % urlID)
            # make sure subsequent child calls on the original have the same
            # behaviour
            self.assertEqual(str(shareURL.child('d')), '/%s/d' % urlID)
            # and that child calls on the returned urls don't (i.e. not
            # '/a/c/a/d'
            self.assertEqual(str(shareURL.child('c').child('d')),
                             '/%s/c/d' % urlID)


    def test_shareURLNoStoreID(self):
        """
        Test that L{xmantissa.websharing._ShareURL} behaves like a regular
        L{nevow.url.URL} when no store ID is passed.
        """
        shareURL = websharing._ShareURL(None, netloc='', scheme='')
        self.assertEqual(str(shareURL.child('a')), '/a')
        self.assertEqual(str(shareURL.child('a').child('b')), '/a/b')


    def test_shareURLNoClassmethodConstructors(self):
        """
        Verify that the C{fromRequest}, C{fromContext} and C{fromString}
        constructors on L{xmantissa.websharing._ShareURL} throw
        L{NotImplementedError}.
        """
        for meth in (websharing._ShareURL.fromRequest,
                     websharing._ShareURL.fromString,
                     websharing._ShareURL.fromContext):
            self.assertRaises(
                NotImplementedError,
                lambda: meth(None))


    def test_shareURLCloneMaintainsShareID(self):
        """
        Test that L{xmantissa.websharing._ShareURL} can be cloned, and that
        clones will remember the share ID.
        """
        shareURL = websharing._ShareURL(u'a', netloc='', scheme='')
        shareURL = shareURL.cloneURL('', '', None, None, '')
        self.assertEqual(shareURL._shareID, u'a')


    def test_defaultShareIDInteractionMatching(self):
        """
        Verify that L{websharing.linkTo} does not explicitly include a share
        ID in the URL if the ID of the share it is passed matches the default.
        """
        websharing.addDefaultShareID(self.s, u'share-id', 0)
        sharing.shareItem(Shareable(store=self.s), shareID=u'share-id')
        share = sharing.getShare(
            self.s, sharing.getEveryoneRole(self.s), u'share-id')
        url = websharing.linkTo(share)
        self.assertEqual(str(url), '/users/right/')
        # and if we call child()
        self.assertEqual(str(url.child('child')), '/users/right/share-id/child')


    def test_defaultShareIDInteractionNoMatch(self):
        """
        Verify that L{websharing.linkTo} explicitly includes a share ID in the
        URL if the ID of the share it is passed doesn't match the default.
        """
        websharing.addDefaultShareID(self.s, u'share-id', 0)
        shareable = Shareable(store=self.s)
        sharing.shareItem(Shareable(store=self.s), shareID=u'not-the-share-id')
        share = sharing.getShare(
            self.s, sharing.getEveryoneRole(self.s), u'not-the-share-id')
        url = websharing.linkTo(share)
        self.assertEqual(str(url), '/users/right/not-the-share-id')


    def test_appStoreLinkTo(self):
        """
        When L{websharing.linkTo} is called on a shared item in an app store,
        it returns an URL with a single path segment consisting of the app's
        name.
        """
        s = Store(dbdir=self.mktemp())
        Mantissa().installSite(s, u"localhost", u"", False)
        Mantissa().installAdmin(s, u'admin', u'localhost', u'asdf')
        off = offering.Offering(
            name=u'test_offering',
            description=u'Offering for creating a sample app store',
            siteRequirements=[],
            appPowerups=[TestAppPowerup],
            installablePowerups=[],
            loginInterfaces=[],
            themes=[],
            )
        userbase = s.findUnique(LoginSystem)
        adminAccount = userbase.accountByAddress(u'admin', u'localhost')
        conf = adminAccount.avatars.open().findUnique(
            offering.OfferingConfiguration)
        conf.installOffering(off, None)
        ss = userbase.accountByAddress(off.name, None).avatars.open()
        sharedItem = sharing.getEveryoneRole(ss).getShare(
            websharing.getDefaultShareID(ss))
        linkURL = websharing.linkTo(sharedItem)
        self.failUnless(isinstance(linkURL, url.URL),
                        "linkTo should return a nevow.url.URL, not %r" %
                        (type(linkURL)))
        self.assertEquals(str(linkURL), '/test_offering/')


class _UserIdentificationMixin:
    def setUp(self):
        self.siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.siteStore, u"localhost", u"", False)
        Mantissa().installAdmin(self.siteStore, u'admin', u'localhost', '')
        self.loginSystem = self.siteStore.findUnique(LoginSystem)
        self.adminStore = self.loginSystem.accountByAddress(
            u'admin', u'localhost').avatars.open()
        sc = self.adminStore.findUnique(signup.SignupConfiguration)
        self.signup = sc.createSignup(
            u'testuser@localhost',
            signup.UserInfoSignup,
            {'prefixURL': u''},
            product.Product(store=self.siteStore, types=[]),
            u'', u'')



class UserIdentificationTestCase(_UserIdentificationMixin, TestCase):
    """
    Tests for L{xmantissa.websharing._storeFromUsername}
    """
    def test_sameLocalpartAndUsername(self):
        """
        Test that L{xmantissa.websharing._storeFromUsername} doesn't get
        confused when the username it is passed is the same as the localpart
        of that user's email address
        """
        self.signup.createUser(
            u'', u'username', u'localhost', u'', u'username@internet')
        self.assertIdentical(
            websharing._storeFromUsername(self.siteStore, u'username'),
            self.loginSystem.accountByAddress(
                u'username', u'localhost').avatars.open())


    def test_usernameMatchesOtherLocalpart(self):
        """
        Test that L{xmantissa.websharing._storeFromUsername} doesn't get
        confused when the username it is passed matches the localpart of
        another user's email address
        """
        self.signup.createUser(
            u'', u'username', u'localhost', u'', u'notusername@internet')
        self.signup.createUser(
            u'', u'notusername', u'localhost', u'', u'username@internet')
        self.assertIdentical(
            websharing._storeFromUsername(self.siteStore, u'username'),
            self.loginSystem.accountByAddress(
                u'username', u'localhost').avatars.open())


class IShareable(Interface):
    """
    Dummy interface for Shareable.
    """
    magicValue = Attribute(
        """
        A magical value.
        """)


    fragmentName = Attribute(
        """
        The value that the corresponding L{ShareableView} should use for its
        C{fragmentName} attribute.
        """)



class Shareable(Item):
    """
    This is a dummy class that may be shared.
    """
    implements(IShareable)

    magicValue = integer()



class ShareableView(LiveElement):
    """
    Nothing to see here, move along.

    @ivar customizedFor: The username we were customized for, or C{None}.
    """
    implements(ixmantissa.INavigableFragment,
               ixmantissa.ICustomizable)

    customizedFor = None
    fragmentName = 'bogus'

    def __init__(self, shareable):
        """
        adapt a shareable to INavigableFragment
        """
        super(ShareableView, self).__init__()
        self.shareable = shareable


    def showMagicValue(self):
        """
        retrieve the magic value from my model
        """
        return self.shareable.magicValue


    # XXX: Everything below in this class should not be required.  It's here to
    # satisfy implicit requirements in SharingIndex.locateChild, but there
    # should be test coverage ensuring that it is not required and that
    # customizeFor is only invoked if you provide the ICustomizable interface.

    def customizeFor(self, user):
        """
        Customize me by returning myself, and storing the username we were
        customized for as L{self.customizedFor}.
        """
        self.customizedFor = user
        return self



registerAdapter(ShareableView, IShareable,
                ixmantissa.INavigableFragment)


class FakePage(record('wrappedFragment')):
    """
    A fake page that simply contains a wrapped fragment; analagous to the
    various shell page classes in the tests which use it.
    """



class FakeShellFactory(record('username')):
    """
    An L{IWebViewer} which returns a fake shell page and maps a role
    directly to its given username.
    """

    def wrapModel(self, model):
        """
        Adapt the given model to L{INavigableFragment} and then wrap it in a
        L{FakePage}.
        """
        return FakePage(ixmantissa.INavigableFragment(model))


    def roleIn(self, userStore):
        """
        Return the primary role for the username passed to me.
        """
        return sharing.getPrimaryRole(userStore, self.username)



class UserIndexPageTestCase(_UserIdentificationMixin, TestCase):
    """
    Tests for L{xmantissa.websharing.UserIndexPage}
    """
    username = u'alice'
    domain = u'example.com'
    shareID = u'ashare'

    def setUp(self):
        """
        Create an additional user for UserIndexPage, and share a single item with a
        shareID of the empty string.
        """
        _UserIdentificationMixin.setUp(self)
        self.magicValue = 123412341234
        self.signup.createUser(
            u'', self.username, self.domain, u'', u'username@internet')
        self.userStore = websharing._storeFromUsername(
            self.siteStore, self.username)
        self.shareable = Shareable(store=self.userStore,
                                   magicValue=self.magicValue)
        self.share = sharing.shareItem(self.shareable, shareID=self.shareID)


    def makeSharingIndex(self, username):
        """
        Create a L{SharingIndex}.
        """
        return websharing.SharingIndex(
            self.userStore,
            webViewer=FakeShellFactory(username))


    def test_locateChild(self):
        """
        L{websharing.UserIndexPage.locateChild} should return the named user's
        L{websharing.SharingIndex} (and any remaining segments), or
        L{rend.NotFound}.
        """
        # Test against at least one other valid user.
        self.signup.createUser(
            u'Andr\xe9', u'andr\xe9', u'localhost', u'', u'andr\xe9@internet')
        userStore2 = websharing._storeFromUsername(self.siteStore, u'andr\xe9')
        index = websharing.UserIndexPage(self.loginSystem, FakeShellFactory(None))

        for _username, _store in [(self.username, self.userStore),
                                  (u'andr\xe9', userStore2)]:
            (found, remaining) = index.locateChild(
                None, [_username.encode('utf-8'), 'x', 'y', 'z'])

            self.assertTrue(isinstance(found, websharing.SharingIndex))
            self.assertIdentical(found.userStore, _store)
            self.assertEquals(remaining, ['x', 'y', 'z'])

        self.assertIdentical(index.locateChild(None, ['bogus', 'username']),
                             rend.NotFound)


    def test_linkToMatchesUserURL(self):
        """
        Test that L{xmantissa.websharing.linkTo} generates a URL using the
        localpart of the account's internal L{axiom.userbase.LoginMethod}
        """
        pathString = str(websharing.linkTo(self.share))
        expected = u'/users/%s/%s' % (self.username, self.shareID)
        self.assertEqual(pathString, expected.encode('ascii'))


    def test_emptySegmentNoDefault(self):
        """
        Verify that we get L{rend.NotFound} from
        L{websharing.SharingIndex.locateChild} if there is no default share ID
        and we access the empty child.
        """
        sharingIndex = self.makeSharingIndex(None)
        result = sharingIndex.locateChild(None, ('',))
        self.assertIdentical(result, rend.NotFound)


    def test_emptySegmentWithDefault(self):
        """
        Verify that we get the right resource and segments from
        L{websharing.SharingIndex.locateChild} if there is a default share ID
        and we access the empty child.
        """
        websharing.addDefaultShareID(self.userStore, u'ashare', 0)
        sharingIndex = self.makeSharingIndex(None)
        SEGMENTS = ('', 'foo', 'bar')
        (res, segments) = sharingIndex.locateChild(None, SEGMENTS)
        self.assertEqual(
            res.wrappedFragment.showMagicValue(), self.magicValue)
        self.assertEqual(segments, SEGMENTS[1:])


    def test_invalidShareIDNoDefault(self):
        """
        Verify that we get L{rend.NotFound} from
        L{websharing.SharingIndex.locateChild} if there is no default share ID
        and we access an invalid segment.
        """
        sharingIndex = self.makeSharingIndex(None)
        result = sharingIndex.locateChild(None, ('foo',))
        self.assertIdentical(result, rend.NotFound)


    def test_validShareID(self):
        """
        Verify that we get the right resource and segments from
        L{websharing.SharingIndex.locateChild} if we access a valid share ID.
        """
        websharing.addDefaultShareID(self.userStore, u'', 0)

        otherShareable = Shareable(store=self.userStore,
                                   magicValue=self.magicValue + 3)

        for _shareID in [u'foo', u'f\xf6\xf6']:
            otherShare = sharing.shareItem(otherShareable, shareID=_shareID)
            sharingIndex = self.makeSharingIndex(None)
            SEGMENTS = (_shareID.encode('utf-8'), 'bar')
            (res, segments) = sharingIndex.locateChild(None, SEGMENTS)
            self.assertEqual(
                res.wrappedFragment.showMagicValue(), self.magicValue + 3)
            self.assertEqual(segments, SEGMENTS[1:])



class DefaultShareIDTestCase(TestCase):
    """
    Tests for L{websharing.addDefaultShareID} and L{websharing.getDefaultShareID}.
    """
    def test_createsItem(self):
        """
        Verify that L{websharing.addDefaultShareID} creates a
        L{websharing._DefaultShareID} item.
        """
        store = Store()
        websharing.addDefaultShareID(store, u'share id', -22)
        item = store.findUnique(websharing._DefaultShareID)
        self.assertEqual(item.shareID, u'share id')
        self.assertEqual(item.priority, -22)


    def test_findShareID(self):
        """
        Verify that L{websharing.getDefaultShareID} reads the share ID set by a
        L{websharing.addDefaultShareID} call.
        """
        store = Store()
        websharing.addDefaultShareID(store, u'share id', 0)
        self.assertEqual(websharing.getDefaultShareID(store), u'share id')


    def test_findHighestPriorityShareID(self):
        """
        Verify that L{websharing.getDefaultShareID} reads the highest-priority
        share ID set by L{websharing.addDefaultShareID}.
        """
        store = Store()
        websharing.addDefaultShareID(store, u'share id!', 24)
        websharing.addDefaultShareID(store, u'share id',  25)
        websharing.addDefaultShareID(store, u'share id.', -1)
        self.assertEqual(websharing.getDefaultShareID(store), u'share id')


    def test_findsNoItem(self):
        """
        Verify that L{websharing.getDefaultShareID} returns C{u''} if there is
        no default share ID.
        """
        self.assertEqual(websharing.getDefaultShareID(Store()), u'')
