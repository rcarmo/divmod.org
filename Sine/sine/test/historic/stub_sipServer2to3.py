# -*- test-case-name: sine.test.historic.test_sipServer2to3 -*-

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn

from sine.sipserver import SIPServer

def createDatabase(s):
    installOn(SIPServer(store=s), s)

if __name__ == '__main__':
    saveStub(createDatabase, 17606)
