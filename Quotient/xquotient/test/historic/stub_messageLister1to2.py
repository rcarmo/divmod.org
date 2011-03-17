from axiom.test.historic.stubloader import saveStub
from xquotient.qpeople import MessageLister
from xmantissa.people import Organizer

def createDatabase(s):
    Organizer(store=s).installOn(s)
    MessageLister(store=s).installOn(s)

if __name__ == '__main__':
    saveStub(createDatabase, 10858)

