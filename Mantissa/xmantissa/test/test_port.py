# Copyright (c) 2008 Divmod, Inc.
# See LICENSE for details.

"""
Tests for L{xmantissa.port}.
"""

import sys
import os
from StringIO import StringIO

from zope.interface import implements
from zope.interface.verify import verifyObject

from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath
from twisted.application.service import IService, IServiceCollection
from twisted.internet.protocol import ServerFactory
from twisted.internet.defer import Deferred
from twisted.internet.ssl import CertificateOptions

from axiom.iaxiom import IAxiomaticCommand
from axiom.store import Store
from axiom.item import Item
from axiom.attributes import inmemory, integer
from axiom.dependency import installOn
from axiom.scripts.axiomatic import Options as AxiomaticOptions
from axiom.test.util import CommandStub

from xmantissa.ixmantissa import IProtocolFactoryFactory
from xmantissa.port import TCPPort, SSLPort
from xmantissa.port import PortConfiguration


CERTIFICATE_DATA = """
-----BEGIN CERTIFICATE-----
MIICmTCCAgICAQEwDQYJKoZIhvcNAQEEBQAwgZQxCzAJBgNVBAYTAlVTMRQwEgYD
VQQDEwtleGFtcGxlLmNvbTERMA8GA1UEBxMITmV3IFlvcmsxEzARBgNVBAoTCkRp
dm1vZCBMTEMxETAPBgNVBAgTCE5ldyBZb3JrMSIwIAYJKoZIhvcNAQkBFhNzdXBw
b3J0QGV4YW1wbGUuY29tMRAwDgYDVQQLEwdUZXN0aW5nMB4XDTA2MTIzMDE5MDEx
NloXDTA3MTIzMDE5MDExNlowgZQxCzAJBgNVBAYTAlVTMRQwEgYDVQQDEwtleGFt
cGxlLmNvbTERMA8GA1UEBxMITmV3IFlvcmsxEzARBgNVBAoTCkRpdm1vZCBMTEMx
ETAPBgNVBAgTCE5ldyBZb3JrMSIwIAYJKoZIhvcNAQkBFhNzdXBwb3J0QGV4YW1w
bGUuY29tMRAwDgYDVQQLEwdUZXN0aW5nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCB
iQKBgQCrmNNyXLHAETcDH8Uxhmbo8IhFFMx1C4i7oTHTKsmD84E3YFj/RdByrWrG
TL4XskALpfmw1+LxQmMO8n4sIsN3QmjkAWhFhMEquKv6NNN+sRo6vF+ytEasuYn/
7gY/iT7LYqUmKWckBsPYzT9elyOXi6miI0tFdeyfXRSxOslKewIDAQABMA0GCSqG
SIb3DQEBBAUAA4GBABotNizqPoGWIG5BMsl8lxseqiw/8AwvoiQNpYTrC8W+Umsg
oZEaMuVkf/NDJEa3TXdYcAzkFwGN9Cn/WCgHEkLxIZ66aHV0bfcE7YJjHRDrrLiY
chPndOGGrD3iTuWaGnauUcsjJ+RsxqHMBu6NRQYgkoYNsOr0UA1ek7O1vjMy
-----END CERTIFICATE-----
"""

PRIVATEKEY_DATA = """
-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQCrmNNyXLHAETcDH8Uxhmbo8IhFFMx1C4i7oTHTKsmD84E3YFj/
RdByrWrGTL4XskALpfmw1+LxQmMO8n4sIsN3QmjkAWhFhMEquKv6NNN+sRo6vF+y
tEasuYn/7gY/iT7LYqUmKWckBsPYzT9elyOXi6miI0tFdeyfXRSxOslKewIDAQAB
AoGAHd9YCBOs+gPFMO0J9iowpiKhhm0tfr7ISemw89MCC8+LUimatK3hsOURrn3T
peppDd4SDsA2iMuG1SZP4r0Wi9ZncZ+uj6KfVHg6rJZRDW2cPsGNyBw2HO8pFxnh
NsfxioutzCqJ9A0KwqSNQsBpOAlRWzP13+/W5wYAGK+yrLECQQDYgOhVR+1KOhty
CI0NVITNFL5IOZ254Eu46qbEGwPNJvkzdp+Wx5gsfCip9aiZgw3LMEeGXu9P1C4N
AqDM4uozAkEAyua0F0nCRLzjLAAw4odC+vA6jnq6K4M7QT6cQVwmrxgOj6jGEOGu
eaoWbXi2bKcxOGBNDZW0PVKmpq4hZblmmQJBALwFP0AIxg+HZRxkRrMD6oz77cBl
oQ+ytbAywH9ggq2gohzKcRAN6J8BeIMZn8EpqkoCdKtCOQyX1SJhXOpySjcCQDds
mZka7tQz/KISU0gtxqAhav1sjNpB+Lez0J8R+wctPR0E70XBQBW/3mx84uf/K7TI
qYOidx+hKiCxxDGzWVECQHNVutQ1ABjmv6EDJTo28QQsm5hNbfS+tVY3bSihNjLM
Y+O7ib90LsqfQ8r0GUphQVi4EA4QMJqaF7ZxKms79qA=
-----END RSA PRIVATE KEY-----
"""



