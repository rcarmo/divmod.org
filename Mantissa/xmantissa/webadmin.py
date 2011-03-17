# -*- test-case-name: xmantissa.test.test_admin -*-

import random, string

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.python.util import sibpath
from twisted.python.filepath import FilePath
from twisted.python import log
from twisted.application.service import IService, Service
from twisted.conch import manhole
from twisted.cred.portal import IRealm

from nevow.page import renderer
from nevow.athena import expose

from epsilon import extime

from axiom.attributes import (integer, boolean, timestamp, bytes, reference,
    inmemory, AND)
from axiom.item import Item, declareLegacyItem
from axiom import userbase
from axiom.dependency import installOn, dependsOn
from axiom.upgrade import registerUpgrader

from xmantissa.liveform import LiveForm, Parameter, ChoiceParameter
from xmantissa.liveform import TEXT_INPUT ,CHECKBOX_INPUT
from xmantissa import webtheme, liveform, webnav, offering, signup
from xmantissa.port import TCPPort, SSLPort
from xmantissa.product import ProductConfiguration, Product, Installation
from xmantissa.suspension import suspendJustTabProviders, unsuspendTabProviders
from xmantissa.tdb import AttributeColumn
from xmantissa.scrolltable import ScrollingFragment
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite, PrefixURLMixin
from xmantissa.terminal import TerminalManhole
from xmantissa.ixmantissa import (
    INavigableElement, INavigableFragment, ISessionlessSiteRootPlugin,
    IProtocolFactoryFactory)

from nevow import rend, athena, static, tags as T


class DeveloperSite(Item, PrefixURLMixin):
    """
    Provides static content sessionlessly for the developer application.
    """
    implements(ISessionlessSiteRootPlugin)

    typeName = 'developer_site'
    schemaVersion = 1

    sessionless = True

    prefixURL = 'static/webadmin'

    # Counts of each kind of user.  These are not maintained, they should be
    # upgraded away at some point.  -exarkun
    developers = integer(default=0)
    administrators = integer(default=0)

    def createResource(self):
        return static.File(sibpath(__file__, 'static'))



class AdminStatsApplication(Item):
    """
    Obsolete.  Only present for schema compatibility.  Do not use.
    """
    powerupInterfaces = (INavigableElement,)
    implements(INavigableElement)

    schemaVersion = 2
    typeName = 'administrator_application'

    updateInterval = integer(default=5)
    privateApplication = dependsOn(PrivateApplication)

    def getTabs(self):
        return []

declareLegacyItem(AdminStatsApplication, 1,
                  dict(updateInterval=integer(default=5)))

def _adminStatsApplication1to2(old):
    new = old.upgradeVersion(AdminStatsApplication.typeName, 1, 2,
                             updateInterval=old.updateInterval,
                             privateApplication=old.store.findOrCreate(PrivateApplication))
    return new
registerUpgrader(_adminStatsApplication1to2, AdminStatsApplication.typeName, 1, 2)

class LocalUserBrowser(Item):
    """
    XXX I am an unfortunate necessity.

    This class shouldn't exist, and in fact, will be destroyed at the first
    possible moment.  It's stateless, existing only to serve as a web lookup
    hook for the UserInteractionFragment view class.
    """

    implements(INavigableElement)

    typeName = 'local_user_browser'
    schemaVersion = 2

    privateApplication = dependsOn(PrivateApplication)
    powerupInterfaces = (INavigableElement,)

    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('Local Users', self.storeID, 0.1)],
                           authoritative=False)]

declareLegacyItem(LocalUserBrowser.typeName, 1,
                  dict(garbage=integer(default=0)))

def _localUserBrowser1to2(old):
    new = old.upgradeVersion(LocalUserBrowser.typeName, 1, 2,
                             privateApplication=old.store.findOrCreate(PrivateApplication))
    return new
registerUpgrader(_localUserBrowser1to2, LocalUserBrowser.typeName, 1, 2)

