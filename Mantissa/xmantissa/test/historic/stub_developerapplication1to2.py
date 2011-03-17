from axiom.test.historic.stubloader import saveStub
from xmantissa.webadmin import DeveloperApplication

def createDatabase(s):
    DeveloperApplication(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 10876)
