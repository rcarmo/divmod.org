
from axiom.test.historic.stubloader import StubbedTest

from xquotient.compose import Composer, Drafts


class ComposerUpgradeTestCase(StubbedTest):
    """
    Test that the Composer no longer has a 'drafts' attribute, that no Drafts
    items have been created and that the other attributes have been copied.
    """

    def test_upgrade(self):
        composer = self.store.findUnique(Composer)
        self.failIf(hasattr(composer, 'drafts'), "Still has 'drafts' attribute")
        self.assertNotEqual(composer.privateApplication, None)
        self.assertEqual(self.store.count(Drafts), 0)
