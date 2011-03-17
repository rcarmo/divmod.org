from axiom.test.historic import stubloader
from xmantissa.people import Organizer, Person, RealName
from xmantissa.webapp import PrivateApplication

class OrganizerTest(stubloader.StubbedTest):
    """
    Test L{Organizer}'s 2->3 upgrader.
    """
    def test_storeOwnerPerson(self):
        """
        Test that L{Organizer.storeOwnerPerson} is set to a L{Person} with no
        L{RealName}, since there isn't enough information in the store to
        construct one.
        """
        o = self.store.findUnique(Organizer)
        self.assertIdentical(o.storeOwnerPerson, self.store.findUnique(Person))
        self.assertEqual(self.store.count(RealName), 0)


    def test_webTranslator(self):
        """
        Test that L{Organizer._webTranslator} is preserved across versions.
        """
        o = self.store.findUnique(Organizer)
        self.assertIdentical(o._webTranslator, self.store.findUnique(PrivateApplication))
