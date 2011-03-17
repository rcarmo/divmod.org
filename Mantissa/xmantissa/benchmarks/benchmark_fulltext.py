
"""
Fulltext index a message a fixed number of times with PyLucene via the Mantissa
fulltext indexing API.
"""

from zope.interface import implements

from epsilon.scripts import benchmark

from axiom import store

from xmantissa import ixmantissa, fulltext


class Message(object):
    implements(ixmantissa.IFulltextIndexable)

    def uniqueIdentifier(self):
        return str(id(self))


    def textParts(self):
        return [
            u"Hello, how are you.  Please to be "
            u"seeing this message as an indexer test." * 100]


    def keywordParts(self):
            return {u'foo': "A Keyword"}


    def documentType(self):
        return u'message'


    def sortKey(self):
        return u''

def main():
    s = store.Store("lucene.axiom")
    indexer = fulltext.PyLuceneIndexer(store=s)

    benchmark.start()
    writer = indexer.openWriteIndex()
    for i in xrange(10000):
        writer.add(Message())
    writer.close()
    benchmark.stop()



if __name__ == '__main__':
    main()
