# -*- test-case-name xquotient.test.test_historic.test_fromAddress1to2 -*-

"""
Create stub database for upgrade of L{xquotient.compose.FromAddress} from
version 1 to version 2.
"""
from axiom.test.historic.stubloader import saveStub
from axiom.userbase import LoginMethod

from xquotient.compose import FromAddress

def createDatabase(s):
    LoginMethod(store=s,
                localpart=u'foo',
                domain=u'bar',
                verified=True,
                protocol=u'*',
                account=s,
                internal=False)

    FromAddress(store=s,
                address=u'foo@bar',
                smtpHost=u'bar',
                smtpPort=26,
                smtpUsername=u'foo',
                smtpPassword=u'secret')
    FromAddress(store=s,
                address=u'foo2@bar',
                smtpHost=u'bar',
                smtpPort=26,
                smtpUsername=u'foo2',
                smtpPassword=u'secret')

if __name__ == '__main__':
    saveStub(createDatabase, 9459)
