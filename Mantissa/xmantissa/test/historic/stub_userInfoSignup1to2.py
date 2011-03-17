from axiom.test.historic.stubloader import saveStub

from xmantissa.signup import UserInfoSignup, Multifactor
from xmantissa.webadmin import AdministrativeBenefactor

def createDatabase(s):
    ab = AdministrativeBenefactor(store=s)
    mf = Multifactor(store=s)
    mf.add(ab)
    UserInfoSignup(store=s,
                   prefixURL=u'/a/b',
                   booth=s,
                   benefactor=mf,
                   emailTemplate=u'TEMPLATE!',
                   prompt=u'OK?')

if __name__ == '__main__':
    saveStub(createDatabase, 10664)
