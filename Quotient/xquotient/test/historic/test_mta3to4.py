
"""
Test for upgrading a MailTransferAgent to move its TCP and SSL information onto
separate objects.
"""

from twisted.application.service import IService

from axiom.test.historic.stubloader import StubbedTest
from axiom.dependency import installedOn
from axiom.userbase import LoginSystem

from xmantissa.port import TCPPort, SSLPort

from xquotient.mail import MailTransferAgent


class MailTransferAgentTests(StubbedTest):
    def test_preservedAttributes(self):
        """
        Test that the parts of the schema which are unchanged retain their
        information.  This includes C{certificateFile} since a certificate is
        required to construct a factory which supports TLS.
        """
        mta = self.store.findUnique(MailTransferAgent)
        self.assertEqual(mta.certificateFile, 'server.pem')
        self.assertEqual(mta.messageCount, 432)
        self.assertEqual(mta.domain, 'example.net')
        self.assertIdentical(mta.userbase, self.store.findUnique(LoginSystem))


    def test_portNumber(self):
        """
        Test that the MailTransferAgent's portNumber attribute is transformed
        into a TCPPort instance.
        """
        mta = self.store.findUnique(MailTransferAgent)
        ports = list(self.store.query(TCPPort, TCPPort.factory == mta))
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0].portNumber, 5025)
        self.assertEqual(installedOn(ports[0]), self.store)
        self.assertEqual(list(self.store.interfacesFor(ports[0])), [IService])


    def test_securePortNumber(self):
        """
        Test that the MailTransferAgent's securePortNumber attribute is
        transformed into an SSLPort instance.
        """
        mta = self.store.findUnique(MailTransferAgent)
        ports = list(self.store.query(SSLPort, SSLPort.factory == mta))
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0].portNumber, 5465)
        certPath = self.store.newFilePath('mta.pem')
        self.assertEqual(ports[0].certificatePath, certPath)
        self.assertEqual(certPath.getContent(), '--- PEM ---\n')
        self.assertEqual(installedOn(ports[0]), self.store)
        self.assertEqual(list(self.store.interfacesFor(ports[0])), [IService])


    def test_poweredDown(self):
        """
        Test that the MailTransferAgent is no longer an IService powerup for
        the store.
        """
        mta = self.store.findUnique(MailTransferAgent)
        powerups = list(self.store.powerupsFor(IService))
        self.failIfIn(mta, powerups)