class UserInteractionFragment(webtheme.ThemedElement):
    """
    Contains two other user-interface elements which allow existing users to be
    browsed and new users to be created, respectively.
    """
    fragmentName = 'admin-user-interaction'

    def __init__(self, userBrowser):
        """
        @param userBrowser: a LocalUserBrowser instance
        """
        super(UserInteractionFragment, self).__init__()
        self.browser = userBrowser


    def userBrowser(self, request, tag):
        """
        Render a TDB of local users.
        """
        f = LocalUserBrowserFragment(self.browser)
        f.docFactory = webtheme.getLoader(f.fragmentName)
        f.setFragmentParent(self)
        return f
    renderer(userBrowser)


    def userCreate(self, request, tag):
        """
        Render a form for creating new users.
        """
        userCreator = liveform.LiveForm(
            self.createUser,
            [liveform.Parameter(
                    "localpart",
                    liveform.TEXT_INPUT,
                    unicode,
                    "localpart"),
             liveform.Parameter(
                    "domain",
                    liveform.TEXT_INPUT,
                    unicode,
                    "domain"),
             liveform.Parameter(
                    "password",
                    liveform.PASSWORD_INPUT,
                    unicode,
                    "password")])
        userCreator.setFragmentParent(self)
        return userCreator
    renderer(userCreate)


    def createUser(self, localpart, domain, password=None):
        """
        Create a new, blank user account with the given name and domain and, if
        specified, with the given password.

        @type localpart: C{unicode}
        @param localpart: The local portion of the username.  ie, the
        C{'alice'} in C{'alice@example.com'}.

        @type domain: C{unicode}
        @param domain: The domain portion of the username.  ie, the
        C{'example.com'} in C{'alice@example.com'}.

        @type password: C{unicode} or C{None}
        @param password: The password to associate with the new account.  If
        C{None}, generate a new password automatically.
        """
        loginSystem = self.browser.store.parent.findUnique(userbase.LoginSystem)
        if password is None:
            password = u''.join([random.choice(string.ascii_letters + string.digits) for i in xrange(8)])
        loginSystem.addAccount(localpart, domain, password)

registerAdapter(UserInteractionFragment, LocalUserBrowser, INavigableFragment)



class LocalUserBrowserFragment(ScrollingFragment):
    jsClass = u'Mantissa.Admin.LocalUserBrowser'

    def __init__(self, userBrowser):
        ScrollingFragment.__init__(self, userBrowser.store.parent,
                                   userbase.LoginMethod,
                                   userbase.LoginMethod.domain != None,
                                   (userbase.LoginMethod.localpart,
                                    userbase.LoginMethod.domain,
                                    userbase.LoginMethod.verified),
                                   defaultSortColumn=userbase.LoginMethod.domain,
                                   defaultSortAscending=True)

    def linkToItem(self, item):
        # no IWebTranslator.  better ideas?
        # will (localpart, domain, protocol) always be unique?
        return unicode(item.storeID)

    def itemFromLink(self, link):
        return self.store.getItemByID(int(link))

    def doAction(self, loginMethod, actionClass):
        """
        Show the form for the requested action.
        """
        loginAccount = loginMethod.account
        return actionClass(
            self,
            loginMethod.localpart + u'@' + loginMethod.domain,
            loginAccount)

    def action_installOn(self, loginMethod):
        return self.doAction(loginMethod, EndowFragment)

    def action_uninstallFrom(self, loginMethod):
        return self.doAction(loginMethod, DepriveFragment)

    def action_suspend(self, loginMethod):
        return self.doAction(loginMethod, SuspendFragment)

    def action_unsuspend(self, loginMethod):
        return self.doAction(loginMethod, UnsuspendFragment)

class EndowDepriveFragment(webtheme.ThemedElement):
    fragmentName = 'user-detail'

    def __init__(self, fragmentParent, username, loginAccount, which):
        super(EndowDepriveFragment, self).__init__(fragmentParent)
        self.account = loginAccount
        self.which = which
        self.username = username

    def _endow(self, **kw):
        subs = self.account.avatars.open()
        def endowall():
            for product in kw.values():
                if product is not None:
                    getattr(product, self.which)(subs)
        subs.transact(endowall)

    def productForm(self, request, tag):
        """
        Render a L{liveform.LiveForm} -- the main purpose of this fragment --
        which will allow the administrator to endow or deprive existing users
        using Products.
        """

        def makeRemover(i):
            def remover(s3lected):
                if s3lected:
                    return self.products[i]
                return None
            return remover

        f = liveform.LiveForm(
            self._endow,
            [liveform.Parameter(
                    'products' + str(i),
                    liveform.FORM_INPUT,
                    liveform.LiveForm(
                        makeRemover(i),
                        [liveform.Parameter(
                                's3lected',
                                liveform.RADIO_INPUT,
                                bool,
                                repr(p),
                                )],
                        '',
                        ),
                    )
             for (i, p)
             in enumerate(self.products)],
            self.which.capitalize() + u' ' + self.username)
        f.setFragmentParent(self)
        return f
    renderer(productForm)
