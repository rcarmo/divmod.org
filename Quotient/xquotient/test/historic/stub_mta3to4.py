# -*- test-case-name: xquotient.test.historic.test_mta3to4 -*-

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn

from xquotient.mail import MailTransferAgent


def createDatabase(store):
    """
    Create a MailTransferAgent with both SMTP and SMTP/SSL configured in the
    given Store.
    """
    mta = MailTransferAgent(
        store=store,
        portNumber=5025, securePortNumber=5465,
        certificateFile='server.pem',
        messageCount=432,
        domain='example.net')
    store.dbdir.child('server.pem').setContent('--- PEM ---\n')
    installOn(mta, store)


if __name__ == '__main__':
    saveStub(createDatabase, 11023)
