# -*- test-case-name: xquotient.test.historic.test_inbox3to4filter -*-

"""
Create a stub database for upgrade of L{xquotient.inbox.Inbox} from version 3
to version 4, where there is a L{xquotient.spam.Filter} in the store
"""

from axiom.test.historic.stubloader import saveStub

from xquotient.quotientapp import QuotientBenefactor
def createDatabase(s):
    QuotientBenefactor().endow(None, s)

if __name__ == '__main__':
    saveStub(createDatabase, 10876)