class EndowFragment(EndowDepriveFragment):
    def __init__(self, fragmentParent, username, loginAccount):
        EndowDepriveFragment.__init__(self, fragmentParent,
                                      username, loginAccount,
                                      'installProductOn')
        allProducts = list(self.account.store.query(Product))
        self.products = [p for p in allProducts
                    if not self.account.avatars.open().findUnique(Installation,
                                                              Installation.types
                                                              == p.types,
                                                              None)]
        self.desc = "Install on"

class DepriveFragment(EndowDepriveFragment):
    def __init__(self, fragmentParent, username, loginAccount):
        EndowDepriveFragment.__init__(self, fragmentParent,
                                      username, loginAccount,
                                      'removeProductFrom')
        allProducts = list(self.account.store.query(Product))
        self.products = [p for p in allProducts
                    if self.account.avatars.open().findUnique(Installation,
                                                              Installation.types
                                                              == p.types,
                                                              None)]
        self.desc = "Remove from"

class SuspendFragment(EndowDepriveFragment):
    def __init__(self, fragmentParent, username, loginAccount):
        self.func = suspendJustTabProviders
        EndowDepriveFragment.__init__(self, fragmentParent,
                                      username, loginAccount,
                                      'suspend')
        allProducts = list(self.account.store.query(Product))
        self.products = [p for p in allProducts
                    if self.account.avatars.open().findUnique(Installation,
                                           AND(Installation.types == p.types,
                                               Installation.suspended == False,
                                               ), [])]
        self.desc = "Suspend"

    def _endow(self, **kw):
        subs = self.account.avatars.open()
        def suspend():
            for product in kw.values():
                if product is not None:
                    i = subs.findUnique(Installation,
                                        Installation.types == product.types,
                                        None)
                    self.func(i)
        subs.transact(suspend)

class UnsuspendFragment(SuspendFragment):
    def __init__(self, fragmentParent, username, loginAccount):
        self.func = unsuspendTabProviders
        EndowDepriveFragment.__init__(self, fragmentParent,
                                      username, loginAccount,
                                      'unsuspend')
        allProducts = list(self.account.store.query(Product))
        self.products = [p for p in allProducts
                    if self.account.avatars.open().findUnique(Installation,
                                           AND(Installation.types == p.types,
                                               Installation.suspended == True),
                                                 None)]
        self.desc = "Unsuspend"



class DeveloperApplication(Item):
    """
    """
    implements(INavigableElement)

    schemaVersion = 2
    typeName = 'developer_application'

    privateApplication = dependsOn(PrivateApplication)
    statementCount = integer(default=0)
    powerupInterfaces = (INavigableElement,)

    def deletedFromStore(self, *a, **kw):
        return super(DeveloperApplication, self).deletedFromStore(*a, **kw)

    # INavigableElement
    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('REPL', self.storeID, 0.0)],
                           authoritative=False)]

declareLegacyItem(DeveloperApplication.typeName, 1,
                  dict(statementCount=integer(default=0)))

def _developerApplication1to2(old):
    new = old.upgradeVersion(DeveloperApplication.typeName, 1, 2,
                             statementCount=old.statementCount,
                             privateApplication=old.store.findOrCreate(PrivateApplication))
    return new
registerUpgrader(_developerApplication1to2, DeveloperApplication.typeName, 1, 2)

