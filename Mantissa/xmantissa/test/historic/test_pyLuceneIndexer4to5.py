# Copyright 2005 Divmod, Inc.  See LICENSE file for details

from axiom.test.historic import stubloader

from xmantissa.ixmantissa import IFulltextIndexer
from xmantissa.fulltext import PyLuceneIndexer

class PyLuceneIndexerTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        """
        The PyLuceneIndexer should be findable by its interface now.  It also
        should have been reset since it was most likely slightly corrupt, with
        respect to deleted documents.
        """
        index = IFulltextIndexer(self.store)
        self.failUnless(isinstance(index, PyLuceneIndexer))
        self.assertEqual(index.indexDirectory, 'foo.index')
        # we called reset(), and there are no indexed items
        self.assertEqual(index.indexCount, 0)
        self.assertEqual(index.installedOn, self.store)
