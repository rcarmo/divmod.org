from axiom.test.historic.stubloader import saveStub
from sine.sipserver import SIPServer

def createDatabase(s):
    SIPServer(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10664)