class REPL(athena.LiveFragment):
    """
    Provides an interactive Read-Eval-Print loop. On a web page (duh).
    """
    implements(INavigableFragment)

    jsClass = u'Mantissa.InterpreterWidget'

    fragmentName = 'admin-python-repl'
    live = 'athena'

    def __init__(self, *a, **kw):
        rend.Fragment.__init__(self, *a, **kw)
        self.namespace = {'s': self.original.store, 'getStore': self.getStore}
        self.interpreter = manhole.ManholeInterpreter(
            self,
            self.namespace)

    def getStore(self, name, domain):
        """Convenience method for the REPL. I got tired of typing this string every time I logged in."""
        return IRealm(self.original.store.parent).accountByAddress(name, domain).avatars.open()

    def head(self):
        return ()


    def addOutput(self, output, async=False):
        self.callRemote('addOutputLine', unicode(output, 'ascii'))


    def evaluateInputLine(self, inputLine):
        return self.interpreter.push(inputLine)
    expose(evaluateInputLine)



registerAdapter(REPL, DeveloperApplication, INavigableFragment)

class Traceback(Item):
    typeName = 'mantissa_traceback'
    schemaVersion = 1

    when = timestamp()
    traceback = bytes()
    collector = reference()

    def __init__(self, store, collector, failure):
        when = extime.Time()
        traceback = failure.getTraceback()
        super(Traceback, self).__init__(
            store=store,
            traceback=traceback,
            when=when,
            collector=collector)

class TracebackCollector(Item, Service):
    implements(IService)

    typeName = 'mantissa_traceback_collector'
    schemaVersion = 1

    tracebackCount = integer(default=0)

    parent = inmemory()
    running = inmemory()
    name = inmemory()
    powerupInterfaces = (IService,)

    def installed(self):
        self.setServiceParent(self.store)

    def startService(self):
        log.addObserver(self.emit)

    def stopService(self):
        log.removeObserver(self.emit)

    def emit(self, event):
        if event.get('isError') and event.get('failure') is not None:
            f = event['failure']
            def txn():
                self.tracebackCount += 1
                Traceback(store=self.store, collector=self, failure=f)
            self.store.transact(txn)

    def getTracebacks(self):
        """
        Return an iterable of Tracebacks that have been collected.
        """
        return self.store.query(Traceback,
                                Traceback.collector == self)


class TracebackViewer(Item):
    implements(INavigableElement)

    typeName = 'mantissa_tb_viewer'
    schemaVersion = 2

    allowDeletion = boolean(default=False)

    privateApplication = dependsOn(PrivateApplication)
    powerupInterfaces = (INavigableElement,)

    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('Errors', self.storeID, 0.3)],
                           authoritative=False)]

    def _getCollector(self):
        def ifCreate(coll):
            installOn(coll, self.store.parent)
        return self.store.parent.findOrCreate(TracebackCollector, ifCreate)

    # this needs to be moved somewhere else, topPanelContent is no more
    #def topPanelContent(self):
    #    # XXX There should really be a juice protocol for this.
    #    return '%d errors logged' % (self._getCollector().tracebackCount,)

declareLegacyItem(TracebackViewer, 1,
                  dict(allowDeletion=boolean(default=False)))

def _tracebackViewer1to2(old):
    return old.upgradeVersion(TracebackViewer.typeName, 1, 2,
                              allowDeletion=old.allowDeletion,
                              privateApplication=old.store.findOrCreate(PrivateApplication))
registerUpgrader(_tracebackViewer1to2, TracebackViewer.typeName, 1, 2)


class TracebackViewerFragment(rend.Fragment):
    implements(INavigableFragment)

    live = False
    fragmentName = 'traceback-viewer'

    def head(self):
        return ()

    def render_tracebacks(self, ctx, data):
        for tb in self.original._getCollector().getTracebacks():
            yield T.div[T.code[T.pre[tb.traceback]]]

registerAdapter(TracebackViewerFragment, TracebackViewer, INavigableFragment)



