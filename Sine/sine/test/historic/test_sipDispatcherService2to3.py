
"""
Tests for the upgrade of L{SIPDispatcherService} from version 2 to version 3.
"""

from axiom.test.historic import stubloader
from axiom.userbase import LoginSystem

from sine.sipserver import SIPDispatcherService

class SIPServerTest(stubloader.StubbedTest):
    def test_upgrade(self):
        ss = self.store.findUnique(SIPDispatcherService)
        self.failUnless(isinstance(ss.userbase, LoginSystem))
