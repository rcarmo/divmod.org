
"""
Test for upgrading a WebSite to move its TCP and SSL information onto separate
objects.
"""

from twisted.application.service import IService
from twisted.cred.portal import IRealm

from nevow.inevow import IResource

from axiom.test.historic.stubloader import StubbedTest
from axiom.dependency import installedOn
from axiom.userbase import LoginSystem

from xmantissa.port import TCPPort, SSLPort
from xmantissa.web import SiteConfiguration
from xmantissa.website import WebSite
from xmantissa.publicweb import AnonymousSite
from xmantissa.ixmantissa import IMantissaSite, IWebViewer

from xmantissa.test.historic.stub_website4to5 import cert


class WebSiteUpgradeTests(StubbedTest):
    expectedHostname = u"example.net"

    def test_preservedAttributes(self):
        """
        Test that some data from the simple parts of the schema is preserved.
        """
        site = self.store.findUnique(SiteConfiguration)
        self.assertEqual(site.httpLog, self.store.filesdir.child('httpd.log'))
        self.assertEqual(site.hostname, self.expectedHostname)


    def test_portNumber(self):
        """
        Test that the WebSite's portNumber attribute is transformed into a
        TCPPort instance.
        """
        site = self.store.findUnique(SiteConfiguration)
        ports = list(self.store.query(TCPPort, TCPPort.factory == site))
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0].portNumber, 8088)
        self.assertEqual(installedOn(ports[0]), self.store)
        self.assertEqual(list(self.store.interfacesFor(ports[0])), [IService])


    def test_securePortNumber(self):
        """
        Test that the WebSite's securePortNumber attribute is transformed into
        an SSLPort instance.
        """
        site = self.store.findUnique(SiteConfiguration)
        ports = list(self.store.query(SSLPort, SSLPort.factory == site))
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0].portNumber, 6443)
        certPath = self.store.newFilePath('server.pem')
        self.assertEqual(ports[0].certificatePath, certPath)
        self.assertEqual(certPath.getContent(), cert)
        self.assertEqual(installedOn(ports[0]), self.store)
        self.assertEqual(list(self.store.interfacesFor(ports[0])), [IService])


    def test_deleted(self):
        """
        The L{WebSite} should no longer exist in the site store.
        """
        self.assertEqual(list(self.store.query(WebSite)), [])


    def test_anonymousSite(self):
        """
        An L{AnonymousSite} is created and installed on the site store.
        """
        resource = self.store.findUnique(AnonymousSite)
        self.assertEqual(list(self.store.interfacesFor(resource)),
                         [IResource, IMantissaSite, IWebViewer])
        self.assertIdentical(installedOn(resource), self.store)
        self.assertIdentical(resource.loginSystem, IRealm(self.store))


    def test_singleLoginSystem(self):
        """
        The upgrade should not create extra L{LoginSystem} items.
        """
        self.assertEqual(self.store.query(LoginSystem).count(), 1)


    def test_userStore(self):
        """
        Test that WebSites in user stores upgrade without errors.
        """
        ls = self.store.findUnique(LoginSystem)
        substore = ls.accountByAddress(u'testuser', u'localhost').avatars.open()
        d = substore.whenFullyUpgraded()
        def fullyUpgraded(ignored):
            web = substore.findUnique(WebSite)
            self.assertEqual(web.hitCount, 321)
        return d.addCallback(fullyUpgraded)


    def tearDown(self):
        d = StubbedTest.tearDown(self)
        def flushit(ign):
            from epsilon.cooperator import SchedulerStopped
            self.flushLoggedErrors(SchedulerStopped)
            return ign
        return d.addCallback(flushit)
