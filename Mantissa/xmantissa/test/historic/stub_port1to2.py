
from OpenSSL.crypto import FILETYPE_PEM

from twisted.internet.ssl import PrivateCertificate, KeyPair

from axiom.item import Item
from axiom.attributes import text
from axiom.dependency import installOn
from axiom.test.historic.stubloader import saveStub

from xmantissa.port import TCPPort, SSLPort
from xmantissa.website import WebSite

# Unfortunately, the test module for this store binds ports.  So pick some
# improbably port numbers and hope they aren't bound.  If they are, the test
# will fail.  Hooray! -exarkun
TCP_PORT = 29415
SSL_PORT = 19224

def createDatabase(siteStore):
    """
    Populate the given Store with a TCPPort and SSLPort.
    """
    factory = WebSite(store=siteStore)
    installOn(factory, siteStore)
    installOn(
        TCPPort(store=siteStore, portNumber=TCP_PORT, factory=factory),
        siteStore)
    certificatePath = siteStore.newFilePath('certificate')

    key = KeyPair.generate()
    cert = key.selfSignedCert(1)
    certificatePath.setContent(
        cert.dump(FILETYPE_PEM) +
        key.dump(FILETYPE_PEM))

    installOn(
        SSLPort(store=siteStore, portNumber=SSL_PORT,
                certificatePath=certificatePath,
                factory=factory),
        siteStore)



if __name__ == '__main__':
    saveStub(createDatabase, 12731)
