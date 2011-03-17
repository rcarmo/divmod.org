from axiom.test.historic.stubloader import StubbedTest
from xquotient.filter import RuleFilteringPowerup
from xquotient.mail import MessageSource

class FilterUpgradeTest(StubbedTest):
    def testRuleFilter1to2(self):
        """
        Ensure that RuleFilteringPowerup gets upgraded and that its
        'messageSource' attribute refers to this store's
        MessageSource.
        """
        f = self.store.findUnique(RuleFilteringPowerup)
        self.assertEquals(f.messageSource, self.store.findUnique(MessageSource))
