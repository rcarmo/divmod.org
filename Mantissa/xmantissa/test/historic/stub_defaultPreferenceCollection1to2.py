
from xmantissa import prefs

def createDatabase(s):
    prefs.DefaultPreferenceCollection(store=s)

from axiom.test.historic.stubloader import saveStub

if __name__ == '__main__':
    saveStub(createDatabase)
