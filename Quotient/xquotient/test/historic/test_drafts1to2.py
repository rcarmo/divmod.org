from axiom.test.historic.stubloader import StubbedTest

from xmantissa.ixmantissa import INavigableElement

from xquotient.compose import Composer, Drafts


class DraftsUpgradeTest(StubbedTest):
    """
    Test that the Drafts item has been removed and is no longer a powerup for a
    composer.
    """

    def test_upgrade(self):
        self.assertEqual(self.store.count(Drafts), 0)
        composer = self.store.findUnique(Composer)
        for pup in composer.powerupsFor(INavigableElement):
            self.failIf(isinstance(pup, Drafts))
