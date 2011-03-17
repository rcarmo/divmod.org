from axiom.test.historic.stubloader import StubbedTest

from xquotient.compose import Composer

class ComposerUpgradeTestCase(StubbedTest):
    def testUpgrade(self):
        composer = self.store.findUnique(Composer)
        self.assertNotEqual(composer.privateApplication, None)
