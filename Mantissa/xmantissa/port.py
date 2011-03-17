# -*- test-case-name: xmantissa.test.test_port -*-

"""
Network port features for Mantissa services.

Provided herein are L{IService} L{Item} classes which can be used to take care
of most of the work required to run a network server within a Mantissa server.

Framework code should define an L{Item} subclass which implements
L{xmantissa.ixmantissa.IProtocolFactoryFactory} as desired.  No direct
interaction with the reactor nor specification of port or other network
configuration is necessary in that subclass.  Port types from this module can
be directly instantiated or configuration can be left up to another tool which
operates on arbitrary ports and L{IProtocolFactoryFactory} powerups (for
example, the administrative powerup L{xmantissa.webadmin.PortConfiguration}).

For example, a finger service might be defined in this way::

    from fingerproject import FingerFactory

    from axiom.item import Item
    from axiom.attributes import integer

    from xmantissa.ixmantissa import IProtocolFactoryFactory

    class Finger(Item):
        '''
        A finger (RFC 1288) server.
        '''
        implements(IProtocolFactoryFactory)
        powerupInterfaces = (IProtocolFactoryFactory,)

        requestCount = integer(doc='''
        The number of finger requests which have been responded to, ever.
        ''')

        def getFactory(self):
            return FingerFactory(self)

All concerns related to binding ports can be disregarded.  Once this item has
been added to a site store, an administrator will have access to it and may
configure it to listen on one or more ports.
"""

from zope.interface import implements

try:
    from OpenSSL import SSL
except ImportError:
    SSL = None

from twisted.application.service import IService, IServiceCollection
from twisted.application.strports import parse
from twisted.internet.ssl import PrivateCertificate, CertificateOptions
from twisted.python.reflect import qual
from twisted.python.usage import Options
from twisted.python.filepath import FilePath

from axiom.item import Item, declareLegacyItem, normalize
from axiom.attributes import inmemory, integer, reference, path, text
from axiom.upgrade import registerAttributeCopyingUpgrader
from axiom.dependency import installOn
from axiom.scripts.axiomatic import AxiomaticCommand, AxiomaticSubCommand

from xmantissa.ixmantissa import IProtocolFactoryFactory



class PortMixin:
    """
    Mixin implementing most of L{IService} as would be appropriate for an Axiom
    L{Item} subclass in order to manage the lifetime of an
    L{twisted.internet.interfaces.IListeningPort}.
    """
    implements(IService)

    powerupInterfaces = (IService,)

    # Required by IService but unused by this code.
    name = None

    def activate(self):
        self.parent = None
        self._listen = None
        self.listeningPort = None


    def installed(self):
        """
        Callback invoked after this item has been installed on a store.

        This is used to set the service parent to the store's service object.
        """
        self.setServiceParent(self.store)


    def deleted(self):
        """
        Callback invoked after a transaction in which this item has been
        deleted is committed.

        This is used to remove this item from its service parent, if it has
        one.
        """
        if self.parent is not None:
            self.disownServiceParent()


    # IService
    def setServiceParent(self, parent):
        IServiceCollection(parent).addService(self)
        self.parent = parent


    def disownServiceParent(self):
        IServiceCollection(self.parent).removeService(self)
        self.parent = None


    def privilegedStartService(self):
        if self.portNumber < 1024:
            self.listeningPort = self.listen()


    def startService(self):
        if self.listeningPort is None:
            self.listeningPort = self.listen()


    def stopService(self):
        d = self.listeningPort.stopListening()
        self.listeningPort = None
        return d



class TCPPort(PortMixin, Item):
    """
    An Axiom Service Item which will bind a TCP port to a protocol factory when
    it is started.
    """
    schemaVersion = 2

    portNumber = integer(doc="""
    The TCP port number on which to listen.
    """)

    interface = text(doc="""
    The hostname to bind to.
    """, default=u'')

    factory = reference(doc="""
    An Item with a C{getFactory} method which returns a Twisted protocol
    factory.
    """, whenDeleted=reference.CASCADE)

    parent = inmemory(doc="""
    A reference to the parent service of this service, whenever there is a
    parent.
    """)

    _listen = inmemory(doc="""
    An optional reference to a callable implementing the same interface as
    L{IReactorTCP.listenTCP}.  If set, this will be used to bind a network
    port.  If not set, the reactor will be imported and its C{listenTCP} method
    will be used.
    """)

    listeningPort = inmemory(doc="""
    A reference to the L{IListeningPort} returned by C{self.listen} which is
    set whenever there there is one listening.
    """)

    def listen(self):
        if self._listen is not None:
            _listen = self._listen
        else:
            from twisted.internet import reactor
            _listen = reactor.listenTCP
        return _listen(self.portNumber, self.factory.getFactory(),
                       interface=self.interface.encode('ascii'))

declareLegacyItem(
    typeName=normalize(qual(TCPPort)),
    schemaVersion=1,
    attributes=dict(
        portNumber=integer(),
        factory=reference(),
        parent=inmemory(),
        _listen=inmemory(),
        listeningPort=inmemory()))

