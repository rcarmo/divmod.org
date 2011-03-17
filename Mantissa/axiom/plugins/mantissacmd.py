
import sys, os, struct

from zope.interface import directlyProvides

from twisted.python import util
from twisted.cred import portal
from twisted.plugin import IPlugin

from axiom import errors as eaxiom
from axiom.scripts import axiomatic
from axiom.attributes import AND
from axiom.dependency import installOn
from axiom.iaxiom import IVersion

from xmantissa.ixmantissa import IOfferingTechnician
from xmantissa import webadmin, publicweb, stats
from xmantissa.web import SiteConfiguration
from xmantissa.terminal import SecureShellConfiguration
from xmantissa.port import TCPPort, SSLPort
from xmantissa.plugins.baseoff import baseOffering

# PortConfiguration isn't used here, but it's a plugin, so it gets discovered
# here.
from xmantissa.port import PortConfiguration
#version also gets registered as a plugin here.
from xmantissa import version

from epsilon.asplode import splode
from epsilon.scripts import certcreate

directlyProvides(version, IPlugin, IVersion)



def gtpswd(prompt, confirmPassword):
    """
    Temporary wrapper for Twisted's getPassword until a version that supports
    customizing the 'confirm' prompt is released.
    """
    try:
        return util.getPassword(prompt=prompt,
                                confirmPrompt=confirmPassword,
                                confirm=True)
    except TypeError:
        return util.getPassword(prompt=prompt,
                                confirm=True)



def genSerial():
    """
    Generate a (hopefully) unique integer usable as an SSL certificate serial.
    """
    return abs(struct.unpack('!l', os.urandom(4))[0])



class Mantissa(axiomatic.AxiomaticCommand):
    """
    Create all the moving parts necessary to begin interactively developing a
    Mantissa application component of your own.
    """

    # Throughout here we use findOrCreate rather than raw creation so that
    # duplicate installations of these components do not create garbage
    # objects.

    # Yea?  Where's the unit tests for that?  And who re-runs "axiomatic
    # mantissa" on the same Store multiple times anyway?  Better that it should
    # give an error than transparently... do... something... maybe...  I'm
    # actively not preserving the idempotency behavior in my changes to this
    # code. -exarkun

    name = 'mantissa'
    description = 'Blank Mantissa service'

    longdesc = __doc__

    optParameters = [
        ('admin-user', 'a', 'admin@localhost',
         'Account name for the administrative user.'),
        ('admin-password', 'p', None,
         'Password for the administrative user '
         '(if omitted, will be prompted for).'),
        ('public-url', None, '',
         'URL at which to publish the public front page.')]

    def postOptions(self):
        siteStore = self.parent.getStore()
        if self['admin-password'] is None:
            pws = u'Divmod\u2122 Mantissa\u2122 password for %r: ' % (self['admin-user'],)
            self['admin-password'] = gtpswd((u'Enter ' + pws).encode(sys.stdout.encoding, 'ignore'),
                                            (u'Confirm ' + pws).encode(sys.stdout.encoding, 'ignore'))


        publicURL = self.decodeCommandLine(self['public-url'])
        adminUser = self.decodeCommandLine(self['admin-user'])
        adminPassword = self['admin-password']

        adminLocal, adminDomain = adminUser.split(u'@')

        siteStore.transact(self.installSite, siteStore, adminDomain, publicURL)
        siteStore.transact(
            self.installAdmin, siteStore, adminLocal, adminDomain, adminPassword)


    def installSite(self, siteStore, domain, publicURL, generateCert=True):
        """
        Create the necessary items to run an HTTP server and an SSH server.
        """
        certPath = siteStore.filesdir.child("server.pem")
        if generateCert and not certPath.exists():
            certcreate.main([
                    '--filename', certPath.path, '--quiet',
                    '--serial-number', str(genSerial()),
                    '--hostname', domain])

        # Install the base Mantissa offering.
        IOfferingTechnician(siteStore).installOffering(baseOffering)

        # Make the HTTP server baseOffering includes listen somewhere.
        site = siteStore.findUnique(SiteConfiguration)
        site.hostname = domain
        installOn(
            TCPPort(store=siteStore, factory=site, portNumber=8080),
            siteStore)
        installOn(
            SSLPort(store=siteStore, factory=site, portNumber=8443,
                    certificatePath=certPath),
            siteStore)

        # Make the SSH server baseOffering includes listen somewhere.
        shell = siteStore.findUnique(SecureShellConfiguration)
        installOn(
            TCPPort(store=siteStore, factory=shell, portNumber=8022),
            siteStore)

        # Install a front page on the top level store so that the
        # developer will have something to look at when they start up
        # the server.
        fp = siteStore.findOrCreate(publicweb.FrontPage, prefixURL=u'')
        installOn(fp, siteStore)


    def installAdmin(self, s, username, domain, password):
        # Add an account for our administrator, so they can log in through the
        # web.
        r = portal.IRealm(s)
        try:
            acc = r.addAccount(username, domain, password, internal=True, verified=True)
        except eaxiom.DuplicateUser:
            acc = r.accountByAddress(username, domain)

        accStore = acc.avatars.open()
        accStore.transact(webadmin.endowAdminPowerups, accStore)



