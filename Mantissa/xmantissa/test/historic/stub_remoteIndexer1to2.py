
from axiom.test.historic.stubloader import saveStub
from axiom.item import Item
from axiom.attributes import integer
from axiom.batch import processor

from xmantissa.fulltext import HypeIndexer, XapianIndexer, PyLuceneIndexer


class StubItem(Item):
    """
    Place-holder.  Stands in as an indexable thing, but no instances of this
    will ever actually be created.
    """
    __module__ = 'xmantissa.test.historic.stub_remoteIndexer1to2'

    attribute = integer()


StubSource = processor(StubItem)


def createDatabase(s):
    """
    Create a batch processor for L{StubItem} instances and add it as a message
    source to an instance of each of the kinds of indexers we support.
    """
    source = StubSource(store=s)
    for cls in [HypeIndexer, XapianIndexer, PyLuceneIndexer]:
        indexer = cls(store=s)
        source.addReliableListener(indexer)



if __name__ == '__main__':
    saveStub(createDatabase, 7053)