registerAttributeCopyingUpgrader(TCPPort, 1, 2)



class SSLPort(PortMixin, Item):
    """
    An Axiom Service Item which will bind a TCP port to a protocol factory when
    it is started.
    """
    schemaVersion = 2

    portNumber = integer(doc="""
    The TCP port number on which to listen.
    """)

    interface = text(doc="""
    The hostname to bind to.
    """, default=u'')

    certificatePath = path(doc="""
    Name of the file containing the SSL certificate to use for this server.
    """)

    factory = reference(doc="""
    An Item with a C{getFactory} method which returns a Twisted protocol
    factory.
    """, whenDeleted=reference.CASCADE)

    parent = inmemory(doc="""
    A reference to the parent service of this service, whenever there is a
    parent.
    """)

    _listen = inmemory(doc="""
    An optional reference to a callable implementing the same interface as
    L{IReactorTCP.listenTCP}.  If set, this will be used to bind a network
    port.  If not set, the reactor will be imported and its C{listenTCP} method
    will be used.
    """)

    listeningPort = inmemory(doc="""
    A reference to the L{IListeningPort} returned by C{self.listen} which is
    set whenever there there is one listening.
    """)


    def getContextFactory(self):
        if SSL is None:
            raise RuntimeError("No SSL support: you need to install OpenSSL.")
        cert = PrivateCertificate.loadPEM(
            self.certificatePath.open().read())
        certOpts = CertificateOptions(
            cert.privateKey.original,
            cert.original,
            requireCertificate=False,
            method=SSL.SSLv23_METHOD)
        return certOpts


    def listen(self):
        if self._listen is not None:
            _listen = self._listen
        else:
            from twisted.internet import reactor
            _listen = reactor.listenSSL
        return _listen(
            self.portNumber,
            self.factory.getFactory(),
            self.getContextFactory(),
            interface=self.interface.encode('ascii'))

declareLegacyItem(
    typeName=normalize(qual(SSLPort)),
    schemaVersion=1,
    attributes=dict(
        portNumber=integer(),
        certificatePath=path(),
        factory=reference(),
        parent=inmemory(),
        _listen=inmemory(),
        listeningPort=inmemory()))

registerAttributeCopyingUpgrader(SSLPort, 1, 2)


class ListOptions(Options):
    """
    I{axiomatic port} subcommand for displaying the ports which are currently
    set up in a store.
    """
    longdesc = "Show the port/factory bindings in an Axiom store."

    def postOptions(self):
        """
        Display details about the ports which already exist.
        """
        store = self.parent.parent.getStore()
        port = None
        factories = {}
        for portType in [TCPPort, SSLPort]:
            for port in store.query(portType):
                key = port.factory.storeID
                if key not in factories:
                    factories[key] = (port.factory, [])
                factories[key][1].append(port)
        for factory in store.powerupsFor(IProtocolFactoryFactory):
            key = factory.storeID
            if key not in factories:
                factories[key] = (factory, [])
        def key((factory, ports)):
            return factory.storeID
        for factory, ports in sorted(factories.values(), key=key):
            if ports:
                print '%d) %r listening on:' % (factory.storeID, factory)
                for port in ports:
                    if port.interface:
                        interface = "interface " + port.interface
                    else:
                        interface = "any interface"
                    if isinstance(port, TCPPort):
                        print '  %d) TCP, %s, port %d' % (
                            port.storeID, interface, port.portNumber)
                    else:
                        if port.certificatePath is not None:
                            pathPart = 'certificate %s' % (
                                port.certificatePath.path,)
                        else:
                            pathPart = 'NO CERTIFICATE'
                        if port.portNumber is not None:
                            portPart = 'port %d' % (port.portNumber,)
                        else:
                            portPart = 'NO PORT'
                        print '  %d) SSL, %s, %s, %s' % (
                            port.storeID, interface, portPart, pathPart)
            else:
                print '%d) %r is not listening.' % (factory.storeID, factory)
        if not factories:
            print "There are no ports configured."
        raise SystemExit(0)



class DeleteOptions(Options):
    """
    I{axiomatic port} subcommand for removing existing ports.

    @type portIdentifiers: C{list} of C{int}
    @ivar portIdentifiers: The store IDs of the ports to be deleted, built up
        by the I{port-identifier} parameter.
    """
    longdesc = (
        "Delete an existing port binding from a factory.  If a server is "
        "currently running using the database from which the port is deleted, "
        "the factory will *not* stop listening on that port until the server "
        "is restarted.")

    def __init__(self):
        Options.__init__(self)
        self.portIdentifiers = []


    def opt_port_identifier(self, storeID):
        """
        Identify a port for deletion.
        """
        self.portIdentifiers.append(int(storeID))


    def _delete(self, store, portIDs):
        """
        Try to delete the ports with the given store IDs.

        @param store: The Axiom store from which to delete items.

        @param portIDs: A list of Axiom store IDs for TCPPort or SSLPort items.

        @raise L{SystemExit}: If one of the store IDs does not identify a port
            item.
        """
        for portID in portIDs:
            try:
                port = store.getItemByID(portID)
            except KeyError:
                print "%d does not identify an item." % (portID,)
                raise SystemExit(1)
            if isinstance(port, (TCPPort, SSLPort)):
                port.deleteFromStore()
            else:
                print "%d does not identify a port." % (portID,)
                raise SystemExit(1)


    def postOptions(self):
        """
        Delete the ports specified with the port-identifier option.
        """
        if self.portIdentifiers:
            store = self.parent.parent.getStore()
            store.transact(self._delete, store, self.portIdentifiers)
            print "Deleted."
            raise SystemExit(0)
        else:
            self.opt_help()



