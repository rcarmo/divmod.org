
from hyperbola.hyperbola_model import HyperbolaPublicPresence

def createDatabase(s):
    s.findOrCreate(HyperbolaPublicPresence)

from axiom.test.historic.stubloader import saveStub

if __name__ == '__main__':
    saveStub(createDatabase, 11596)
