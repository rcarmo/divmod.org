from axiom.test.historic import stubloader
from xquotient.spam import SpambayesFilter, Filter


class SpambayesFilterTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        """
        Ensure upgraded fields refer to correct items.
        """
        self.assertEqual(self.store.findUnique(SpambayesFilter).filter,
                         self.store.findUnique(Filter))
