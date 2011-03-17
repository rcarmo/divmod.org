from axiom.test.historic import stubloader
from xquotient.extract import URLExtract, PhoneNumberExtract, EmailAddressExtract

class ExtractUpgradeTest(stubloader.StubbedTest):
    def testUpgrade(self):
        for typ in (URLExtract, PhoneNumberExtract, EmailAddressExtract):
            self.assertEquals(self.store.count(typ), 0)
