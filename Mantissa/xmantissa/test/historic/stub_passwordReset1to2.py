from axiom.test.historic.stubloader import saveStub
from xmantissa.signup import PasswordReset

def createDatabase(s):
    PasswordReset(store=s, installedOn=s)

if __name__ == '__main__':
    saveStub(createDatabase, 8991)