class Generate(axiomatic.AxiomaticCommand):
    name = "project"

    # This will show up next to the name in --help output
    description = "Generate most basic skeleton of a Mantissa app"

    optParameters = [
        ('name', 'n', None, 'The name of the app to deploy'),
        ]

    def postOptions(self):
        if self['name'] is None:
            proj = ''
            while( proj == ''):
                try:
                    proj = raw_input("Please provide the name of the app to deploy: " )
                except KeyboardInterrupt:
                    raise SystemExit()
        else:
            proj = self.decodeCommandLine(self['name'])
        proj = proj.lower()
        capproj = proj.capitalize()
        print "Creating", capproj, "in", capproj

        fObj = file(util.sibpath(__file__, 'template.txt'))

        splode(fObj.readlines(), proj, capproj)



class RemoteStatsAdd(axiomatic.AxiomaticSubCommand):

    optParameters = [
        ("host", "h", None, "The host accepting statistical data."),
        ("port", "p", None, "The port to connect to."),
        ]

    def postOptions(self):
        s = self.parent.parent.getStore()
        s.transact(self.installCollector, s, self['host'], int(self['port']))


    def installCollector(self, s, host, port):
        ss = portal.IRealm(s).accountByAddress(u'mantissa',
                                               None).avatars.open()
        stats.RemoteStatsObserver(store=ss, hostname=host, port=port)



class RemoteStatsList(axiomatic.AxiomaticSubCommand):
    def postOptions(self):
        s = self.parent.parent.getStore()
        ss = portal.IRealm(s).accountByAddress(u'mantissa',
                                               None).avatars.open()
        for i, obs in enumerate(ss.query(stats.RemoteStatsObserver)):
            print "%s) %s:%s" % (i, obs.hostname, obs.port)



class RemoteStatsRemove(axiomatic.AxiomaticSubCommand):
    optParameters = [
        ("host", "h", None, "The hostname of the observer to remove."),
        ("port", "p", None, "The port of the observer to remove."),
        ]
    def postOptions(self):
        s = self.parent.parent.getStore()
        ss = portal.IRealm(s).accountByAddress(u'mantissa',
                                               None).avatars.open()
        for obs in ss.query(stats.RemoteStatsObserver,
                            AND(stats.RemoteStatsObserver.hostname==self['host'], stats.RemoteStatsObserver.port==int(self['port']))):
            obs.deleteFromStore()



class RemoteStats(axiomatic.AxiomaticCommand):
    name = "stats"
    description = "Control remote statistics collection"

    subCommands = [("add", None, RemoteStatsAdd, "Submit Mantissa statistical data to another server"),
                   ("list", None, RemoteStatsList, "List remote targets for stats delivery"),
                   ("remove", None, RemoteStatsRemove, "Remove a remote stats target")]


__all__ = [
    PortConfiguration.__name__, Mantissa.__name__, Generate.__name__,
    RemoteStats.__name__, RemoteStatsAdd.__name__, RemoteStatsList.__name__,
    RemoteStatsRemove.__name__]