class CreateOptions(AxiomaticSubCommand):
    """
    I{axiomatic port} subcommand for creating new ports.
    """
    name = "create"
    longdesc = (
        "Create a new port binding for an existing factory.  If a server is "
        "currently running using the database in which the port is created, "
        "the factory will *not* be started on that port until the server is "
        "restarted.")

    _pemFormatError = ('PEM routines', 'PEM_read_bio', 'no start line')
    _noSuchFileError = ('system library', 'fopen', 'No such file or directory')
    _certFileError = ('SSL routines', 'SSL_CTX_use_certificate_file', 'system lib')
    _keyFileError = ('SSL routines', 'SSL_CTX_use_PrivateKey_file', 'system lib')

    optParameters = [
        ("strport", None, None,
         "A Twisted strports description of a port to add."),
        ("factory-identifier", None, None,
         "Identifier for a protocol factory to associate with the new port.")]


    def postOptions(self):
        strport = self['strport']
        factoryIdentifier = self['factory-identifier']
        if strport is None or factoryIdentifier is None:
            self.opt_help()

        store = self.parent.parent.getStore()
        storeID = int(factoryIdentifier)
        try:
            factory = store.getItemByID(storeID)
        except KeyError:
            print "%d does not identify an item." % (storeID,)
            raise SystemExit(1)
        else:
            if not IProtocolFactoryFactory.providedBy(factory):
                print "%d does not identify a factory." % (storeID,)
                raise SystemExit(1)
            else:
                try:
                    kind, args, kwargs = parse(strport, factory)
                except ValueError:
                    print "%r is not a valid port description." % (strport,)
                    raise SystemExit(1)
                except KeyError:
                    print "Unrecognized port type."
                    raise SystemExit(1)
                except SSL.Error, e:
                    if self._pemFormatError in e.args[0]:
                        print 'Certificate file must use PEM format.'
                        raise SystemExit(1)
                    elif self._noSuchFileError in e.args[0]:
                        if self._certFileError in e.args[0]:
                            print "Specified certificate file does not exist."
                            raise SystemExit(1)
                        elif self._keyFileError in e.args[0]:
                            print "Specified private key file does not exist."
                            raise SystemExit(1)
                        else:
                            # Note, no test coverage.
                            raise
                    else:
                        # Note, no test coverage.
                        raise
                else:
                    try:
                        method = getattr(self, 'create_' + kind)
                    except AttributeError:
                        print "Unsupported port type."
                        raise SystemExit(1)
                    else:
                        port = method(store, *args, **kwargs)
                        installOn(port, store)
                        print "Created."
        raise SystemExit(0)


    def create_TCP(self, store, port, factory, backlog, interface):
        """
        Create a new L{TCPPort} with the specified parameters.
        """
        return TCPPort(
            store=store, portNumber=port,
            factory=factory, interface=self.decodeCommandLine(interface))


    def create_SSL(self, store, port, factory, context, backlog, interface):
        """
        Create a new L{SSLPort} with the specified parameters.

        @type context: L{DefaultOpenSSLContextFactory}
        """
        key = context.privateKeyFileName
        cert = context.certificateFileName
        if key != cert:
            print "You must specify the same file for certKey and privateKey."
            raise SystemExit(1)
        elif context.sslmethod != SSL.SSLv23_METHOD:
            print "Only SSLv23_METHOD is supported."
            raise SystemExit(1)
        else:
            port = SSLPort(
                store=store, portNumber=port, factory=factory,
                interface=self.decodeCommandLine(interface))
            targetDir = store.filesdir.child(str(port.storeID))
            targetDir.makedirs()
            targetPath = targetDir.child("cert.pem")
            port.certificatePath = targetPath
            FilePath(key).copyTo(targetPath)
            return port



class PortConfiguration(AxiomaticCommand):
    """
    Axiomatic subcommand plugin for inspecting and modifying port
    configuration.
    """
    subCommands = [("list", None, ListOptions, "Show existing ports and factories."),
                   ("delete", None, DeleteOptions, "Delete existing ports."),
                   ("create", None, CreateOptions, "Create new ports.")]

    name = "port"
    description = "Examine, create, and destroy network servers."
    longdesc = (
        "This command allows for the inspection and modification of the "
        "configuration of network services in an Axiom store.")

    def postOptions(self):
        """
        If nothing else happens, display usage information.
        """
        self.opt_help()



__all__ = ['TCPPort', 'SSLPort', 'PortConfiguration']
