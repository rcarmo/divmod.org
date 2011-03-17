# -*- test-case-name: xquotient.test.test_popout -*-

import os

from zope.interface import implements

from twisted.python import log
from twisted.internet import defer, protocol
from twisted.protocols import policies
from twisted.cred import portal
from twisted.mail import pop3
from twisted.application.service import IService
from twisted.internet.task import coiterate

from axiom import item, attributes
from axiom.item import declareLegacyItem
from axiom.attributes import bytes, reference, integer
from axiom.errors import MissingDomainPart
from axiom.userbase import LoginSystem
from axiom.dependency import dependsOn, installOn
from axiom.upgrade import registerUpgrader

from xmantissa.ixmantissa import IProtocolFactoryFactory
from xmantissa.port import TCPPort, SSLPort

from xquotient.exmess import Message


class MessageInfo(item.Item):
    typeName = 'quotient_pop3_message'
    schemaVersion = 2

    localPop3UID = attributes.bytes()
    localPop3Deleted = attributes.boolean(indexed=True)

    message = attributes.reference()



def _transactionally(iterator, transactor, ntimes):
    """
    Run chunks of an iterator transactionally.

    @param iterator: an iterator which will yield some results

    @param transactor: a function which takes a callable and runs its argument,
    such as store.transact

    @param ntimes: an integer explaining how many times to run the iterator's
    next() method in one chunk.

    @return: an iterator which will yield the same results as the input
    iterator.
    """
    done = []
    results = []
    def chunker():
        results[:] = []
        for x in range(ntimes):
            try:
                results.append(iterator.next())
            except StopIteration:
                done.append(True)
                break
    while not done:
        transactor(chunker)
        for result in results:
            yield result



class _ActualMailbox:
    """
    This is an in-memory implementation of all the transient state associated
    with a user's authenticated POP3 session.
    """

    listingDeferred = None
    pagesize = 20

    def __init__(self, store):
        """
        Create a mailbox implementation from an L{axiom.store.Store}.

        @type store: L{axiom.store.Store}

        @param store: a user store containing L{Message} and possibly also
        L{MessageInfo} objects.
        """
        self.store = store
        self.undeleteMessages()
        self.messageList = None
        self.coiterate = coiterate


    def whenReady(self):
        """
        Return a deferred which will fire when the mailbox is ready, or a
        deferred which has already fired if the mailbox is already ready.
        """
        if self.listingDeferred is None:
            self.listingDeferred = self.kickoff()
        return _ndchain(self.listingDeferred)


    def kickoff(self):
        """
        Begin loading all POP-accessible messages into an in-memory list.

        @return: a Deferred which will fire with a list of L{MessageInfo}
        instances when complete.
        """
        def _(ignored):
            return self.messageList
        return self.coiterate(_transactionally(self._buildMessageList(),
                                               self.store.transact,
                                               # lambda x: x(),
                                               self.pagesize)).addCallback(_)


    def _buildMessageList(self):
        """
        @return: a generator, designed to be run to completion in coiterate(),
        which will alternately yield None and L{MessageInfo} instances as it
        loads them from the database.
        """
        infoList = []
        for message in self.store.query(Message
                                        ).paginate(pagesize=self.pagesize):
            # Find the POP information for this message.
            messageInfos = list(self.store.query(MessageInfo,
                                                 MessageInfo.message == message))
            if len(messageInfos) == 0:
                messageInfo = MessageInfo(store=self.store,
                                          localPop3Deleted=False,
                                          localPop3UID=os.urandom(16).encode('hex'),
                                          message=message)
            else:
                messageInfo = messageInfos[0]
            if messageInfo.localPop3Deleted:
                yield None
            else:
                infoList.append(messageInfo)
                yield messageInfo
        self.messageList = infoList


    def messageSize(self, index):
        if index in self.deletions:
            return 0
        i = self._getMessageImpl(index).message.impl
        return i.bodyOffset + (i.bodyLength or 0)



    def listMessages(self, index=None):
        if index is None:
            return [self.messageSize(idx) for idx in
                    xrange(len(self.messageList))]
        else:
            return self.messageSize(index)


    def _getMessageImpl(self, index):
        msgList = self.messageList
        try:
            msg = msgList[index]
        except IndexError:
            raise ValueError(index)
        else:
            return msg


    def deleteMessage(self, index):
        if index in self.deletions:
            raise ValueError(index)
        self._getMessageImpl(index)
        self.deletions.add(index)


    def getMessage(self, index):
        if index in self.deletions:
            raise ValueError(index)
        return self._getMessageImpl(index).message.impl.source.open()


    def getUidl(self, index):
        if index in self.deletions:
            raise ValueError(index)
        return self._getMessageImpl(index).localPop3UID


    def sync(self):
        ml = self.messageList
        for delidx in self.deletions:
            ml[delidx].localPop3Deleted = True
        self.messageList = None
        self.deletions = set()
        self.listingDeferred = None
        self.whenReady()


    def undeleteMessages(self):
        self.deletions = set()


