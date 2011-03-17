# -*- test-case-name: xmantissa.test.historic.test_pyLuceneIndexer4to5 -*-
# Copyright 2005 Divmod, Inc.  See LICENSE file for details

from axiom.test.historic.stubloader import saveStub

from xmantissa.test.historic.stub_pyLuceneIndexer3to4 import createDatabase as _createDatabase

def createDatabase(*a, **kw):
    return _createDatabase(*a, **kw)

if __name__ == '__main__':
    saveStub(createDatabase, 10568)
