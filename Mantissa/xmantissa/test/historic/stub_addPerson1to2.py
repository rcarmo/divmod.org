from axiom.test.historic.stubloader import saveStub
from xmantissa.people import AddPerson

def createDatabase(s):
    AddPerson(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10664)
