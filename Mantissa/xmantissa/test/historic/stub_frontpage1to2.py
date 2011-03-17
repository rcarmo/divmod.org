"""
Database-creation script for testing the version 1 to version 2 upgrader of
L{xmantissa.publicweb.FrontPage}.
"""
from axiom.test.historic.stubloader import saveStub
from xmantissa.publicweb import FrontPage

def createDatabase(s):
    """
    Create a L{FrontPage} item.
    """
    FrontPage(store=s, publicViews=17, privateViews=42)

if __name__ == '__main__':
    saveStub(createDatabase, 16183)

