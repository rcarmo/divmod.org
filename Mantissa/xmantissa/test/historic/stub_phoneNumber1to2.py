from axiom.test.historic.stubloader import saveStub
from xmantissa.people import PhoneNumber, Person

def createDatabase(s):
    PhoneNumber(store=s,
                number=u'555-1212',
                type=u'default',
                person=Person(store=s,
                              name=u'Bob'))

if __name__ == '__main__':
    saveStub(createDatabase, 7052)
