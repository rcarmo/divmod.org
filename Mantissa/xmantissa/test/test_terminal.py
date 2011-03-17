# Copyright 2009 Divmod, Inc.  See LICENSE file for details

"""
Tests for L{xmantissa.terminal}.
"""

from zope.interface import implements
from zope.interface.verify import verifyObject

from twisted.internet.protocol import ProcessProtocol
from twisted.trial.unittest import TestCase
from twisted.cred.credentials import UsernamePassword
from twisted.conch.interfaces import IConchUser, ISession
from twisted.conch.ssh.keys import Key
from twisted.conch.ssh.session import SSHSession
from twisted.conch.insults.helper import TerminalBuffer
from twisted.conch.insults.insults import ServerProtocol
from twisted.conch.manhole import ColoredManhole

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import text, inmemory
from axiom.dependency import installOn
from axiom.userbase import LoginSystem, LoginMethod

from xmantissa.ixmantissa import IProtocolFactoryFactory, ITerminalServerFactory
from xmantissa.ixmantissa import IViewer
from xmantissa.sharing import getSelfRole
from xmantissa.terminal import SecureShellConfiguration, TerminalManhole
from xmantissa.terminal import ShellAccount, ShellServer, _ReturnToMenuWrapper
from xmantissa.terminal import _AuthenticatedShellViewer


class SecureShellConfigurationTests(TestCase):
    """
    Tests for L{xmantissa.shell.SecureShellConfiguration} which defines how to
    create an SSH server.
    """
    _hostKey = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIByAIBAAJhAM/dftm59mJJ1JVy0bsq8J7fp4WUecgaJukRyf637d76ywxRYGdw\n"
        "47hkBiJaDYgaE9HMlh2eSow3b2YCyom4FLlh/7Buq58A9IofR7ZiNVYv0ZDppbDg\n"
        "FN+Gl2ZFLFB3dwIBIwJgC+DFa4b4It+lv2Wllaquqf4m1G7iYzSxxCzm+JzLw5lN\n"
        "bmsM0rX+Yk7bx3LcM6m34vyvhY6p/kQyjHo7/CkpaSQg4bnpOcqEq3oMf8E0c0lp\n"
        "TQ1TdtfnKKrZZPTaVr7rAjEA7O19/tSLK6by1BpE1cb6W07GK1WcafYLxQLT64o+\n"
        "GKxbrlsossc8gWJ8GDRjE2S5AjEA4JkYfYkgfucH941r9yDFrhr6FuOdwbLXDESZ\n"
        "DyLhW/7DHiVIXlaLFnY+51PcTwWvAjBzFESDFsdBFpMz0j6w+j8WaBccXMhQuVYs\n"
        "fbdjxs20NnWsdWuKCQAhljxGRVSxpfMCMBmrGL3jyTMTFtp2j/78bl0KZbl5GVf3\n"
        "LoUPJ29xs1r4i1PnAPTWsM9d+I93TGDNcwIxAMRz4KO02tiLXG2igwDw/WWszrkr\n"
        "r4ggaFDlt4QqoNz0l4tayqzbDV1XceLgP4cXcQ==\n"
        "-----END RSA PRIVATE KEY-----\n")

    def setUp(self):
        """
        Create an in-memory L{Store} with a L{SecureShellConfiguration} in it.
        """
        self.store = Store()
        self.shell = SecureShellConfiguration(
            store=self.store, hostKey=self._hostKey)
        installOn(self.shell, self.store)


    def test_interfaces(self):
        """
        L{SecureShellConfiguration} implements L{IProtocolFactoryFactory}.
        """
        self.assertTrue(verifyObject(IProtocolFactoryFactory, self.shell))


    def test_powerup(self):
        """
        L{installOn} powers up the target for L{IProtocolFactoryFactory} with
        L{SecureShellConfiguration}.
        """
        self.assertIn(
            self.shell, list(self.store.powerupsFor(IProtocolFactoryFactory)))


    def test_repr(self):
        """
        The result of C{repr} on a L{SecureShellConfiguration} instance
        includes only a fingerprint of the private key, not the entire value.
        """
        self.assertEqual(
            repr(self.shell),
            "SecureShellConfiguration(storeID=%d, " % (self.shell.storeID,) +
            "hostKeyFingerprint='68cc7060bb6394060672467e7c4d8f3b')")


    def assertHostKey(self, shell, factory):
        """
        Assert that the public and private keys provided by C{factory}
        match those specified by C{shell} and that they are L{Key}
        instances.
        """
        privateKey = Key.fromString(shell.hostKey)
        self.assertEqual(
            factory.publicKeys, {'ssh-rsa': privateKey.public()})
        self.assertEqual(factory.privateKeys, {'ssh-rsa': privateKey})


    def test_getFactory(self):
        """
        L{SecureShellConfiguration.getFactory} returns an L{SSHFactory} with
        keys from L{SecureShellConfiguration.hostKey}.
        """
        factory = self.shell.getFactory()
        self.assertHostKey(self.shell, factory)


    def test_keyGeneration(self):
        """
        L{SecureShellConfiguration} generates its own key pair if one is not
        supplied to C{__init__}.
        """
        store = Store()
        shell = SecureShellConfiguration(store=store)
        installOn(shell, store)
        factory = shell.getFactory()
        self.assertHostKey(shell, factory)


    def test_portal(self):
        """
        The factory returned by L{SecureShellConfiguration.getFactory} has a
        C{portal} attribute which allows logins authenticated in the usual
        L{axiom.userbase} manner.
        """
        localpart = u'foo bar'
        domain = u'example.com'
        password = u'baz quux'

        loginSystem = self.store.findUnique(LoginSystem)
        account = loginSystem.addAccount(
            localpart, domain, password, internal=True)
        subStore = account.avatars.open()
        avatar = object()
        subStore.inMemoryPowerUp(avatar, IConchUser)
        factory = self.shell.getFactory()
        login = factory.portal.login(
            UsernamePassword(
                '%s@%s' % (localpart.encode('ascii'), domain.encode('ascii')),
                password),
            None, IConchUser)
        def cbLoggedIn(result):
            self.assertIdentical(IConchUser, result[0])
            self.assertIdentical(avatar, result[1])
        login.addCallback(cbLoggedIn)
        return login



