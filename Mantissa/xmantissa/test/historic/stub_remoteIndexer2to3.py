# -*- test-case-name: xmantissa.test.historic.test_remoteIndexer2to3 -*-

from axiom.test.historic.stubloader import saveStub

from xmantissa.fulltext import HypeIndexer, XapianIndexer, PyLuceneIndexer
from xmantissa.test.test_fulltext import FakeMessageSource

def createDatabase(s):
    """
    Create a several indexers in the given store and hook them each up to a
    dummy message source.
    """
    source = FakeMessageSource(store=s)
    for cls in [HypeIndexer, XapianIndexer, PyLuceneIndexer]:
        indexer = cls(store=s)
        indexer.addSource(source)


if __name__ == '__main__':
    saveStub(createDatabase, 8029)
