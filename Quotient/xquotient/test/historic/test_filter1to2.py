
from axiom.test.historic.stubloader import StubbedTest

from xquotient.spam import Filter

class FilterTestCase(StubbedTest):
    def test_postiniChanges(self):
        """
        Version 2 added a couple postini-related attributes.  Make sure the
        existing attributes are still set and the new ones have reasonable
        values.
        """
        filter = self.store.findUnique(Filter)
        self.assertEquals(filter.usePostiniScore, False)
        self.assertEquals(filter.postiniThreshhold, 0.03)
