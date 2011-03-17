from axiom.test.historic.stubloader import saveStub
from xmantissa.people import Organizer

def createDatabase(s):
    Organizer(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10664)
