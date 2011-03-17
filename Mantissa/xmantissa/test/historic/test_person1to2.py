
"""
Tests for the upgrade from schema version 1 to 2 of the Person item which
adds the I{vip} attribute.
"""

from xmantissa.test.historic.stub_person1to2 import NAME, CREATED

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.people import Organizer, Person


class PersonUpgradeTests(StubbedTest):
    def test_attributes(self):
        """
        Existing attributes from the L{Person} should still be present and the
        new C{vip} attribute should be C{False}.
        """
        organizer = self.store.findUnique(Organizer)
        person = self.store.findUnique(
            Person, Person.storeID != organizer.storeOwnerPerson.storeID)
        self.assertIdentical(person.organizer, organizer)
        self.assertEqual(person.name, NAME)
        self.assertEqual(person.created, CREATED)
        self.assertEqual(person.vip, False)
