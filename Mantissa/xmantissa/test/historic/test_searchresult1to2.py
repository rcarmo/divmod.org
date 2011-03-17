
from axiom.test.historic.stubloader import StubbedTest

from xmantissa.search import SearchResult

class SearchResultUpgradeTestCase(StubbedTest):
    def test_removal(self):
        """
        SearchResults are no longer necessary, so the upgrade to version two
        should delete them completely.
        """
        self.assertEquals(
            list(self.store.query(SearchResult)),
            [])
