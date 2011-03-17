from twisted.python.filepath import FilePath

from axiom.test.historic.stubloader import saveStub
from xmantissa.fulltext import PyLuceneIndexer

def createDatabase(s):
    PyLuceneIndexer(store=s,
                    installedOn=s,
                    indexCount=23,
                    indexDirectory=u'foo.index').installOn(s)

if __name__ == '__main__':
    saveStub(createDatabase, 9044)
