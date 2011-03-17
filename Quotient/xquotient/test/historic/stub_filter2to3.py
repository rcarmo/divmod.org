from axiom.test.historic.stubloader import saveStub
from xquotient.spam import Filter

def createDatabase(s):
    Filter(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10664)
