# -*- test-case-name: xmantissa.test.historic.test_ticket1to2 -*-
"""
Stub for Ticket upgrade. Creates a Ticket using the normal signup
machinery.
"""
from axiom.test.historic.stubloader import saveStub
from xmantissa.signup import SignupConfiguration, FreeTicketSignup, Multifactor
from xmantissa.provisioning import BenefactorFactory
from xmantissa.webadmin import AdministrativeBenefactor

def createDatabase(s):
    mff = BenefactorFactory("", "", AdministrativeBenefactor)
    sc = SignupConfiguration(store=s)
    sc.installOn(s)
    s.parent = s
    signup = sc.createSignup(u'bob', FreeTicketSignup, {'prefixURL': u'/signup'},
                             {mff: {}}, None,
                             u'Sign Up')
    t = signup.booth.createTicket(signup, u'bob@example.com', signup.benefactor)

if __name__ == '__main__':
    saveStub(createDatabase, 10876)
