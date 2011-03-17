from axiom.test.historic.stubloader import saveStub

from xmantissa.signup import FreeTicketSignup

def createDatabase(s):
    FreeTicketSignup(store=s,
                     prefixURL=u'/a/b',
                     booth=s,
                     benefactor=s,
                     emailTemplate=u'TEMPLATE!')

if __name__ == '__main__':
    saveStub(createDatabase, 5809)
