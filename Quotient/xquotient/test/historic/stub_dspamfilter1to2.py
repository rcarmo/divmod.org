from axiom.test.historic.stubloader import saveStub
from axiom.userbase import LoginMethod
from xquotient.spam import DSPAMFilter

def createDatabase(s):
    LoginMethod(store=s,
                localpart=u'foo',
                domain=u'bar',
                verified=True,
                protocol=u'*',
                account=s,
                internal=False)
    DSPAMFilter(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10876)