class AuthenticatedShellViewerTests(TestCase):
    """
    Tests for L{_AuthenticatedShellViewer}, an L{IViewer} implementation for
    use with L{ITerminalServerFactory.buildTerminalProtocol}.
    """
    def test_interface(self):
        """
        L{_AuthenticatedShellViewer} instances provide L{IViewer}.
        """
        self.assertTrue(verifyObject(IViewer, _AuthenticatedShellViewer([])))


    def test_roleIn(self):
        """
        L{_AuthenticatedShellViewer.roleIn} returns a L{Role} for one of the
        account names passed to L{_AuthenticatedShellViewer.__init__}.
        """
        store = Store()
        viewer = _AuthenticatedShellViewer([(u"alice", u"example.com")])
        role = viewer.roleIn(store)
        self.assertEquals(role.externalID, u"alice@example.com")
        self.assertIdentical(role.store, store)



class ShellAccountTests(TestCase):
    """
    Tests for L{ShellAccount} which provide a basic L{IConchUser} avatar.
    """
    def setUp(self):
        """
        Create an in-memory L{Store} with a L{ShellAccount} in it.
        """
        self.store = Store()
        self.account = ShellAccount(store=self.store)
        installOn(self.account, self.store)


    def test_interfaces(self):
        """
        L{ShellAccount} powers up the item on which it is installed for
        L{IConchUser} and the L{IConchUser} powerup is adaptable to
        L{ISession}.
        """
        avatar = IConchUser(self.store)
        self.assertTrue(verifyObject(IConchUser, avatar))
        session = ISession(avatar)
        self.assertTrue(verifyObject(ISession, session))


    def test_lookupSessionChannel(self):
        """
        L{ShellAccount.lookupChannel} returns an L{SSHSession} instance.  (This
        is because L{SSHSession} implements handlers for the standard SSH
        requests issued to set up a shell.)
        """
        avatar = IConchUser(self.store)
        channel = avatar.lookupChannel('session', 65536, 16384, '')
        self.assertTrue(isinstance(channel, SSHSession))


    def test_openShell(self):
        """
        The L{ISession} adapter of the L{IConchUser} powerup implements
        C{openShell} so as to associate the given L{IProcessProtocol} with a
        transport.
        """
        proto = ProcessProtocol()
        session = ISession(IConchUser(self.store))

        # XXX See Twisted ticket #3864
        proto.session = session
        proto.write = lambda bytes: None

        # XXX See #2895.
        session.getPty(None, (123, 456, 789, 1000), None)
        session.openShell(proto)
        self.assertNotIdentical(proto.transport, None)



class FakeTerminal(TerminalBuffer):
    """
    A fake implementation of L{ITerminalTransport} used by the
    L{_ReturnToMenuWrapper} tests.
    """
    disconnected = False

    def loseConnection(self):
        self.disconnected = True



