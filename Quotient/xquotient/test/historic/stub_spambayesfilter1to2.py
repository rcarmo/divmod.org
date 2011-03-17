from axiom.test.historic.stubloader import saveStub
from axiom.userbase import LoginMethod
from xquotient.spam import SpambayesFilter

def createDatabase(s):
    SpambayesFilter(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10876)
