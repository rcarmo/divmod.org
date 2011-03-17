# -*- test-case-name: xmantissa.test.historic.test_searchresult1to2 -*-

from axiom.test.historic.stubloader import saveStub

from xmantissa.search import SearchResult

def createDatabase(s):
    SearchResult(store=s, indexedItem=s, identifier=0)

if __name__ == '__main__':
    saveStub(createDatabase, 7976)
