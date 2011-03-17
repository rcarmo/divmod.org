# -*- test-case-name: xmantissa.test.test_webcmd -*-

import os
import sys

from twisted.python import reflect
from twisted.python.usage import UsageError

from axiom import item, attributes
from axiom.dependency import installOn, onlyInstallPowerups
from axiom.scripts import axiomatic

from xmantissa.web import SiteConfiguration
from xmantissa.website import StaticSite, APIKey
from xmantissa import ixmantissa, webadmin
from xmantissa.plugins.baseoff import baseOffering


class WebConfiguration(axiomatic.AxiomaticCommand):
    name = 'web'
    description = 'Web.  Yay.'

    optParameters = [
        ('http-log', 'h', None,
         'Filename (relative to files directory of the store) to which to log '
         'HTTP requests (empty string to disable)'),
        ('hostname', 'H', None,
         'Canonical hostname for this server (used in URL generation).'),
        ('urchin-key', '', None,
         'Google Analytics API key for this site')]

    def __init__(self, *a, **k):
        super(WebConfiguration, self).__init__(*a, **k)
        self.staticPaths = []


    didSomething = 0

    def postOptions(self):
        siteStore = self.parent.getStore()

        # Make sure the base mantissa offering is installed.
        offeringTech = ixmantissa.IOfferingTechnician(siteStore)
        offerings = offeringTech.getInstalledOfferingNames()
        if baseOffering.name not in offerings:
            raise UsageError(
                "This command can only be used on Mantissa databases.")

        # It is, we can make some simplifying assumptions.  Specifically,
        # there is exactly one SiteConfiguration installed.
        site = siteStore.findUnique(SiteConfiguration)

        if self['http-log'] is not None:
            if self['http-log']:
                site.httpLog = siteStore.filesdir.preauthChild(
                    self['http-log'])
            else:
                site.httpLog = None

        if self['hostname'] is not None:
            if self['hostname']:
                site.hostname = self.decodeCommandLine(self['hostname'])
            else:
                raise UsageError("Hostname may not be empty.")

        if self['urchin-key'] is not None:
            # Install the API key for Google Analytics, to enable tracking for
            # this site.
            APIKey.setKeyForAPI(
                siteStore, APIKey.URCHIN, self['urchin-key'].decode('ascii'))


        # Set up whatever static content was requested.
        for webPath, filePath in self.staticPaths:
            staticSite = siteStore.findFirst(
                StaticSite, StaticSite.prefixURL == webPath)
            if staticSite is not None:
                staticSite.staticContentPath = filePath
            else:
                staticSite = StaticSite(
                    store=siteStore,
                    staticContentPath=filePath,
                    prefixURL=webPath,
                    sessionless=True)
                onlyInstallPowerups(staticSite, siteStore)


    def opt_static(self, pathMapping):
        webPath, filePath = self.decodeCommandLine(pathMapping).split(os.pathsep, 1)
        if webPath.startswith('/'):
            webPath = webPath[1:]
        self.staticPaths.append((webPath, os.path.abspath(filePath)))


    def opt_list(self):
        self.didSomething = 1
        s = self.parent.getStore()
        for ws in s.query(SiteConfiguration):
            print 'The hostname is', ws.hostname
            if ws.httpLog is not None:
                print 'Logging HTTP requests to', ws.httpLog
            break
        else:
            print 'No configured webservers.'


        def powerupsWithPriorityFor(interface):
            for cable in s.query(
                item._PowerupConnector,
                attributes.AND(item._PowerupConnector.interface == unicode(reflect.qual(interface)),
                               item._PowerupConnector.item == s),
                sort=item._PowerupConnector.priority.descending):
                yield cable.powerup, cable.priority

        print 'Sessionless plugins:'
        for srp, prio in powerupsWithPriorityFor(ixmantissa.ISessionlessSiteRootPlugin):
            print '  %s (prio. %d)' % (srp, prio)
        print 'Sessioned plugins:'
        for srp, prio in powerupsWithPriorityFor(ixmantissa.ISiteRootPlugin):
            print '  %s (prio. %d)' % (srp, prio)
        sys.exit(0)

    opt_static.__doc__ = """
    Add an element to the mapping of web URLs to locations of static
    content on the filesystem (webpath%sfilepath)
    """ % (os.pathsep,)



class WebAdministration(axiomatic.AxiomaticCommand):
    name = 'web-admin'
    description = 'Administrative controls for the web'

    optFlags = [
        ('admin', 'a', 'Enable administrative controls'),
        ('developer', 'd', 'Enable developer controls'),

        ('disable', 'D', 'Remove the indicated options, instead of enabling them.'),
        ]

    def postOptions(self):
        s = self.parent.getStore()

        didSomething = False

        if self['admin']:
            didSomething = True
            if self['disable']:
                for app in s.query(webadmin.AdminStatsApplication):
                    app.deleteFromStore()
                    break
                else:
                    raise UsageError('Administrator controls already disabled.')
            else:
                installOn(webadmin.AdminStatsApplication(store=s), s)

        if self['developer']:
            didSomething = True
            if self['disable']:
                for app in s.query(webadmin.DeveloperApplication):
                    app.deleteFromStore()
                    break
                else:
                    raise UsageError('Developer controls already disabled.')
            else:
                installOn(webadmin.DeveloperApplication(store=s), s)

        if not didSomething:
            raise UsageError("Specify something or I won't do anything.")
