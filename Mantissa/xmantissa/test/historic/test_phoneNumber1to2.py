from axiom.test.historic import stubloader
from xmantissa.people import PhoneNumber, Person

class PhoneNumberTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        phone = self.store.findUnique(PhoneNumber)
        person = self.store.findUnique(Person)
        self.assertIdentical(phone.person, person)
        self.assertEquals(phone.number, '555-1212')
