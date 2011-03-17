# -*- test-case-name: xmantissa.test.test_terminal -*-
# Copyright 2009 Divmod, Inc.  See LICENSE file for details

"""
This module provides an extensible terminal server for Mantissa, exposed over
L{SSHv2<twisted.conch>}.  The server supports username/password authentication
and encrypted communication.  It can be extended by applications which provide
L{ITerminalServerFactory} powerups to create L{ITerminalProtocol} providers.
"""

from md5 import md5

from Crypto.PublicKey import RSA

from zope.interface import implements

from twisted.python.randbytes import secureRandom

from twisted.python.components import Componentized
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ICredentialsChecker
from twisted.conch.interfaces import IConchUser, ISession
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.conch.manhole_ssh import TerminalUser, TerminalSession, TerminalSessionTransport
from twisted.conch.insults.insults import ServerProtocol, TerminalProtocol
from twisted.conch.insults.window import TopWindow, VBox, Border, Button
from twisted.conch.manhole import ColoredManhole

from axiom.iaxiom import IPowerupIndirector
from axiom.item import Item
from axiom.attributes import bytes
from axiom.dependency import dependsOn
from axiom.userbase import LoginSystem, getAccountNames

from xmantissa.ixmantissa import IProtocolFactoryFactory, ITerminalServerFactory
from xmantissa.ixmantissa import IViewer
from xmantissa.sharing import getAccountRole


__metaclass__ = type


def _generate():
    """
    Generate a new SSH key pair.
    """
    key = RSA.generate(1024, secureRandom)
    return Key(key).toString('openssh')



class _AuthenticatedShellViewer:
    """
    L{_AuthenticatedShellViewer} is an L{IViewer} implementation used to
    indicate to shell applications which user is trying to access them.

    @ivar _accountNames: A list of account names associated with this viewer.
        This is in the same form as the return value of L{getAccountNames}.
    """
    implements(IViewer)

    def __init__(self, accountNames):
        self._accountNames = accountNames


    def roleIn(self, userStore):
        """
        Get the authenticated role for the user represented by this view in the
        given user store.
        """
        return getAccountRole(userStore, self._accountNames)



class SecureShellConfiguration(Item):
    """
    Configuration object for a Mantissa SSH server.
    """
    powerupInterfaces = (IProtocolFactoryFactory,)
    implements(*powerupInterfaces)

    loginSystem = dependsOn(LoginSystem)

    hostKey = bytes(
        doc="""
        An OpenSSH-format string giving the host key for this server.
        """, allowNone=False, defaultFactory=_generate)


    def __repr__(self):
        """
        Return a summarized representation of this item.
        """
        fmt = "SecureShellConfiguration(storeID=%d, hostKeyFingerprint='%s')"
        privateKey = Key.fromString(data=self.hostKey)
        publicKeyBlob = privateKey.blob()
        fingerprint = md5(publicKeyBlob).hexdigest()
        return fmt % (self.storeID, fingerprint)


    def getFactory(self):
        """
        Create an L{SSHFactory} which allows access to Mantissa accounts.
        """
        privateKey = Key.fromString(data=self.hostKey)
        public = privateKey.public()
        factory = SSHFactory()
        factory.publicKeys = {'ssh-rsa': public}
        factory.privateKeys = {'ssh-rsa': privateKey}
        factory.portal = Portal(
            IRealm(self.store), [ICredentialsChecker(self.store)])
        return factory



class _ReturnToMenuWrapper:
    """
    L{ITerminalTransport} wrapper which changes only the behavior of the
    C{loseConnection} method.  Rather than allowing the terminal to be
    disconnected, a L{ShellServer} is re-activated.

    @ivar _shell: The L{ShellServer} to re-activate when disconnection is
        attempted.

    @ivar _terminal: The L{ITerminalTransport} to which to proxy all attribute
        lookups other than C{loseConnection}.
    """
    def __init__(self, shell, terminal):
        self._shell = shell
        self._terminal = terminal


    def loseConnection(self):
        self._shell.reactivate()


    def __getattr__(self, name):
        return getattr(self._terminal, name)



