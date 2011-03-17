
from axiom.userbase import LoginSystem
from axiom.test.historic.stubloader import StubbedTest

from nevow.inevow import IResource

from xmantissa.ixmantissa import IMantissaSite, IWebViewer

from xmantissa.publicweb import AnonymousSite

class AnonymousSiteUpgradeTests(StubbedTest):
    """
    Tests to verify that the L{AnonymousSite} was properly upgraded.
    """

    def test_attribute(self):
        """
        Make sure that the one attribute defined by L{AnonymousSite} is
        properly set.
        """
        ls = self.store.findUnique(LoginSystem)
        site = self.store.findUnique(AnonymousSite)
        self.assertIdentical(site.loginSystem, ls)


    def test_powerups(self):
        """
        L{AnonymousSite} should be installed as a powerup for
        L{IWebViewer} and L{IMantissaSite}.
        """
        self.assertEqual(
            set(list(self.store.interfacesFor(
                        self.store.findUnique(AnonymousSite)))),
            set([IResource, IMantissaSite, IWebViewer]))
