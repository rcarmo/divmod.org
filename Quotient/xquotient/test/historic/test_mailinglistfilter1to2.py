from axiom.test.historic.stubloader import StubbedTest
from xquotient.filter import MailingListFilteringPowerup
from xquotient.mail import MessageSource

class FilterUpgradeTest(StubbedTest):
    def testMailingListFilter1to2(self):
        """
        Ensure that MailingListFilteringPowerup gets upgraded and that its
        'messageSource' attribute refers to this store's
        MessageSource.
        """
        f = self.store.findUnique(MailingListFilteringPowerup)
        self.assertEquals(f.messageSource, self.store.findUnique(MessageSource))
