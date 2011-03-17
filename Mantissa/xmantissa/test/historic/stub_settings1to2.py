from axiom.test.historic.stubloader import saveStub
from xmantissa.settings import Settings

def createDatabase(s):
    Settings(store=s, installedOn=s)

if __name__ == '__main__':
    saveStub(createDatabase, 8528)
