from axiom.test.historic.stubloader import saveStub
from xquotient.popout import POP3Listener
from axiom.userbase import LoginSystem

def createDatabase(s):
    LoginSystem(store=s).installOn(s)
    POP3Listener(store=s).installOn(s)

if __name__ == '__main__':
    saveStub(createDatabase, 10858)