class PortConfiguration(Item):
    """
    Marker powerup which allows those on whom it is installed to modify the
    configuration of listening ports in this server.
    """
    implements(INavigableElement)

    powerupInterfaces = (INavigableElement,)

    # Only present because Axiom requires at least one attribute on an Item.
    garbage = integer(default=12345678653)

    def getTabs(self):
        """
        Add this object to the tab navigation so it can display configuration
        information and allow configuration to be modified.
        """
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('Ports', self.storeID, 0.4)],
                           authoritative=False)]


    def createPort(self, portNumber, ssl, certPath, factory, interface=u''):
        """
        Create a new listening port.

        @type portNumber: C{int}
        @param portNumber: Port number on which to listen.

        @type ssl: C{bool}
        @param ssl: Indicates whether this should be an SSL port or not.

        @type certPath: C{str}
        @param ssl: If C{ssl} is true, a path to a certificate file somewhere
        within the site store's files directory.  Ignored otherwise.

        @param factory: L{Item} which provides L{IProtocolFactoryFactory} which
        will be used to get a protocol factory to associate with this port.

        @return: C{None}
        """
        store = self.store.parent
        if ssl:
            port = SSLPort(store=store, portNumber=portNumber,
                           certificatePath=FilePath(certPath), factory=factory,
                           interface=interface)
        else:
            port = TCPPort(store=store, portNumber=portNumber, factory=factory,
                           interface=interface)
        installOn(port, store)



class FactoryColumn(AttributeColumn):
    """
    Display the name of the class of items referred to by a reference
    attribute.
    """
    def extractValue(self, model, item):
        """
        Get the class name of the factory referenced by a port.

        @param model: Either a TabularDataModel or a ScrollableView, depending
        on what this column is part of.

        @param item: A port item instance (as defined by L{xmantissa.port}).

        @rtype: C{unicode}
        @return: The name of the class of the item to which this column's
        attribute refers.
        """
        factory = super(FactoryColumn, self).extractValue(model, item)
        return factory.__class__.__name__.decode('ascii')



class CertificateColumn(AttributeColumn):
    """
    Display a path attribute as a unicode string.
    """
    def extractValue(self, model, item):
        """
        Get the path referenced by this column's attribute.

        @param model: Either a TabularDataModel or a ScrollableView, depending
        on what this column is part of.

        @param item: A port item instance (as defined by L{xmantissa.port}).

        @rtype: C{unicode}
        """
        certPath = super(CertificateColumn, self).extractValue(model, item)
        return certPath.path.decode('utf-8', 'replace')



class PortScrollingFragment(ScrollingFragment):
    """
    A scrolling fragment for TCPPorts and SSLPorts which knows how to link to
    them and how to delete them.

    @ivar userStore: The store of the user viewing these ports.

    @ivar siteStore: The site store, where TCPPorts and SSLPorts are loaded
    from.
    """
    jsClass = u'Mantissa.Admin.PortBrowser'

    def __init__(self, userStore, portType, columns):
        super(PortScrollingFragment, self).__init__(
            userStore.parent,
            portType,
            None,
            columns)
        self.userStore = userStore
        self.siteStore = userStore.parent
        self.webTranslator = self.userStore.findUnique(PrivateApplication)


    def itemFromLink(self, link):
        """
        @type link: C{unicode}
        @param link: A webID to translate into an item.

        @rtype: L{Item}
        @return: The item to which the given link referred.
        """
        return self.siteStore.getItemByID(self.webTranslator.linkFrom(link))


    def action_delete(self, port):
        """
        Delete the given port.
        """
        port.deleteFromStore()



