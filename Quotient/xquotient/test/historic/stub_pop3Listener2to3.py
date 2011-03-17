# -*- test-case-name: xquotient.test.historic.test_pop3Listener2to3 -*-

from axiom.test.historic.stubloader import saveStub

from axiom.dependency import installOn

from xquotient.popout import POP3Listener


def createDatabase(store):
    """
    Add a POP3Listener configured to listen for POP3 and POP3S connections to
    the given store.
    """
    pop3 = POP3Listener(store=store, portNumber=2110, securePortNumber=2995, certificateFile='server.pem')
    store.dbdir.child('server.pem').setContent('--- PEM ---\n')
    installOn(pop3, store)


if __name__ == '__main__':
    saveStub(createDatabase, 11023)
