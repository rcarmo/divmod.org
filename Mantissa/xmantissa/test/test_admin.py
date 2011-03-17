"""
Test cases for the L{xmantissa.webadmin} module.
"""


from twisted.trial.unittest import TestCase


from nevow.athena import LivePage
from nevow.context import WovenContext
from nevow.testutil import FakeRequest
from nevow.loaders import stan
from nevow.tags import html, head, body, directive
from nevow.inevow import IRequest

from axiom.store import Store
from axiom.userbase import LoginSystem, LoginMethod
from axiom.dependency import installOn

from axiom.plugins.mantissacmd import Mantissa

from xmantissa.webadmin import (
    LocalUserBrowser, LocalUserBrowserFragment,
    UserInteractionFragment, EndowFragment, DepriveFragment,
    SuspendFragment, UnsuspendFragment)

from xmantissa.product import Product


class UserInteractionFragmentTestCase(TestCase):
    def setUp(self):
        """
        Create a site store and a user store with a L{LocalUserBrowser}
        installed on it.
        """
        self.siteStore = Store()
        self.loginSystem = LoginSystem(store=self.siteStore)
        installOn(self.loginSystem, self.siteStore)

        self.userStore = Store()
        self.userStore.parent = self.siteStore
        self.browser = LocalUserBrowser(store=self.userStore)


    def test_createUser(self):
        """
        Test that L{webadmin.UserInteractionFragment.createUser} method
        actually creates a user.
        """
        userInteractionFragment = UserInteractionFragment(self.browser)
        userInteractionFragment.createUser(
            u'testuser', u'localhost', u'password')

        account = self.loginSystem.accountByAddress(u'testuser', u'localhost')
        self.assertEquals(account.password, u'password')


    def test_rendering(self):
        """
        Test that L{webadmin.UserInteractionFragment} renders without raising
        any exceptions.
        """
        f = UserInteractionFragment(self.browser)

        p = LivePage(
            docFactory=stan(
                html[
                    head(render=directive('liveglue')),
                    body(render=lambda ctx, data: f)]))
        f.setFragmentParent(p)

        ctx = WovenContext()
        req = FakeRequest()
        ctx.remember(req, IRequest)

        d = p.renderHTTP(ctx)
        def rendered(ign):
            p.action_close(None)
        d.addCallback(rendered)
        return d



class ActionsTestCase(TestCase):
    """
    Tests to verify that actions behave as expected.

    @ivar siteStore: A site store containing an administrative user's account.

    @ivar siteAccount: The L{axiom.userbase.LoginAccount} for the
    administrator, in the site store.

    @ivar siteMethod: The single L{axiom.userbase.LoginMethod} for the
    administrator, in the site store.

    @ivar localUserBrowserFragment: A L{LocalUserBrowserFragment} examining the
    administrator's L{LocalUserBrowser} powerup.
    """

    def setUp(self):
        """
        Construct a site and user store with an administrator that can invoke the
        web administrative tools, setting the instance variables described in
        this class's docstring.
        """
        self.siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.siteStore, u"localhost", u"", False)
        Mantissa().installAdmin(self.siteStore, u'admin', u'localhost', u'asdf')

        self.siteMethod = self.siteStore.findUnique(
            LoginMethod, LoginMethod.localpart == u'admin')
        self.siteAccount = self.siteMethod.account
        userStore = self.siteAccount.avatars.open()
        lub = userStore.findUnique(LocalUserBrowser)
        self.localUserBrowserFragment = LocalUserBrowserFragment(lub)


    def test_actionTypes(self):
        """
        Verify that all the action methods expose the appropriate fragment
        objects, with their attributes set to indicate the correct objects to
        manipulate.
        """
        myRowID = self.localUserBrowserFragment.linkToItem(self.siteMethod)
        actionMap = [('installOn', EndowFragment),
                     ('uninstallFrom', DepriveFragment),
                     ('suspend', SuspendFragment),
                     ('unsuspend', UnsuspendFragment)]
        for action, fragmentType in actionMap:
            resultFragment = self.localUserBrowserFragment.performAction(
                action, myRowID)
            self.failUnless(isinstance(resultFragment, fragmentType),
                            "%s does not return a %s" %
                            (action, fragmentType))
            self.assertEquals(resultFragment.fragmentParent,
                              self.localUserBrowserFragment)
            self.assertEquals(resultFragment.account, self.siteAccount)



class RenderingTestCase(TestCase):
    """
    Test cases for HTML rendering of various fragments.
    """

    def doRendering(self, fragmentClass):
        """
        Verify that the given fragment class will render without raising an
        exception.
        """
        siteStore = Store()

        loginSystem = LoginSystem(store=siteStore)
        installOn(loginSystem, siteStore)
        p = Product(store=siteStore, types=["xmantissa.webadmin.LocalUserBrowser",
                                            "xmantissa.signup.SignupConfiguration"])
        account = loginSystem.addAccount(u'testuser', u'localhost', None)
        p.installProductOn(account.avatars.open())
        f = fragmentClass(None, u'testuser', account)

        p = LivePage(
            docFactory=stan(
                html[
                    head(render=directive('liveglue')),
                    body(render=lambda ctx, data: f)]))
        f.setFragmentParent(p)

        ctx = WovenContext()
        req = FakeRequest()
        ctx.remember(req, IRequest)

        d = p.renderHTTP(ctx)
        def rendered(ign):
            p.action_close(None)
        d.addCallback(rendered)
        return d


    def test_endowRendering(self):
        """
        Verify that L{EndowFragment} can render without raising an exception.
        """
        return self.doRendering(EndowFragment)


    def test_depriveRendering(self):
        """
        Verify that L{DepriveFragment} can render without raising an exception.
        """
        return self.doRendering(DepriveFragment)


    def test_suspendRendering(self):
        """
        Verify that L{SuspendFragment} can render without raising an exception.
        """
        return self.doRendering(SuspendFragment)


    def test_unsuspendRendering(self):
        """
        Verify that L{UnsuspendFragment} can render without raising an
        exception.
        """
        return self.doRendering(UnsuspendFragment)


