
"""
Test that a version 1 Composer powers up the Item it is installed on for
IMessageSender when it is upgraded to version 2.
"""

from axiom.test.historic.stubloader import StubbedTest

from xquotient.iquotient import IMessageSender
from xquotient.compose import Composer

class ComposerUpgradeTestCase(StubbedTest):
    def testUpgrade(self):
        self.assertIdentical(
            self.store.findUnique(Composer),
            IMessageSender(self.store))
