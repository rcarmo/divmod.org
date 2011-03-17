from axiom.test.historic.stubloader import saveStub
from xmantissa.people import EmailAddress, Person

def createDatabase(s):
    EmailAddress(store=s,
                 address=u'bob@divmod.com',
                 type=u'default',
                 person=Person(store=s,
                               name=u'Bob'))

if __name__ == '__main__':
    saveStub(createDatabase, 7052)
