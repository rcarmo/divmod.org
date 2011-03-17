from axiom.test.historic import stubloader
from xmantissa.people import Organizer
from xmantissa.webapp import PrivateApplication

class OrganizerTest(stubloader.StubbedTest):
    def testUpgrade(self):
        o = self.store.findUnique(Organizer)
        self.failUnless(isinstance(o._webTranslator, PrivateApplication))
