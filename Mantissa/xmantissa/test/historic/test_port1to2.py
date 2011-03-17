"""
Upgrader tests for L{xmantissa.port} items.
"""

from xmantissa.port import TCPPort, SSLPort
from xmantissa.web import SiteConfiguration

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.test.historic.stub_port1to2 import TCP_PORT, SSL_PORT

class PortInterfaceUpgradeTest(StubbedTest):
    """
    Schema upgrade tests for L{xmantissa.port} items.

    This upgrade adds an "interface" attribute.
    """
    def test_TCPPort(self):
        """
        Test the TCPPort 1->2 schema upgrade.
        """
        port = self.store.findUnique(TCPPort)
        self.assertEqual(port.portNumber, TCP_PORT)
        self.assertTrue(isinstance(port.factory, SiteConfiguration))
        self.assertEqual(port.interface, u'')

    def test_SSLPort(self):
        """
        Test the SSLPort 1->2 schema upgrade.
        """
        port = self.store.findUnique(SSLPort)
        self.assertEqual(port.portNumber, SSL_PORT)
        self.assertEqual(port.certificatePath,
                self.store.newFilePath('certificate'))
        self.assertTrue(isinstance(port.factory, SiteConfiguration))
        self.assertEqual(port.interface, u'')
