from axiom.test.historic.stubloader import saveStub
from xmantissa.webapp import PrivateApplication

def createDatabase(s):
    PrivateApplication(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10876)
