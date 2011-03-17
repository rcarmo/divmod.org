
"""
Tests for the upgrade from schema version 2 to 3 of the Person item which
changed the I{name} attribute from case-sensitive to case-insensitive.
"""

from xmantissa.test.historic.stub_person2to3 import NAME, CREATED

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.people import Organizer, Person


class PersonUpgradeTests(StubbedTest):
    def test_attributes(self):
        """
        Existing attributes from the L{Person} should still be present and have
        the same value as it did prior to the upgrade.
        """
        organizer = self.store.findUnique(Organizer)
        person = self.store.findUnique(
            Person, Person.storeID != organizer.storeOwnerPerson.storeID)
        self.assertIdentical(person.organizer, organizer)
        self.assertEqual(person.name, NAME)
        self.assertEqual(person.created, CREATED)
        self.assertEqual(person.vip, False)
