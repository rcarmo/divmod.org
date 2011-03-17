from axiom.test.historic.stubloader import saveStub
from xquotient.grabber import GrabberConfiguration

def createDatabase(s):
    GrabberConfiguration(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10876)
