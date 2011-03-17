from axiom.test.historic import stubloader
from xmantissa.people import EmailAddress, Person

class EmailAddressTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        ea = self.store.findUnique(EmailAddress)
        person = self.store.findUnique(Person)
        self.assertIdentical(ea.person, person)
        self.assertEquals(ea.address, 'bob@divmod.com')
