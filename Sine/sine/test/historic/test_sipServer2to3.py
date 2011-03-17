
"""
Tests for the upgrade of L{SIPServer} from version 2 to version 3.
"""

from axiom.test.historic import stubloader
from axiom.userbase import LoginSystem

from sine.sipserver import SIPServer


class SIPServerTest(stubloader.StubbedTest):
    def test_upgrade(self):
        ss = self.store.findUnique(SIPServer)
        self.failUnless(isinstance(ss.userbase, LoginSystem))
        # Stop it now, because it started up a dang SIPTransport.  Oh, darn.
        # SIPServer has no stopService.  Guess I'll just gank it.
        return ss.port.stopListening()