class DummyPort(object):
    """
    Stub class used to track what reactor listen calls have been made and what
    created ports have been stopped.
    """
    stopping = None

    def __init__(self, portNumber, factory, contextFactory=None, interface=''):
        self.portNumber = portNumber
        self.factory = factory
        self.contextFactory = contextFactory
        self.interface = interface


    def stopListening(self):
        assert self.stopping is None
        self.stopping = Deferred()
        return self.stopping



class DummyFactory(Item):
    """
    Helper class used as a stand-in for a real protocol factory by the unit
    tests.
    """
    implements(IProtocolFactoryFactory)

    dummyAttribute = integer(doc="""
    Meaningless attribute which serves only to make this a valid Item subclass.
    """)

    realFactory = inmemory(doc="""
    A reference to the protocol factory which L{getFactory} will return.
    """)

    def getFactory(self):
        return self.realFactory



class PortTestsMixin:
    """
    Test method-defining mixin class for port types with C{portNumber} and
    C{factory} attributes.

    Included are tests for various persistence-related behaviors as well as the
    L{IService} implementation which all ports should have.

    @ivar portType: The L{Item} subclass which will be tested.

    @ivar lowPortNumber: A port number which requires privileges to bind on
    POSIX.  Used to test L{privilegedStartService}.

    @ivar highPortNumber: A port number which does not require privileges to
    bind on POSIX.  Used to test the interaction between
    L{privilegedStartService} and L{startService}.

    @ivar dbdir: The path at which to create the test L{Store}.  This must be
    bound before L{setUp} is run, since that is the only method which examines
    its value.

    @ivar ports: A list of ports which have been bound using L{listen}.
    created in L{setUp}.
    """
    portType = None

    lowPortNumber = 123
    highPortNumber = 1234
    someInterface = u'127.0.0.1'

    def port(self, **kw):
        """
        Create and return a new port instance with the given attribute values.
        """
        return self.portType(**kw)


    def listen(self, *a, **kw):
        """
        Pretend to bind a port.  Used as a stub implementation of a reactor
        listen method.  Subclasses should override and implement to append
        useful information to C{self.ports}.
        """
        raise NotImplementedError()


    def checkPort(self, port, alternatePort=None):
        """
        Assert that the given port has been properly created.

        @type port: L{DummyPort}
        @param port: A port which has been created by the code being tested.

        @type alternatePort: C{int}
        @param alternatePort: If not C{None}, the port number on which C{port}
        should be listening.
        """
        raise NotImplementedError()


    def setUp(self):
        self.filesdir = self.mktemp()
        self.store = Store(filesdir=self.filesdir)
        self.realFactory = ServerFactory()
        self.factory = DummyFactory(store=self.store, realFactory=self.realFactory)
        self.ports = []


    def test_portNumberAttribute(self):
        """
        Test that C{self.portType} remembers the port number it is told to
        listen on.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber)
        self.assertEqual(port.portNumber, self.lowPortNumber)


    def test_interfaceAttribute(self):
        """
        Test that C{self.portType} remembers the interface it is told to listen
        on.
        """
        port = self.port(store=self.store, interface=self.someInterface)
        self.assertEqual(port.interface, self.someInterface)


    def test_factoryAttribute(self):
        """
        Test that C{self.portType} remembers the factory it is given to associate
        with its port.
        """
        port = self.port(store=self.store, factory=self.factory)
        self.assertIdentical(port.factory, self.factory)


    def test_service(self):
        """
        Test that C{self.portType} becomes a service on the store it is installed on.
        """
        port = self.port(store=self.store)
        installOn(port, self.store)

        self.assertEqual(
            list(self.store.powerupsFor(IService)),
            [port])


    def test_setServiceParent(self):
        """
        Test that the C{self.portType.setServiceParent} method adds the C{self.portType} to
        the Axiom Store Service as a child.
        """
        port = self.port(store=self.store)
        port.setServiceParent(self.store)
        self.failUnlessIn(port, list(IService(self.store)))


    def test_disownServiceParent(self):
        """
        Test that the C{self.portType.disownServiceParent} method removes the
        C{self.portType} from the Axiom Store Service.
        """
        port = self.port(store=self.store)
        port.setServiceParent(self.store)
        port.disownServiceParent()
        self.failIfIn(port, list(IService(self.store)))


    def test_serviceParent(self):
        """
        Test that C{self.portType} is a child of the store service after it is
        installed.
        """
        port = self.port(store=self.store)
        installOn(port, self.store)

        service = IServiceCollection(self.store)
        self.failUnlessIn(port, list(service))


    def _start(self, portNumber, methodName):
        port = self.port(store=self.store, portNumber=portNumber, factory=self.factory)
        port._listen = self.listen
        getattr(port, methodName)()
        return self.ports


    def _privilegedStartService(self, portNumber):
        return self._start(portNumber, 'privilegedStartService')


    def _startService(self, portNumber):
        return self._start(portNumber, 'startService')


    def test_startPrivilegedService(self):
        """
        Test that C{self.portType} binds a low-numbered port with the reactor when it
        is started with privilege.
        """
        ports = self._privilegedStartService(self.lowPortNumber)
        self.assertEqual(len(ports), 1)
        self.checkPort(ports[0])


    def test_dontStartPrivilegedService(self):
        """
        Test that C{self.portType} doesn't bind a high-numbered port with the
        reactor when it is started with privilege.
        """
        ports = self._privilegedStartService(self.highPortNumber)
        self.assertEqual(ports, [])


    def test_startServiceLow(self):
        """
        Test that C{self.portType} binds a low-numbered port with the reactor
        when it is started without privilege.
        """
        ports = self._startService(self.lowPortNumber)
        self.assertEqual(len(ports), 1)
        self.checkPort(ports[0])


    def test_startServiceHigh(self):
        """
        Test that C{self.portType} binds a high-numbered port with the reactor
        when it is started without privilege.
        """
        ports = self._startService(self.highPortNumber)
        self.assertEqual(len(ports), 1)
        self.checkPort(ports[0], self.highPortNumber)


    def test_startServiceNoInterface(self):
        """
        Test that C{self.portType} binds to all interfaces if no interface is
        explicitly specified.
        """
        port = self.port(store=self.store, portNumber=self.highPortNumber, factory=self.factory)
        port._listen = self.listen
        port.startService()
        self.assertEqual(self.ports[0].interface, '')


    def test_startServiceInterface(self):
        """
        Test that C{self.portType} binds to only the specified interface when
        instructed to.
        """
        port = self.port(store=self.store, portNumber=self.highPortNumber, factory=self.factory, interface=self.someInterface)
        port._listen = self.listen
        port.startService()
        self.assertEqual(self.ports[0].interface, self.someInterface)


    def test_startedOnce(self):
        """
        Test that C{self.portType} only binds one network port when
        C{privilegedStartService} and C{startService} are both called.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber, factory=self.factory)
        port._listen = self.listen
        port.privilegedStartService()
        self.assertEqual(len(self.ports), 1)
        self.checkPort(self.ports[0])
        port.startService()
        self.assertEqual(len(self.ports), 1)


    def test_stopService(self):
        """
        Test that C{self.portType} cleans up its listening port when it is stopped.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber, factory=self.factory)
        port._listen = self.listen
        port.startService()
        stopped = port.stopService()
        stopping = self.ports[0].stopping
        self.failIfIdentical(stopping, None)
        self.assertIdentical(stopped, stopping)


    def test_deletedFactory(self):
        """
        Test that the deletion of a C{self.portType}'s factory item results in the
        C{self.portType} being deleted.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber, factory=self.factory)
        self.factory.deleteFromStore()
        self.assertEqual(list(self.store.query(self.portType)), [])


    def test_deletionDisownsParent(self):
        """
        Test that a deleted C{self.portType} no longer shows up in the children list
        of the service which used to be its parent.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber, factory=self.factory)
        port.setServiceParent(self.store)
        port.deleteFromStore()
        service = IServiceCollection(self.store)
        self.failIfIn(port, list(service))



class TCPPortTests(PortTestsMixin, TestCase):
    """
    Tests for L{xmantissa.port.TCPPort}.
    """
    portType = TCPPort


    def checkPort(self, port, alternatePort=None):
        if alternatePort is None:
            alternatePort = self.lowPortNumber
        self.assertEqual(port.portNumber, alternatePort)
        self.assertEqual(port.factory, self.realFactory)


    def listen(self, port, factory, interface=''):
        self.ports.append(DummyPort(port, factory, interface=interface))
        return self.ports[-1]



class SSLPortTests(PortTestsMixin, TestCase):
    """
    Tests for L{xmantissa.port.SSLPort}.
    """
    portType = SSLPort

    def checkPort(self, port, alternatePort=None):
        if alternatePort is None:
            alternatePort = self.lowPortNumber
        self.assertEqual(port.portNumber, alternatePort)
        self.assertEqual(port.factory, self.realFactory)
        self.failUnless(isinstance(port.contextFactory, CertificateOptions))


    def port(self, certificatePath=None, **kw):
        if certificatePath is None:
            certificatePath = self.store.newFilePath('certificate.pem')
            assert not certificatePath.exists()
            certificatePath.setContent(CERTIFICATE_DATA + PRIVATEKEY_DATA)
        return self.portType(certificatePath=certificatePath, **kw)


    def listen(self, port, factory, contextFactory, interface=''):
        self.ports.append(DummyPort(port, factory, contextFactory, interface=interface))
        return self.ports[-1]


    def test_certificatePathAttribute(self):
        """
        Test that L{SSLPort} remembers the certificate filename it is given.
        """
        certificatePath = self.store.newFilePath('foo', 'bar')
        port = self.port(store=self.store, certificatePath=certificatePath)
        self.assertEqual(port.certificatePath, certificatePath)



class PortConfigurationCommandTests(TestCase):
    """
    Tests for the I{axiomatic port} command.
    """
    def setUp(self):
        """
        Override C{sys.stdout} to capture anything written by the port
        subcommand.
        """
        self.oldColumns = os.environ.get('COLUMNS')
        os.environ['COLUMNS'] = '80'
        self.stdout = sys.stdout
        sys.stdout = StringIO()


    def tearDown(self):
        """
        Restore the original value of C{sys.stdout}.
        """
        sys.stdout = self.stdout
        if self.oldColumns is not None:
            os.environ['COLUMNS'] = self.oldColumns

    def _makeConfig(self, store):
        """
        Create a L{PortConfiguration} instance with a properly set C{parent}
        attribute.
        """
        config = PortConfiguration()
        config.parent = CommandStub(store, "port")
        return config


    def assertSuccessStatus(self, options, arguments):
        """
        Parse the given arguments with the given options object and assert that
        L{SystemExit} is raised with an exit code of C{0}.
        """
        self.assertFailStatus(0, options, arguments)


    def assertFailStatus(self, code, options, arguments):
        """
        Parse the given arguments with the given options object and assert that
        L{SystemExit} is raised with the specified exit code.
        """
        exc = self.assertRaises(SystemExit, options.parseOptions, arguments)
        self.assertEqual(exc.args, (code,))


    def test_providesCommandInterface(self):
        """
        L{PortConfiguration} provides L{IAxiomaticCommand}.
        """
        verifyObject(IAxiomaticCommand, PortConfiguration)


    def test_axiomaticSubcommand(self):
        """
        L{PortConfiguration} is available as a subcommand of I{axiomatic}.
        """
        subCommands = AxiomaticOptions().subCommands
        [options] = [cmd[2] for cmd in subCommands if cmd[0] == 'port']
        self.assertIdentical(options, PortConfiguration)


    _portHelpText = (
        # This is a bit unfortunate.  It depends on what Options in Twisted
        # decides to spit out.  Note particularly the seemingly random amount
        # of trailing whitespace included on some lines.  The intent of tests
        # using this isn't really to ensure byte-identical results, but simply
        # to verify that help text is going to be shown to a user.  -exarkun
        "Usage: axiomatic [options] port [options]\n"
        "Options:\n"
        "      --version  \n"
        "      --help     Display this help and exit.\n"
        "\n"
        "This command allows for the inspection and modification of the "
        "configuration of\n"
        "network services in an Axiom store.\n"
        "Commands:\n"
        "    list        Show existing ports and factories.\n"
        "    delete      Delete existing ports.\n"
        "    create      Create new ports.\n"
        "\n")

    def test_implicitPortHelp(self):
        """
        When I{axiomatic port} is invoked with no arguments, usage information
        is written to standard out and the process exits successfully.
        """
        self.assertSuccessStatus(self._makeConfig(None), [])
        self.assertEqual(self._portHelpText, sys.stdout.getvalue())


    def test_explicitPortHelp(self):
        """
        When I{axiomatic port} is invoked with I{--help}, usage information is
        written to standard out.
        """
        self.assertSuccessStatus(self._makeConfig(None), ["--help"])
        self.assertEqual(self._portHelpText, sys.stdout.getvalue())


    _listHelpText = (
        "Usage: axiomatic [options] port [options] list [options]\n"
        "Options:\n"
        "      --version  \n"
        "      --help     Display this help and exit.\n"
        "\n"
        "Show the port/factory bindings in an Axiom store.\n"
        "\n")

    def test_explicitListHelp(self):
        """
        When I{axiomatic port list} is invoked with I{--help}, usage
        information for the C{list} subcommand is written to standard out.
        """
        self.assertSuccessStatus(self._makeConfig(None), ["list", "--help"])
        self.assertEqual(self._listHelpText, sys.stdout.getvalue())


    def test_listEmpty(self):
        """
        When I{axiomatic port list} is invoked, the ports which are currently
        configured in the system are displayed.
        """
        store = Store()
        self.assertSuccessStatus(self._makeConfig(store), ["list"])
        self.assertIn("There are no ports configured.", sys.stdout.getvalue())


    def test_listTCPPort(self):
        """
        When I{axiomatic port list} is invoked for a L{Store} which has a
        L{TCPPort} in it, the details of that port, including its factory, are
        written to stdout.
        """
        store = Store()
        factory = DummyFactory(store=store)
        port = TCPPort(
            store=store, factory=factory, portNumber=1234, interface=u"foo")
        self.assertSuccessStatus(self._makeConfig(store), ["list"])
        self.assertEqual(
            "%d) %r listening on:\n" % (factory.storeID, factory) +
            "  %d) TCP, interface %s, port %d\n" % (
                port.storeID, port.interface, port.portNumber),
            sys.stdout.getvalue())


    def test_listSSLPort(self):
        """
        When I{axiomatic port list} is invoked for a L{Store} which has an
        L{SSLPort} in it, the details of that port, including its factory, are
        written to stdout.
        """
        store = Store(filesdir=self.mktemp())
        factory = DummyFactory(store=store)
        port = SSLPort(
            store=store, factory=factory, portNumber=1234, interface=u"foo",
            certificatePath=store.filesdir.child("bar"))
        self.assertSuccessStatus(self._makeConfig(store), ["list"])
        self.assertEqual(
            "%d) %r listening on:\n" % (factory.storeID, factory) +
            "  %d) SSL, interface %s, port %d, certificate %s\n" % (
                port.storeID, port.interface, port.portNumber,
                port.certificatePath.path),
            sys.stdout.getvalue())


    def test_listAnyInterface(self):
        """
        I{axiomatic port list} displays a special string for a port bound to
        C{INADDR_ANY}.
        """
        store = Store()
        factory = DummyFactory(store=store)
        port = TCPPort(
            store=store, factory=factory, portNumber=1234, interface=u"")
        self.assertSuccessStatus(self._makeConfig(store), ["list"])
        self.assertEqual(
            "%d) %r listening on:\n" % (factory.storeID, factory) +
            "  %d) TCP, any interface, port %d\n" % (port.storeID, port.portNumber),
            sys.stdout.getvalue())


    def test_listSSLPortWithoutAttributes(self):
        """
        If there is an L{SSLPort} with no certificate or no port number (a
        rather invalid configuration), I{axiomatic port list} should show this
        in its output without producing an error.
        """
        store = Store()
        factory = DummyFactory(store=store)
        port = SSLPort(store=store, factory=factory)
        self.assertSuccessStatus(self._makeConfig(store), ["list"])
        self.assertEqual(
            "%d) %r listening on:\n" % (factory.storeID, factory) +
            "  %d) SSL, any interface, NO PORT, NO CERTIFICATE\n" % (
                port.storeID,),
            sys.stdout.getvalue())


    def test_listTwoPorts(self):
        """
        I{axiomatic port list} displays two different ports bound to the same
        factory together beneath that factory.
        """
        store = Store()
        factory = DummyFactory(store=store)
        portOne = TCPPort(
            store=store, factory=factory, portNumber=1234, interface=u"foo")
        portTwo = TCPPort(
            store=store, factory=factory, portNumber=2345, interface=u"bar")
        self.assertSuccessStatus(self._makeConfig(store), ["list"])
        self.assertEqual(
            "%d) %r listening on:\n" % (factory.storeID, factory) +
            "  %d) TCP, interface %s, port %d\n" % (
                portOne.storeID, portOne.interface, portOne.portNumber) +
            "  %d) TCP, interface %s, port %d\n" % (
                portTwo.storeID, portTwo.interface, portTwo.portNumber),
            sys.stdout.getvalue())


    def test_listTwoFactories(self):
        """
        I{axiomatic port list} displays two different factories separately from
        each other.
        """
        store = Store()
        factoryOne = DummyFactory(store=store)
        factoryTwo = DummyFactory(store=store)
        portOne = TCPPort(
            store=store, factory=factoryOne, portNumber=10, interface=u"foo")
        portTwo = TCPPort(
            store=store, factory=factoryTwo, portNumber=20, interface=u"bar")
        self.assertSuccessStatus(self._makeConfig(store), ["list"])
        self.assertEqual(
            "%d) %r listening on:\n" % (factoryOne.storeID, factoryOne) +
            "  %d) TCP, interface %s, port %d\n" % (
                portOne.storeID, portOne.interface, portOne.portNumber) +
            "%d) %r listening on:\n" % (factoryTwo.storeID, factoryTwo) +
            "  %d) TCP, interface %s, port %d\n" % (
                portTwo.storeID, portTwo.interface, portTwo.portNumber),
            sys.stdout.getvalue())


    def test_listUnlisteningFactory(self):
        """
        I{axiomatic port list} displays factories even if they aren't associate
        with any port.
        """
        store = Store()
        factory = DummyFactory(store=store)
        store.powerUp(factory, IProtocolFactoryFactory)
        self.assertSuccessStatus(self._makeConfig(store), ["list"])
        self.assertEqual(
            "%d) %r is not listening.\n" % (factory.storeID, factory),
            sys.stdout.getvalue())


    _deleteHelpText = (
        "Usage: axiomatic [options] port [options] delete [options]\n"
        "Options:\n"
        "      --port-identifier=  Identify a port for deletion.\n"
        "      --version           \n"
        "      --help              Display this help and exit.\n"
        "\n"
        "Delete an existing port binding from a factory. If a server is "
        "currently running\n"
        "using the database from which the port is deleted, the factory "
        "will *not* stop\n"
        "listening on that port until the server is restarted.\n"
        "\n")

    def test_explicitDeleteHelp(self):
        """
        If I{axiomatic port delete} is invoked with I{--help}, usage
        information for the C{delete} subcommand is written to standard out.
        """
        store = Store()
        self.assertSuccessStatus(self._makeConfig(store), ["delete", "--help"])
        self.assertEqual(self._deleteHelpText, sys.stdout.getvalue())


    def test_implicitDeleteHelp(self):
        """
        If I{axiomatic port delete} is invoked with no arguments, usage
        information for the C{delete} subcommand is written to standard out.
        """
        store = Store()
        self.assertSuccessStatus(self._makeConfig(store), ["delete"])
        self.assertEqual(self._deleteHelpText, sys.stdout.getvalue())


    def test_deletePorts(self):
        """
        I{axiomatic port delete} deletes each ports with a C{storeID} which is
        specified.
        """
        store = Store(filesdir=self.mktemp())
        factory = DummyFactory(store=store)
        deleteTCP = TCPPort(
            store=store, factory=factory, portNumber=10, interface=u"foo")
        keepTCP = TCPPort(
            store=store, factory=factory, portNumber=10, interface=u"bar")
        deleteSSL = SSLPort(
            store=store, factory=factory, portNumber=10, interface=u"baz",
            certificatePath=store.filesdir.child("baz"))
        keepSSL = SSLPort(
            store=store, factory=factory, portNumber=10, interface=u"quux",
            certificatePath=store.filesdir.child("quux"))
        self.assertSuccessStatus(
            self._makeConfig(store),
            ["delete",
             "--port-identifier", str(deleteTCP.storeID),
             "--port-identifier", str(deleteSSL.storeID)])
        self.assertEqual("Deleted.\n", sys.stdout.getvalue())
        self.assertEqual(list(store.query(TCPPort)), [keepTCP])
        self.assertEqual(list(store.query(SSLPort)), [keepSSL])


    def test_cannotDeleteOtherStuff(self):
        """
        I{axiomatic port delete} will not delete something which is neither a
        L{TCPPort} nor an L{SSLPort} and does not delete anything if an invalid
        port identifier is present in the command.
        """
        store = Store()
        factory = DummyFactory(store=store)
        tcp = TCPPort(
            store=store, factory=factory, interface=u"foo", portNumber=1234)
        self.assertFailStatus(
            1,
            self._makeConfig(store),
            ["delete",
             "--port-identifier", str(tcp.storeID),
             "--port-identifier", str(factory.storeID)])
        self.assertEqual(
            "%d does not identify a port.\n" % (factory.storeID,),
            sys.stdout.getvalue())
        self.assertEqual(list(store.query(DummyFactory)), [factory])
        self.assertEqual(list(store.query(TCPPort)), [tcp])


    def test_cannotDeleteNonExistent(self):
        """
        I{axiomatic port delete} writes a short error to standard output when a
        port-identifier is specified for which there is no corresponding store
        ID.
        """
        store = Store()
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["delete", "--port-identifier", "12345"])
        self.assertEqual(
            "12345 does not identify an item.\n",
            sys.stdout.getvalue())


    _createHelpText = (
        "Usage: axiomatic [options] port [options] create [options]\n"
        "Options:\n"
        "      --strport=             A Twisted strports description of a "
        "port to add.\n"
        "      --factory-identifier=  Identifier for a protocol factory to "
        "associate with\n"
        "                             the new port.\n"
        "      --version              \n"
        "      --help                 Display this help and exit.\n"
        "\n"
        "Create a new port binding for an existing factory. If a server is "
        "currently\n"
        "running using the database in which the port is created, the "
        "factory will *not*\n"
        "be started on that port until the server is restarted.\n"
        "\n")

    def test_createImplicitHelp(self):
        """
        If I{axiomatic port create} is invoked with no arguments, usage
        information for the C{create} subcommand is written to standard out.
        """
        self.assertSuccessStatus(self._makeConfig(None), ["create"])
        self.assertEqual(self._createHelpText, sys.stdout.getvalue())


    def test_createExplicitHelp(self):
        """
        If I{axiomatic port create} is invoked with C{--help} as an argument,
        usage information for the C{add} subcommand is written to standard out.
        """
        self.assertSuccessStatus(self._makeConfig(None), ["create", "--help"])
        self.assertEqual(self._createHelpText, sys.stdout.getvalue())


    def test_createInvalidPortDescription(self):
        """
        If an invalid string is given for the C{strport} option of I{axiomatic
        port create}, a short error is written to standard output.
        """
        store = Store()
        factory = DummyFactory(store=store)
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create", "--strport", "xyz",
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual(
            "'xyz' is not a valid port description.\n", sys.stdout.getvalue())


    def test_createNonExistentFactoryIdentifier(self):
        """
        If a storeID which is not associated with any item is given for the
        C{factory-identifier} option of I{axiomatic port create}, a short error
        is written to standard output.
        """
        store = Store()
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create", "--strport", "tcp:8080",
             "--factory-identifier", "123"])
        self.assertEqual(
            "123 does not identify an item.\n", sys.stdout.getvalue())


    def test_createNonFactoryIdentifier(self):
        """
        If a storeID which is associated with an item which does not provide
        L{IProtocolFactoryFactory} is given for the C{factory-identifier}
        option of I{axiomatic port create}, a short error is written to
        standard output.
        """
        store = Store()
        storeID = TCPPort(store=store).storeID
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create", "--strport", "tcp:8080",
             "--factory-identifier", str(storeID)])
        self.assertEqual(
            "%d does not identify a factory.\n" % (storeID,),
            sys.stdout.getvalue())


    def test_createTCPPort(self):
        """
        If given a valid strport description of a TCP port and the storeID of
        an extant factory, I{axiomatic port create} creates a new L{TCPPort}
        with the specified configuration and referring to that factory.  The
        port is also powered up on the store for L{IService}.
        """
        store = Store()
        factory = DummyFactory(store=store)
        self.assertSuccessStatus(
            self._makeConfig(store),
            ["create", "--strport", "tcp:8080",
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual("Created.\n", sys.stdout.getvalue())
        [tcp] = list(store.query(TCPPort))
        self.assertEqual(tcp.portNumber, 8080)
        self.assertIdentical(tcp.factory, factory)
        self.assertEqual(list(store.interfacesFor(tcp)), [IService])


    def test_createSSLPortInvalidCertificate(self):
        """
        If given a certificate file which does not contain a PEM-format
        certificate, I{axiomatic port create} writes a short error message to
        standard output.
        """
        pemPath = FilePath(self.mktemp())
        pemPath.setContent("pem goes here")
        store = Store()
        factory = DummyFactory(store=store)
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create", "--strport", "ssl:8443:certKey=" + pemPath.path,
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual(
            "Certificate file must use PEM format.\n",
            sys.stdout.getvalue())
        self.assertEqual(store.query(SSLPort).count(), 0)


    def test_createSSLPortNonExistentCertificateFile(self):
        """
        Specifying a certificate file which does not exist when creating an SSL
        port with I{axiomatic port create} causes a short error message to be
        written to stdout.
        """
        pemPath = FilePath(self.mktemp())
        pemPath.setContent(PRIVATEKEY_DATA)

        store = Store()
        factory = DummyFactory(store=store)
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create",
             "--strport", "ssl:8443:certKey=quux:privateKey=" + pemPath.path,
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual(
            "Specified certificate file does not exist.\n",
            sys.stdout.getvalue())
        self.assertEqual(store.query(SSLPort).count(), 0)


    def test_createSSLPortNonExistentKeyFile(self):
        """
        Specifying a private key file which does not exist when creating an SSL
        port with I{axiomatic port create} causes a short error message to be
        written to stdout.
        """
        pemPath = FilePath(self.mktemp())
        pemPath.setContent(CERTIFICATE_DATA)

        store = Store()
        factory = DummyFactory(store=store)
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create",
             "--strport", "ssl:8443:privateKey=quux:certKey=" + pemPath.path,
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual(
            "Specified private key file does not exist.\n",
            sys.stdout.getvalue())
        self.assertEqual(store.query(SSLPort).count(), 0)


    def test_createSSLPortInconsistentCertificateAndKeyFiles(self):
        """
        If different values are specified for the certificate file and the
        private key file when creating an SSL port with I{axiomatic port
        create}, a short error message is written to standard output.

        This reflects an implementation limitation which may be lifted in the
        future.
        """
        certPath = FilePath(self.mktemp())
        certPath.setContent(CERTIFICATE_DATA)
        keyPath = FilePath(self.mktemp())
        keyPath.setContent(PRIVATEKEY_DATA)

        store = Store()
        factory = DummyFactory(store=store)
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create",
             "--strport", "ssl:8443:privateKey=" + keyPath.path +
             ":certKey=" + certPath.path,
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual(
            "You must specify the same file for certKey and privateKey.\n",
            sys.stdout.getvalue())
        self.assertEqual(store.query(SSLPort).count(), 0)


    def test_createSSLPortWithMethod(self):
        """
        SSL method configuration is unsupported and when I{axiomatic port
        create} is used to create an SSL port, an error is written to standard
        out if an attempt is made to specify a method.
        """
        pemPath = FilePath(self.mktemp())
        pemPath.setContent(CERTIFICATE_DATA + PRIVATEKEY_DATA)

        store = Store()
        factory = DummyFactory(store=store)
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create",
             "--strport", "ssl:8443:privateKey=" + pemPath.path +
             ":certKey=" + pemPath.path + ":sslmethod=TLSv1_METHOD",
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual(
            "Only SSLv23_METHOD is supported.\n",
            sys.stdout.getvalue())
        self.assertEqual(store.query(SSLPort).count(), 0)


    def test_createSSLPort(self):
        """
        If a given valid strport description of an SSL port and the storeID of
        an extant factory, I{axiomatic port create} creates a new L{SSLPort}
        with the specified configuration and referring to that factory.  The
        certificate file specified is copied to a path inside the Store's files
        directory.  The port is also powered up on the store for L{IService}.
        """
        pemPath = FilePath(self.mktemp())
        pemPath.setContent(CERTIFICATE_DATA + PRIVATEKEY_DATA)
        store = Store(filesdir=self.mktemp())
        factory = DummyFactory(store=store)
        self.assertSuccessStatus(
            self._makeConfig(store),
            ["create", "--strport",
             "ssl:8443:certKey=" + pemPath.path +
             ":privateKey=" + pemPath.path,
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual("Created.\n", sys.stdout.getvalue())
        [ssl] = list(store.query(SSLPort))
        self.assertEqual(ssl.portNumber, 8443)
        self.assertEqual(
            ssl.certificatePath.getContent(),
            CERTIFICATE_DATA + PRIVATEKEY_DATA)
        self.assertIdentical(ssl.factory, factory)
        self.assertEqual(
            pemPath.getContent(), CERTIFICATE_DATA + PRIVATEKEY_DATA)
        self.assertEqual(list(store.interfacesFor(ssl)), [IService])


    def test_createUnrecognized(self):
        """
        If given a strport description of an unrecognized port type,
        I{axiomatic port create} writes an error message to standard output.
        """
        store = Store()
        factory = DummyFactory(store=store)
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create", "--strport", "quux:foo",
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual(
            "Unrecognized port type.\n", sys.stdout.getvalue())


    def test_createUnsupported(self):
        """
        If given a strport description of a valid type which is not supported
        by Mantissa, I{axiomatic port create} writes an error message to
        standard output.
        """
        store = Store()
        factory = DummyFactory(store=store)
        self.assertFailStatus(
            1, self._makeConfig(store),
            ["create", "--strport", "unix:/foo",
             "--factory-identifier", str(factory.storeID)])
        self.assertEqual(
            "Unsupported port type.\n", sys.stdout.getvalue())