class PortConfigurationFragment(webtheme.ThemedElement):
    """
    Provide the view for L{PortConfiguration}.

    Specifically, three renderers are offered: the first two, L{tcpPorts} and
    L{sslPorts}, add a L{PortScrollingFragment} to their tag as a child; the
    last, L{createPortForm} adds a L{LiveForm} for adding new ports to its tag
    as a child.

    @ivar portConf: The L{PortConfiguration} item.
    @ivar store: The user store.
    """
    implements(INavigableFragment)

    fragmentName = 'port-configuration'


    def __init__(self, portConf):
        super(PortConfigurationFragment, self).__init__()
        self.portConf = portConf
        self.store = portConf.store


    def head(self):
        return ()


    def tcpPorts(self, req, tag):
        """
        Create and return a L{PortScrollingFragment} for the L{TCPPort} items
        in site store.
        """
        f = PortScrollingFragment(
            self.store,
            TCPPort,
            (TCPPort.portNumber,
             TCPPort.interface,
             FactoryColumn(TCPPort.factory)))
        f.setFragmentParent(self)
        f.docFactory = webtheme.getLoader(f.fragmentName)
        return tag[f]
    renderer(tcpPorts)


    def sslPorts(self, req, tag):
        """
        Create and return a L{PortScrollingFragment} for the L{SSLPort} items
        in the site store.
        """
        f = PortScrollingFragment(
            self.store,
            SSLPort,
            (SSLPort.portNumber,
             SSLPort.interface,
             CertificateColumn(SSLPort.certificatePath),
             FactoryColumn(SSLPort.factory)))
        f.setFragmentParent(self)
        f.docFactory = webtheme.getLoader(f.fragmentName)
        return tag[f]
    renderer(sslPorts)


    def createPortForm(self, req, tag):
        """
        Create and return a L{LiveForm} for adding a new L{TCPPort} or
        L{SSLPort} to the site store.
        """
        def port(s):
            n = int(s)
            if n < 0 or n > 65535:
                raise ValueError(s)
            return n

        factories = []
        for f in self.store.parent.powerupsFor(IProtocolFactoryFactory):
            factories.append((f.__class__.__name__.decode('ascii'),
                              f,
                              False))

        f = LiveForm(
            self.portConf.createPort,
            [Parameter('portNumber', TEXT_INPUT, port, 'Port Number',
                       'Integer 0 <= n <= 65535 giving the TCP port to bind.'),

             Parameter('interface', TEXT_INPUT, unicode, 'Interface',
                       'Hostname to bind to, or blank for all interfaces.'),

             Parameter('ssl', CHECKBOX_INPUT, bool, 'SSL',
                       'Select to indicate port should use SSL.'),

             # Text area?  File upload?  What?
             Parameter('certPath', TEXT_INPUT, unicode, 'Certificate Path',
                       'Path to a certificate file on the server, if SSL is to be used.'),

             ChoiceParameter('factory', factories, 'Protocol Factory',
                             'Which pre-existing protocol factory to associate with this port.')])
        f.setFragmentParent(self)
        # f.docFactory = webtheme.getLoader(f.fragmentName)
        return tag[f]
    renderer(createPortForm)

registerAdapter(PortConfigurationFragment, PortConfiguration, INavigableFragment)



class AdministrativeBenefactor(Item):
    typeName = 'mantissa_administrative_benefactor'
    schemaVersion = 1

    endowed = integer(default=0)
    powerupNames = ["xmantissa.webadmin.AdminStatsApplication",
                    "xmantissa.webadmin.DeveloperApplication",
                    "xmantissa.signup.SignupConfiguration",
                    "xmantissa.webadmin.TracebackViewer",
                    "xmantissa.webadmin.BatchManholePowerup",
                    "xmantissa.webadmin.LocalUserBrowser"]


def endowAdminPowerups(userStore):
    powerups = [
            # Install a web site for the individual user as well.
            # This is necessary because although we have a top-level
            # website for everybody, not all users should be allowed
            # to log in through the web (like UNIX's "system users",
            # "nobody", "database", etc.)  Note, however, that there
            # is no port number, because the WebSite's job in this
            # case is to be a web *resource*, not a web *server*.
            WebSite,

            # Now we install the 'private application' plugin for
            # 'admin', on admin's private store, This provides the URL
            # "/private", but only when 'admin' is logged in.  It is a
            # hook to hang other applications on.  (XXX Rename:
            # PrivateApplication should probably be called
            # PrivateAppShell)
            PrivateApplication,

            # This is a plugin *for* the PrivateApplication; it publishes
            # objects via the tab-based navigation (a Python interactive
            # interpreter).
            DeveloperApplication,

            #ProductConfiguration lets admins collect powerups into
            #Products users can sign up for.

            ProductConfiguration,

            # And another one: SignupConfiguration allows the
            # administrator to add signup forms which grant various
            # kinds of account.
            signup.SignupConfiguration,

            # This one lets the administrator view unhandled
            # exceptions which occur in the server.
            TracebackViewer,

            # Allow the administrator to set the ports associated with
            # different network services.
            PortConfiguration,

            # And this one gives the administrator a page listing all
            # users which exist in this site's credentials database.
            LocalUserBrowser,

            # Grant Python REPL access to the server.
            TerminalManhole,
            ]
    for powerup in powerups:
        installOn(powerup(store=userStore), userStore)
    # This is another PrivateApplication plugin.  It allows
    # the administrator to configure the services offered
    # here.
    oc = offering.OfferingConfiguration(store=userStore)
    installOn(oc, userStore)
