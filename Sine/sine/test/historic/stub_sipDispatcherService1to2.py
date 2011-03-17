from axiom.test.historic.stubloader import saveStub
from sine.sipserver import SIPDispatcherService

def createDatabase(s):
    SIPDispatcherService(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10664)