def _ndchain(d1):
    """
    Create a deferred based on another deferred's results, without altering the
    value which will be passed to callbacks of the input deferred.

    @param d1: a L{Deferred} which will fire in the future.

    @return: a L{Deferred} which will fire at the same time as the given input,
    with the same value.
    """
    # this is a re-implementation of functionality in epsilon.pending (among
    # other places).  TODO: decide on one way to do this and make everything
    # use it.  I think this is a decent implementation strategy but I am
    # leaving it private here because I have thought that 5 other ways to do
    # this were _also_ decent implementation strategies and they all met with
    # despair.  Once we have a consistent application of such multi-deferred
    # functionality across all Divmod projects, it should move into Twisted.
    # --glyph
    d2 = defer.Deferred()
    def cb(value):
        try:
            d2.callback(value)
        except:
            log.err()
        return value
    d1.addBoth(cb)
    return d2


class POP3Up(item.Item):
    """
    This is a powerup which provides POP3 mailbox functionality to a user.

    The actual work of implementing L{IMailbox} is done in a separate,
    transient in-memory class.
    """

    typeName = 'quotient_pop3_user_powerup'

    implements(pop3.IMailbox)

    powerupInterfaces = (pop3.IMailbox,)

    actualMailbox = attributes.inmemory()

    installedOn = attributes.reference()


    def installOn(self, other):
        super(POP3Up, self).installOn(other)
        other.powerUp(self, pop3.IMailbox)


    def _realize(self):
        """
        Generate the object which will implement this user's mailbox.

        @return: an L{_ActualMailbox} instance.
        """
        r = _ActualMailbox(self.store)
        self.actualMailbox = r
        return r


    def logout(self):
        """
        Re-initialize actualMailbox attribute for future sessions.
        """
        self.actualMailbox = None


    def _deferOperation(self, methodName):
        """
        This generates methods which, when invoked, will tell my mailbox
        implementation to load all of its messages if necessary and then
        perform the requested operation.

        @type methodName: L{str}

        @param methodName: the name of the method being potentially deferred.
        Should be in L{IMailbox}.

        @return: a callable which returns a Deferred that fires with the
        results of the given IMailbox method.
        """
        actualMailbox = getattr(self, 'actualMailbox', None)
        if actualMailbox is None:
            actualMailbox = self._realize()
        actualMethod = getattr(actualMailbox, methodName)
        def inner(*a, **k):
            def innerinner(ignored):
                return actualMethod(*a, **k)
            if methodName in ['getUidl', 'deleteMessage', 'undeleteMessages',
                              'sync']:
                # Twisted's POP3 implementation can't handle a Deferred here.
                # Arguably this is a bug, but we have to work around it for the
                # moment.
                return innerinner(None)
            return actualMailbox.whenReady().addCallback(innerinner)
        return inner


    def __getattribute__(self, name):
        """
        Provides normal attribute access, except for methods from
        L{pop3.IMailbox}, which are handled with L{_deferOperation}.

        @param name: the name of the attribute being requested.
        """
        if name in pop3.IMailbox:
            return self._deferOperation(name)
        return super(POP3Up, self).__getattribute__(name)



