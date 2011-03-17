
"""
Create an L{AnonymousSite} in a database by itself.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn

from xmantissa.publicweb import AnonymousSite

def createDatabase(s):
    installOn(AnonymousSite(store=s), s)

if __name__ == '__main__':
    saveStub(createDatabase, 16560)
