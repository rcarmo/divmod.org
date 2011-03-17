
"""
Test that the 2->3 upgrader for Composer constructs a FromAddress item out of
the login credentials in the database and sets Composer.fromAddress to point
to the item
"""

from axiom.test.historic.stubloader import StubbedTest

from axiom.userbase import LoginMethod
from xquotient.compose import Composer
from xquotient.smtpout import FromAddress


class ComposerUpgradeTestCase(StubbedTest):
    def testUpgrade(self):
        composer = self.store.findUnique(Composer)