class QuotientPOP3(pop3.POP3):
    """
    Trivial customization of the basic POP3 server: when this server notices
    a login which fails with L{axiom.errors.MissingDomainPart} it reports a
    special error message to the user suggesting they add a domain to their
    username.
    """
    def _ebMailbox(self, err):
        if err.check(MissingDomainPart):
            self.failResponse(
                'Username without domain name (ie "yourname" instead of '
                '"yourname@yourdomain") not allowed; try with a domain name.')
        else:
            return pop3.POP3._ebMailbox(self, err)



class POP3ServerFactory(protocol.Factory):

    implements(pop3.IServerFactory)

    protocol = QuotientPOP3

    def __init__(self, portal):
        self.portal = portal


    def cap_IMPLEMENTATION(self):
        from xquotient import version
        return "Quotient " + str(version)


    def cap_EXPIRE(self):
        raise NotImplementedError()


    def cap_LOGIN_DELAY(self):
        return 120


    def perUserLoginDelay(self):
        return True


    def buildProtocol(self, addr):
        p = protocol.Factory.buildProtocol(self, addr)
        p.portal = self.portal
        return p



class POP3Benefactor(item.Item):
    endowed = attributes.integer(default=0)
    powerupNames = ["xquotient.popout.POP3Up"]



class POP3Listener(item.Item):
    implements(IProtocolFactoryFactory)

    powerupInterfaces = (IProtocolFactoryFactory,)

    typeName = "quotient_pop3listener"
    schemaVersion = 3

    # A cred portal, a Twisted TCP factory and as many as two
    # IListeningPorts
    portal = attributes.inmemory()
    factory = attributes.inmemory()

    certificateFile = attributes.bytes(
        "The name of a file on disk containing a private key and certificate "
        "for use by the POP3 server when negotiating TLS.",
        default=None)

    userbase = dependsOn(LoginSystem)

    # When enabled, toss all traffic into logfiles.
    debug = False


    def activate(self):
        self.portal = None
        self.factory = None


    # IProtocolFactoryFactory
    def getFactory(self):
        if self.factory is None:
            self.portal = portal.Portal(self.userbase, [self.userbase])
            self.factory = POP3ServerFactory(self.portal)

            if self.debug:
                self.factory = policies.TrafficLoggingFactory(self.factory, 'pop3')
        return self.factory


    def setServiceParent(self, parent):
        """
        Compatibility hack necessary to prevent the Axiom service startup
        mechanism from barfing.  Even though this Item is no longer an IService
        powerup, it will still be found as one one more time and this method
        will be called on it.
        """



def pop3Listener1to2(old):
    p3l = old.upgradeVersion(POP3Listener.typeName, 1, 2)
    p3l.userbase = old.store.findOrCreate(LoginSystem)
    return p3l
registerUpgrader(pop3Listener1to2, POP3Listener.typeName, 1, 2)

declareLegacyItem(
    POP3Listener.typeName, 2, dict(portNumber=integer(default=6110),
                                   securePortNumber=integer(default=0),
                                   certificateFile=bytes(default=None),
                                   userbase=reference(doc="dependsOn(LoginSystem)")))

def pop3listener2to3(oldPOP3):
    """
    Create TCPPort and SSLPort items as appropriate.
    """
    newPOP3 = oldPOP3.upgradeVersion(
        POP3Listener.typeName, 2, 3,
        userbase=oldPOP3.userbase,
        certificateFile=oldPOP3.certificateFile)

    if oldPOP3.portNumber is not None:
        port = TCPPort(store=newPOP3.store, portNumber=oldPOP3.portNumber, factory=newPOP3)
        installOn(port, newPOP3.store)

    securePortNumber = oldPOP3.securePortNumber
    certificateFile = oldPOP3.certificateFile
    if securePortNumber is not None and certificateFile:
        oldCertPath = newPOP3.store.dbdir.preauthChild(certificateFile)
        if oldCertPath.exists():
            newCertPath = newPOP3.store.newFilePath('pop3.pem')
            oldCertPath.copyTo(newCertPath)
            port = SSLPort(store=newPOP3.store, portNumber=oldPOP3.securePortNumber, certificatePath=newCertPath, factory=newPOP3)
            installOn(port, newPOP3.store)

    newPOP3.store.powerDown(newPOP3, IService)

    return newPOP3
registerUpgrader(pop3listener2to3, POP3Listener.typeName, 2, 3)
