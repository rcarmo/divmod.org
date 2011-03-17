# Copyright (c) 2008 Divmod.  See LICENSE for details.

"""
Tests for I{axiomatic mantissa} and other functionality provided by
L{axiom.plugins.mantissacmd}.
"""

from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath
from twisted.internet.ssl import Certificate

from axiom.store import Store
from axiom.plugins.mantissacmd import genSerial, Mantissa
from axiom.test.util import CommandStubMixin

from xmantissa.ixmantissa import IOfferingTechnician
from xmantissa.port import TCPPort, SSLPort
from xmantissa.web import SiteConfiguration
from xmantissa.terminal import SecureShellConfiguration
from xmantissa.plugins.baseoff import baseOffering


class MiscTestCase(TestCase):
    def test_genSerial(self):
        """
        Test that L{genSerial} returns valid unique serials.
        """
        s1 = genSerial()
        self.assertTrue(isinstance(s1, int), '%r must be an int' % (s1,))
        self.assertTrue(s1 >= 0, '%r must be positive' % (s1,))
        s2 = genSerial()
        self.assertNotEqual(s1, s2)



class CertificateTestCase(CommandStubMixin, TestCase):
    """
    Tests for the certificate generated by L{Mantissa}.
    """
    def _getCert(self):
        """
        Get the SSL certificate from an Axiom store directory.
        """
        certFile = FilePath(self.dbdir).child('files').child('server.pem')
        return Certificate.loadPEM(certFile.open('rb').read())


    def test_uniqueSerial(self):
        """
        Test that 'axiomatic mantissa' generates SSL certificates with a
        different unique serial on each invocation.
        """
        m = Mantissa()
        m.parent = self

        self.dbdir = self.mktemp()
        self.store = Store(self.dbdir)
        m.parseOptions(['--admin-password', 'foo'])
        cert1 = self._getCert()

        self.dbdir = self.mktemp()
        self.store = Store(self.dbdir)
        m.parseOptions(['--admin-password', 'foo'])
        cert2 = self._getCert()

        self.assertNotEqual(cert1.serialNumber(), cert2.serialNumber())


    def test_commonName(self):
        """
        C{axiomatic mantissa} generates an SSL certificate with the domain part
        of the admin username as its common name.
        """
        m = Mantissa()
        m.parent = self
        self.dbdir = self.mktemp()
        self.store = Store(filesdir=FilePath(self.dbdir).child("files").path)
        m.parseOptions(['--admin-user', 'admin@example.com', '--admin-password', 'foo'])
        cert = self._getCert()
        self.assertEqual(cert.getSubject().commonName, "example.com")



class MantissaCommandTests(TestCase, CommandStubMixin):
    """
    Tests for L{Mantissa}.
    """
    def setUp(self):
        """
        Create a store to use in tests.
        """
        self.filesdir = self.mktemp()
        self.siteStore = Store(filesdir=self.filesdir)


    def test_baseOffering(self):
        """
        L{Mantissa.installSite} installs the Mantissa base offering.
        """
        options = Mantissa()
        options.installSite(self.siteStore, u"example.com", u"", False)

        self.assertEqual(
            IOfferingTechnician(self.siteStore).getInstalledOfferingNames(),
            [baseOffering.name])


    def test_httpPorts(self):
        """
        L{Mantissa.installSite} creates a TCP port and an SSL port for the
        L{SiteConfiguration} which comes with the base offering it installs.
        """
        options = Mantissa()
        options.installSite(self.siteStore, u"example.com", u"", False)

        site = self.siteStore.findUnique(SiteConfiguration)
        tcps = list(self.siteStore.query(TCPPort, TCPPort.factory == site))
        ssls = list(self.siteStore.query(SSLPort, SSLPort.factory == site))

        self.assertEqual(len(tcps), 1)
        self.assertEqual(tcps[0].portNumber, 8080)
        self.assertEqual(len(ssls), 1)
        self.assertEqual(ssls[0].portNumber, 8443)
        self.assertNotEqual(ssls[0].certificatePath, None)


    def test_hostname(self):
        """
        L{Mantissa.installSite} sets the C{hostname} of the
        L{SiteConfiguration} to the domain name it is called with.
        """
        options = Mantissa()
        options.installSite(self.siteStore, u"example.net", u"", False)
        site = self.siteStore.findUnique(SiteConfiguration)
        self.assertEqual(site.hostname, u"example.net")


    def test_sshPorts(self):
        """
        L{Mantissa.installSite} creates a TCP port for the
        L{SecureShellConfiguration} which comes with the base offering it
        installs.
        """
        options = Mantissa()
        options.installSite(self.siteStore, u"example.com", u"", False)

        shell = self.siteStore.findUnique(SecureShellConfiguration)
        tcps = list(self.siteStore.query(TCPPort, TCPPort.factory == shell))

        self.assertEqual(len(tcps), 1)
        self.assertEqual(tcps[0].portNumber, 8022)