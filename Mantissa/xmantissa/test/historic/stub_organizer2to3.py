from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn

from xmantissa.people import Organizer

def createDatabase(s):
    installOn(Organizer(store=s), s)



if __name__ == '__main__':
    saveStub(createDatabase, 13142)