class ReturnToMenuTests(TestCase):
    """
    Tests for L{_ReturnToMenuWrapper} which wraps an L{ITerminalTransport} for
    an L{ITerminalProtocol} and switches to another L{ITerminalProtocol} when
    C{loseConnection} is called on it instead of disconnecting.
    """
    def test_write(self):
        """
        L{_ReturnToMenuWrapper.write} passes through to the wrapped terminal.
        """
        terminal = FakeTerminal()
        terminal.makeConnection(None)
        wrapper = _ReturnToMenuWrapper(None, terminal)
        wrapper.write('some bytes')
        wrapper.write('some more')
        self.assertIn('some bytessome more', str(terminal))


    def test_loseConnection(self):
        """
        L{_ReturnToMenuWrapper.loseConnection} does not disconnect the
        terminal; instead it calls the C{reactivate} method of its C{shell}
        attribute.
        """
        class FakeShell(object):
            activated = False

            def reactivate(self):
                self.activated = True

        shell = FakeShell()
        terminal = FakeTerminal()
        wrapper = _ReturnToMenuWrapper(shell, terminal)
        wrapper.loseConnection()
        self.assertFalse(terminal.disconnected)
        self.assertTrue(shell.activated)



class MockTerminalProtocol(object):
    """
    Implementation of L{ITerminalProtocol} used in test L{ShellServer}'s
    interactions with the interface.

    @ivar terminal: The L{ITerminalTransport} passed to C{makeConnection}.

    @ivar keystrokes: A C{list} of two-tuples giving each keystroke which this
        protocol has received.

    @ivar disconnected: A C{bool} indicating whether C{connectionLost} has been
        called yet.
    """
    def __init__(self):
        self.keystrokes = []
        self.terminal = None
        self.disconnected = False


    def makeConnection(self, terminal):
        self.terminal = terminal


    def connectionLost(self, reason):
        self.disconnected = True


    def keystrokeReceived(self, keyID, modifier):
        self.keystrokes.append((keyID, modifier))



class MockTerminalServerFactory(object):
    """
    Implementation of L{ITerminalServerFactory} used in test L{ShellServer}'s
    interactions with the interface.

    @ivar terminalProtocolInstance: The L{MockTerminalServer} created and
        returned by C{buildTerminalProtocol}, or C{None} if that method has not
        been called.
    """
    implements(ITerminalServerFactory)

    name = "mock"
    shellViewer = None
    terminalProtocolInstance = None

    def buildTerminalProtocol(self, shellViewer):
        self.shellViewer = shellViewer
        self.terminalProtocolInstance = MockTerminalProtocol()
        return self.terminalProtocolInstance

# Sanity check - this isn't a comprehensive (or even close) verification of
# MockTerminalServerFactory, but it at least points out obvious mistakes.
verifyObject(ITerminalServerFactory, MockTerminalServerFactory())



class MockTerminalServerFactoryItem(Item):
    """
    An L{Item} implementation of L{ITerminalServerFactory} used by tests.
    """
    powerupInterfaces = (ITerminalServerFactory,)
    implements(*powerupInterfaces)

    name = text()
    shellViewer = inmemory(
        doc="""
        The L{IViewer} passed to L{buildTerminalProtocol}.
        """)
    terminalProtocolInstance = inmemory(
        doc="""
        The L{MockTerminalServer} created and returned by
        C{buildTerminalProtocol}, or C{None} if that method has not been
        called.
        """)

    def activate(self):
        self.shellViewer = None
        self.terminalProtocolInstance = None


    def buildTerminalProtocol(self, shellViewer):
        self.shellViewer = shellViewer
        self.terminalProtocolInstance = MockTerminalProtocol()
        return self.terminalProtocolInstance

# Sanity check - see above call to verifyObject.
verifyObject(ITerminalServerFactory, MockTerminalServerFactoryItem())



