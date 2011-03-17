
from axiom.test.historic import stubloader
from xmantissa.fulltext import PyLuceneIndexer

class PyLuceneIndexerTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        index = self.store.findUnique(PyLuceneIndexer)
        self.assertEqual(index.indexDirectory, 'foo.index')
        # we called reset(), and there are no indexed items
        self.assertEqual(index.indexCount, 0)
        self.assertEqual(index.installedOn, self.store)