class ShellServer(TerminalProtocol):
    """
    A terminal protocol which finds L{ITerminalServerFactory} powerups in the
    same store and presents the option of beginning a session with one of them.

    @ivar _store: The L{Store} which will be searched for
        L{ITerminalServerFactory} powerups.

    @ivar _protocol: If an L{ITerminalServerFactory} has been selected to
        interact with, then this attribute refers to the L{ITerminalProtocol}
        produced by that factory's C{buildTerminalProtocol} method.  Input from
        the terminal is delivered to this protocol.  This attribute is C{None}
        whenever the "main menu" user interface is being displayed.

    @ivar _window: A L{TopWindow} instance which contains the "main menu" user
        interface.  Whenever the C{_protocol} attribute is C{None}, input is
        directed to this object instead.  Whenever the C{_protocol} attribute
        is not C{None}, this window is hidden.
    """
    _width = 80
    _height = 24

    _protocol = None

    def __init__(self, store):
        TerminalProtocol.__init__(self)
        self._store = store


    def _draw(self):
        """
        Call the drawing API for the main menu widget with the current known
        terminal size and the terminal.
        """
        self._window.draw(self._width, self._height, self.terminal)


    def _appButtons(self):
        for factory in self._store.powerupsFor(ITerminalServerFactory):
            yield Button(
                factory.name.encode('utf-8'),
                lambda factory=factory: self.switchTo(factory))


    def _logoffButton(self):
        return Button("logoff", self.logoff)


    def _makeWindow(self):
        buttons = VBox()
        for button in self._appButtons():
            buttons.addChild(Border(button))
        buttons.addChild(Border(self._logoffButton()))

        from twisted.internet import reactor
        window = TopWindow(self._draw, lambda f: reactor.callLater(0, f))
        window.addChild(Border(buttons))
        return window


    def connectionMade(self):
        """
        Reset the terminal and create a UI for selecting an application to use.
        """
        self.terminal.reset()
        self._window = self._makeWindow()


    def reactivate(self):
        """
        Called when a sub-protocol is finished.  This disconnects the
        sub-protocol and redraws the main menu UI.
        """
        self._protocol.connectionLost(None)
        self._protocol = None
        self.terminal.reset()
        self._window.filthy()
        self._window.repaint()


    def switchTo(self, app):
        """
        Use the given L{ITerminalServerFactory} to create a new
        L{ITerminalProtocol} and connect it to C{self.terminal} (such that it
        cannot actually disconnect, but can do most anything else).  Control of
        the terminal is delegated to it until it gives up that control by
        disconnecting itself from the terminal.

        @type app: L{ITerminalServerFactory} provider
        @param app: The factory which will be used to create a protocol
            instance.
        """
        viewer = _AuthenticatedShellViewer(list(getAccountNames(self._store)))
        self._protocol = app.buildTerminalProtocol(viewer)
        self._protocol.makeConnection(_ReturnToMenuWrapper(self, self.terminal))


    def keystrokeReceived(self, keyID, modifier):
        """
        Forward input events to the application-supplied protocol if one is
        currently active, otherwise forward them to the main menu UI.
        """
        if self._protocol is not None:
            self._protocol.keystrokeReceived(keyID, modifier)
        else:
            self._window.keystrokeReceived(keyID, modifier)


    def logoff(self):
        """
        Disconnect from the terminal completely.
        """
        self.terminal.loseConnection()



class _BetterTerminalSession(TerminalSession):
    """
    L{TerminalSession} is missing C{windowChanged} and C{eofReceived} for some
    reason.  Add it here until it's fixed in Twisted.  See Twisted ticket
    #3303.
    """
    def windowChanged(self, newWindowSize):
        """
        Ignore window size change events.
        """


    def eofReceived(self):
        """
        Ignore the eof event.
        """


class _BetterTerminalUser(TerminalUser):
    """
    L{TerminalUser} is missing C{conn} for some reason reason (probably the
    reason that it's not a very great thing and generally an implementation
    will be missing it for a while).  Add it here until it's fixed in Twisted.
    See Twisted ticket #3863.
    """
    # Some code in conch will rudely rebind this attribute later.  For now,
    # make sure that it is at least bound to something so that the object
    # appears to fully implement IConchUser.  Most likely, TerminalUser should
    # be taking care of this, not us.  Or even better, this attribute shouldn't
    # be part of the interface; some better means should be provided for
    # informing the IConchUser avatar of the connection object (I'm not even
    # sure why the avatar would care about having a reference to the connection
    # object).
    conn = None


class ShellAccount(Item):
    """
    Axiom cred hook for creating SSH avatars.
    """
    powerupInterfaces = (IConchUser,)
    implements(IPowerupIndirector)

    garbage = bytes()

    def indirect(self, interface):
        """
        Create an L{IConchUser} avatar which will use L{ShellServer} to
        interact with the connection.
        """
        if interface is IConchUser:
            componentized = Componentized()

            user = _BetterTerminalUser(componentized, None)
            session = _BetterTerminalSession(componentized)
            session.transportFactory = TerminalSessionTransport
            session.chainedProtocolFactory = lambda: ServerProtocol(ShellServer, self.store)

            componentized.setComponent(IConchUser, user)
            componentized.setComponent(ISession, session)

            return user

        raise NotImplementedError(interface)



class TerminalManhole(Item):
    """
    A terminal application which presents an interactive Python session running
    in the primary Mantissa server process.
    """
    powerupInterfaces = (ITerminalServerFactory,)
    implements(*powerupInterfaces)

    shell = dependsOn(ShellAccount)

    name = 'manhole'

    def buildTerminalProtocol(self, shellViewer):
        """
        Create and return a L{ColoredManhole} which includes this item's store
        in its namespace.
        """
        return ColoredManhole({'db': self.store, 'viewer': shellViewer})



__all__ = ['SecureShellConfiguration', 'ShellAccount', 'TerminalManhole']