class ShellServerTests(TestCase):
    """
    Tests for L{ShellServer} which is the top-level L{ITerminalProtocol},
    interacting initially and directly with terminals by presenting a menu of
    possible activities and delegating to other L{ITerminalProtocol}s which
    appropriate.
    """
    def test_switchTo(self):
        """
        L{ShellServer.switchTo} takes a L{ITerminalServerFactory} and uses it
        to create a new L{ITerminalProtocol} which it connects to a
        L{_ReturnToMenuWrapper}.  L{buildTerminalProtocol} is passed an
        L{IViewer}.
        """
        terminal = FakeTerminal()
        store = Store()
        # Put a login method into the store so it can have a role.  See #2665.
        LoginMethod(
            store=store, internal=True, protocol=u'*', verified=True,
            localpart=u'alice', domain=u'example.com',
            # Not really an account, but simpler...
            account=store)
        server = ShellServer(store)
        server.makeConnection(terminal)
        factory = MockTerminalServerFactory()
        server.switchTo(factory)
        self.assertIdentical(factory.shellViewer.roleIn(store), getSelfRole(store))
        self.assertTrue(isinstance(server._protocol, MockTerminalProtocol))
        self.assertTrue(isinstance(server._protocol.terminal, _ReturnToMenuWrapper))
        self.assertIdentical(server._protocol.terminal._shell, server)
        self.assertIdentical(server._protocol.terminal._terminal, terminal)


    def test_appButtons(self):
        """
        L{ShellServer._appButtons} returns an iterator the elements of which
        are L{Button} instances, one for each L{ITerminalServerFactory}
        powerup.  When one of these buttons is activated, L{ShellServer} is
        switched to the corresponding L{ITerminalServerFactory}'s protocol.
        """
        store = Store()
        terminal = FakeTerminal()
        server = ShellServer(store)
        server.makeConnection(terminal)

        firstFactory = MockTerminalServerFactoryItem(
            store=store, name=u"first - \N{ROMAN NUMERAL ONE}")
        installOn(firstFactory, store)
        secondFactory = MockTerminalServerFactoryItem(
            store=store, name=u"second - \N{ROMAN NUMERAL TWO}")
        installOn(secondFactory, store)

        buttons = list(server._appButtons())
        self.assertEqual(len(buttons), 2)

        # For now, we'll say the order isn't significant.
        buttons.sort(key=lambda b: b.label)

        self.assertEqual(
            buttons[0].label, firstFactory.name.encode('utf-8'))
        buttons[0].onPress()

        server.keystrokeReceived('x', None)
        self.assertEqual(
            firstFactory.terminalProtocolInstance.keystrokes, [('x', None)])

        self.assertEqual(
            buttons[1].label, secondFactory.name.encode('utf-8'))
        buttons[1].onPress()
        server.keystrokeReceived('y', None)
        self.assertEqual(
            secondFactory.terminalProtocolInstance.keystrokes, [('y', None)])


    def test_logoffButton(self):
        """
        L{ShellServer._logoffButton} returns a L{Button} which, when activated,
        disconnects the terminal.
        """
        terminal = FakeTerminal()
        server = ShellServer(Store())
        server.makeConnection(terminal)
        server._logoffButton().onPress()
        self.assertTrue(terminal.disconnected)


    def test_reactivate(self):
        """
        L{ShellServer.reactivate} disconnects the protocol previously switched
        to, drops the reference to it, and redraws the main menu.
        """
        terminal = FakeTerminal()
        server = ShellServer(Store())
        server.makeConnection(terminal)
        server.switchTo(MockTerminalServerFactory())
        server.reactivate()
        self.assertIdentical(server._protocol, None)


    def test_keystrokeReceivedWindow(self):
        """
        L{ShellServer.keystrokeReceived} delivers keystroke data to the main
        menu widget when no protocol has been switched to.
        """
        class FakeWidget(object):
            def __init__(self):
                self.keystrokes = []

            def keystrokeReceived(self, keyID, modifier):
                self.keystrokes.append((keyID, modifier))

        terminal = FakeTerminal()
        window = FakeWidget()
        server = ShellServer(Store())
        server._makeWindow = lambda: window
        server.makeConnection(terminal)
        server.keystrokeReceived(' ', ServerProtocol.ALT)
        self.assertEqual(window.keystrokes, [(' ', ServerProtocol.ALT)])


    def test_keystrokeReceivedProtocol(self):
        """
        L{ShellServer.keystrokeReceived} delivers keystroke data to the
        protocol built by the factory which has been switched to.
        """
        factory = MockTerminalServerFactory()
        terminal = FakeTerminal()
        server = ShellServer(Store())
        server.makeConnection(terminal)
        server.switchTo(factory)
        server.keystrokeReceived(' ', ServerProtocol.ALT)
        self.assertEqual(
            factory.terminalProtocolInstance.keystrokes,
            [(' ', ServerProtocol.ALT)])



class ManholeTests(TestCase):
    """
    Tests for L{TerminalManhole} which provides an L{ITerminalServerFactory}
    for a protocol which gives a user an in-process Python REPL.
    """
    def test_interface(self):
        """
        L{TerminalManhole} implements L{ITerminalServerFactory}.
        """
        self.assertTrue(verifyObject(ITerminalServerFactory, TerminalManhole()))


    def test_buildTerminalProtocol(self):
        """
        L{TerminalManhole.buildTerminalProtocol} returns a L{ColoredManhole}
        with a namespace including the store the L{TerminalManhole} is in.
        """
        store = Store()
        factory = TerminalManhole(store=store)
        viewer = object()
        protocol = factory.buildTerminalProtocol(viewer)
        self.assertTrue(isinstance(protocol, ColoredManhole))
        self.assertEqual(protocol.namespace, {'db': store, 'viewer': viewer})
