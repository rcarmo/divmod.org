
"""
Tests for upgrading a POP3Listener to move its TCP and SSL information into
separate objects.
"""

from twisted.application.service import IService

from axiom.test.historic.stubloader import StubbedTest
from axiom.userbase import LoginSystem
from axiom.dependency import installedOn

from xmantissa.port import TCPPort, SSLPort

from xquotient.popout import POP3Listener


class POP3ListenerUpgradeTests(StubbedTest):
    def test_preservedAttributes(self):
        """
        Test that the parts of the schema which are unchanged retain their
        information.
        """
        pop3 = self.store.findUnique(POP3Listener)
        self.assertEqual(pop3.certificateFile, 'server.pem')
        self.assertIdentical(pop3.userbase, self.store.findUnique(LoginSystem))


    def test_portNumber(self):
        """
        Test that the POP3Listener's portNumber attribute is transformed into a
        TCPPort instance.
        """
        pop3 = self.store.findUnique(POP3Listener)
        ports = list(self.store.query(TCPPort, TCPPort.factory == pop3))
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0].portNumber, 2110)
        self.assertEqual(installedOn(ports[0]), self.store)
        self.assertEqual(list(self.store.interfacesFor(ports[0])), [IService])


    def test_securePortNumber(self):
        """
        Test that the POP3Listener's securePortNumber attribute is transformed
        into an SSLPort instance.
        """
        pop3 = self.store.findUnique(POP3Listener)
        ports = list(self.store.query(SSLPort, SSLPort.factory == pop3))
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0].portNumber, 2995)
        certPath = self.store.newFilePath('pop3.pem')
        self.assertEqual(ports[0].certificatePath, certPath)
        self.assertEqual(certPath.getContent(), '--- PEM ---\n')
        self.assertEqual(installedOn(ports[0]), self.store)
        self.assertEqual(list(self.store.interfacesFor(ports[0])), [IService])


    def test_poweredDown(self):
        """
        Test that the POP3Listener is no longer an IService powerup for the
        store.
        """
        pop3 = self.store.findUnique(POP3Listener)
        powerups = list(self.store.powerupsFor(IService))
        self.failIfIn(pop3, powerups)
