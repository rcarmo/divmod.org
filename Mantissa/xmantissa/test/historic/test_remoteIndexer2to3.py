
from axiom.test.historic.stubloader import StubbedTest
from axiom.batch import processor
from axiom.iaxiom import REMOTE

from xmantissa.fulltext import HypeIndexer, XapianIndexer, PyLuceneIndexer
from xmantissa.test.test_fulltext import FakeMessageSource

class RemoteIndexerTestCase(StubbedTest):
    """
    Test that the upgrade from 2 to 3 does not drop any information and that it
    resets the indexer so that the changes to the indexing behavior gets
    applied to all old messages.
    """
    def setUp(self):
        # Grab the FakeMessageSource and hold a reference to it so its
        # in-memory attributes stick around long enough for us to make some
        # assertions about them.
        result = StubbedTest.setUp(self)
        self.messageSource = self.store.findUnique(FakeMessageSource)
        return result

    def _test(self, indexerClass):
        indexer = self.store.findUnique(indexerClass)
        self.assertEquals(
            [self.messageSource],
            list(indexer.getSources()))
        # Make sure it got reset
        self.assertIn((indexer, REMOTE), self.messageSource.added)
        self.assertIn(indexer, self.messageSource.removed)

    def testUpgradeHype(self):
        return self._test(HypeIndexer)


    def testUpgradeXapian(self):
        return self._test(XapianIndexer)


    def testUpgradePyLucene(self):
        return self._test(PyLuceneIndexer)
