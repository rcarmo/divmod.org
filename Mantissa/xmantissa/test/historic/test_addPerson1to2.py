from axiom.test.historic import stubloader
from xmantissa.people import AddPerson, Organizer
from xmantissa.webapp import PrivateApplication

class AddPersonTest(stubloader.StubbedTest):
    def testUpgrade(self):
        ap = self.store.findUnique(AddPerson)
        self.failUnless(isinstance(ap.organizer, Organizer))
