from axiom.test.historic import stubloader
from xquotient.spam import DSPAMFilter, Filter, dspam


class DSPAMFilterTestCase(stubloader.StubbedTest):
    if dspam is None:
        skip = "DSPAM not installed"

    def testUpgrade(self):
        """
        Ensure upgraded fields refer to correct items.
        """
        self.assertEqual(self.store.findUnique(DSPAMFilter).filter,
                         self.store.findUnique(Filter))
