
from axiom.test.historic.stubloader import StubbedTest
from axiom.batch import processor

from xmantissa.fulltext import HypeIndexer, XapianIndexer, PyLuceneIndexer
from xmantissa.test.historic.stub_remoteIndexer1to2 import StubSource


class RemoteIndexerTestCase(StubbedTest):
    """
    Test that each kind of remote indexer correctly becomes associated with an
    item source when being upgraded to version two.
    """
    def testUpgradeHype(self):
        indexer = self.store.findUnique(HypeIndexer)
        self.assertEquals(
            [self.store.findUnique(StubSource)],
            list(indexer.getSources()))


    def testUpgradeXapian(self):
        indexer = self.store.findUnique(XapianIndexer)
        self.assertEquals(
            [self.store.findUnique(StubSource)],
            list(indexer.getSources()))


    def testUpgradePyLucene(self):
        indexer = self.store.findUnique(PyLuceneIndexer)
        self.assertEquals(
            [self.store.findUnique(StubSource)],
            list(indexer.getSources()))
