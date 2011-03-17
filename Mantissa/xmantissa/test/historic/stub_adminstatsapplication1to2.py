from axiom.test.historic.stubloader import saveStub
from xmantissa.webadmin import AdminStatsApplication

def createDatabase(s):
    AdminStatsApplication(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 11254)
