from axiom.test.historic.stubloader import saveStub
from xquotient.extract import URLExtract, PhoneNumberExtract, EmailAddressExtract

def createDatabase(s):
    for typ in (URLExtract, PhoneNumberExtract, EmailAddressExtract):
        typ(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 7052)
