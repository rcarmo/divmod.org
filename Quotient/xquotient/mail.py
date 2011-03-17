# -*- test-case-name: xquotient.test.test_mta -*-
# Copyright (c) 2008 Divmod.  See LICENSE for details.

"""
Support for SMTP servers in Quotient.

Implementations of L{twisted.mail.smtp.IMessageDeliveryFactory},
L{twisted.mail.smtp.IMessageDelivery}, and L{twisted.mail.smtp.IMessage} can be
found here.  There are classes for handling anonymous SMTP delivery into the
system (the typical case for receiving messages for Quotient users from
elsewhere) and authenticated SMTP (the way Quotient users will send messages to
other people).  SMTP, SMTP/SSL, and STARTTLS are all supported, mainly for free
from Twisted's SSL and SMTP support code.
"""

import datetime

try:
    from OpenSSL import SSL
except ImportError:
    SSL = None

from zope.interface import implements

from twisted.internet import protocol, defer
from twisted.internet.ssl import PrivateCertificate, CertificateOptions
from twisted.protocols import policies
from twisted.python import failure
from twisted.cred import portal, checkers, credentials
from twisted.mail import smtp, imap4
from twisted.mail.smtp import IMessageDeliveryFactory
from twisted.application.service import IService

from axiom import item, attributes, userbase, batch
from axiom.attributes import reference, integer, bytes
from axiom.upgrade import registerUpgrader
from axiom.errors import MissingDomainPart
from axiom.dependency import dependsOn, installOn

from xmantissa.ixmantissa import IProtocolFactoryFactory
from xmantissa.port import TCPPort, SSLPort

from xquotient import iquotient, exmess, mimestorage

MessageSource = batch.processor(exmess.Message)

class MailConfigurationError(RuntimeError):
    """You specified some invalid configuration.
    """

class MessageDelivery(object):
    """
    Message Delivery implementation used by anonymous senders.

    This implementation only allows messages to be delivered to local users
    (ie, it does not perform relaying) and rejects sender addresses which
    belong to local users.
    """
    implements(smtp.IMessageDelivery)

    def __init__(self, store, portal):
        self.store = store
        self.portal = portal


    def receivedHeader(self, helo, origin, recipients):
        return "" # Maybe put something here?


    def validateFrom(self, helo, origin):
        if origin.domain in userbase.getDomainNames(self.store):
            return defer.fail(smtp.SMTPBadSender(origin))
        return defer.succeed(origin)


    def validateTo(self, user):
        addr = '@'.join((user.dest.local, user.dest.domain))
        d = self.portal.login(
            userbase.Preauthenticated(addr), None, iquotient.IMIMEDelivery)
        def loggedIn((iface, avatar, logout)):
            logout() # XXX???
            def receiverCreator():
                return avatar.createMIMEReceiver(
                    u"smtp://%s@%s" % (user.dest.local, user.dest.domain))
            return receiverCreator
        def notLoggedIn(err):
            err.trap(userbase.NoSuchUser)
            return defer.fail(smtp.SMTPBadRcpt(user))
        d.addCallbacks(loggedIn, notLoggedIn)
        return d



class SafeMIMEParserWrapper(object):
    """
    Simple wrapper around a real MIME parser which captures errors from
    lineReceived and saves them until messageDone().
    """
    implements(smtp.IMessage)

    failure = None

    def __init__(self, receiver):
        self.receiver = receiver


    def lineReceived(self, line):
        if self.failure is None:
            try:
                return self.receiver.lineReceived(line)
            except:
                self.failure = failure.Failure()


    def messageDone(self):
        if self.failure is not None:
            self.failure.raiseException()
        else:
            return self.receiver.messageDone()


    def __getattr__(self, name):
        # Let people get at feedStringNow and that junk, if they want.
        # We won't help them out if they try.
        return getattr(self.receiver, name)



class DeliveryAgent(item.Item):
    """
    Entrypoint for MIME-formatted content into a Quotient-enabled Store.

    @ivar messageCount: The number of MIME receivers which have ever been
    created. (Not necessarily the number of messages which have been delivered
    - XXX rename this to receiverCount and add messageCount which counts
    messages).
    """
    implements(iquotient.IMIMEDelivery)

    installedOn = attributes.reference()
    messageCount = attributes.integer(default=0)

    powerupInterfaces = (iquotient.IMIMEDelivery,)

    def _createMIMESourceFile(self):
        """
        @return: an L{AtomicFile} with a pathname appropriate to a message that was
        just delivered.
        """
        today = datetime.date.today()
        fObj = self.store.newFile(
            'messages',
            str(today.year),
            str(today.month),
            str(today.day),
            str(self.messageCount % 100),
            str(self.messageCount))
        self.messageCount += 1
        return fObj


    def createMIMEReceiver(self, source):
        """
        Basic implementation of L{iquotient.IMIMEDelivery.createMIMEReceiver}.
        """
        return SafeMIMEParserWrapper(mimestorage.IncomingMIMEMessageStorer(
            self.store, self._createMIMESourceFile(), source))


    def _createMIMEDraftReceiver(self, source):
        """
        Temporary hack so that the composer does not deliver messages to the
        inbox.

        This should really be refactored ASAP to separate the steps of MIME
        message parsing and message delivery.
        """
        return mimestorage.DraftMIMEMessageStorer(
            self.store, self._createMIMESourceFile(), source)


    def _createDraftUpdateReceiver(self, message, source):
        """

        Temporary hack because the compose system is hideously complex
        and drafts are touching too much state in the system.

        This interface is wrong because::

            The composer has no business knowing about the object
            lifetimes of draft messages.  It is responsible for
            creating them and sending them, what happens in between is
            the concern of the user interface and the mimebakery
            module.

            The composer should not have MIME text pushed through it
            in order to create message objects.  It should be possible
            to create these in a much simpler way, both for ease of
            programming and because it may be necessary to create
            message objects when no Composer exists.
        """
        return mimestorage.ExistingMessageMIMEStorer(
            self.store, self._createMIMESourceFile(), source, message)



class QuotientESMTP(smtp.ESMTP):
    """
    Trivial customization of the basic ESMTP server: when this server
    notices a login which fails with L{axiom.errors.MissingDomainPart} it
    reports a special error message to the user suggesting they add a domain
    to their username.
    """
    def _ebAuthenticated(self, err):
        if err.check(MissingDomainPart):
            self.challenge = None
            self.sendCode(
                535,
                'Authentication failure [Username without domain name '
                '(ie "yourname" instead of "yourname@yourdomain") not '
                'allowed; try with a domain name.]')
        else:
            return smtp.ESMTP._ebAuthenticated(self, err)



class ESMTPFactory(protocol.ServerFactory):
    """
    Protocol factory for enhanced SMTP server connections.  Creates server
    protocol instances which know about CRAM-MD5 and TLS.
    """
    protocol = QuotientESMTP

    def __init__(self, portal, hostname, challengers, contextFactory):
        self.portal = portal
        self.hostname = hostname
        self.challengers = challengers
        self.contextFactory = contextFactory


    def buildProtocol(self, addr):
        p = self.protocol(
            self.challengers,
            self.contextFactory)
        p.factory = self
        p.portal = self.portal
        if self.hostname is not None:
            p.host = self.hostname
        return p



class MailTransferAgent(item.Item):
    """
    Service responsible for binding server ports for SMTP and SMTP/SSL
    protocols.  Also responsible for attaching an appropriately Axiomified cred
    portal to the factories for those servers.
    """
    implements(IProtocolFactoryFactory, IMessageDeliveryFactory)

    powerupInterfaces = (IProtocolFactoryFactory, IMessageDeliveryFactory)

    typeName = "mantissa_mta"
    schemaVersion = 4

    certificateFile = attributes.bytes(
        "The name of a file on disk containing a private key and certificate "
        "for use by the SMTP server when negotiating TLS.",
        default=None)

    messageCount = attributes.integer(
        "The number of messages which have been delivered through this agent.",
        default=0)

    domain = attributes.bytes(
        "The canonical name of this host.  Used when greeting SMTP clients.",
        default=None)

    userbase = dependsOn(userbase.LoginSystem)

    # A cred portal, a Twisted TCP factory and as many as two
    # IListeningPorts
    portal = attributes.inmemory()
    factory = attributes.inmemory()

    # When enabled, toss all traffic into logfiles.
    debug = False

    def activate(self):
        self.portal = None
        self.factory = None


    # IMessageDeliveryFactory
    def getMessageDelivery(self):
        # Force self.portal to be created
        self.getFactory()
        return MessageDelivery(self.store, self.portal)


    # IProtocolFactoryFactory
    def getFactory(self):
        if self.factory is None:
            if self.certificateFile is not None:
                cert = PrivateCertificate.loadPEM(
                    file(self.certificateFile).read())
                certOpts = CertificateOptions(
                    cert.privateKey.original,
                    cert.original,
                    requireCertificate=False,
                    method=SSL.SSLv23_METHOD)
            else:
                certOpts = None

            self.portal = portal.Portal(
                self.userbase, [self.userbase, checkers.AllowAnonymousAccess()])
            self.factory = ESMTPFactory(
                self.portal,
                self.domain,
                {'CRAM-MD5': credentials.CramMD5Credentials,
                 'LOGIN': imap4.LOGINCredentials,
                 },
                certOpts)
            if self.debug:
                self.factory = policies.TrafficLoggingFactory(self.factory, 'smtp')
        return self.factory

    # GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG
    def setServiceParent(self, parent):
        pass


item.declareLegacyItem(typeName=MailTransferAgent.typeName,
                  schemaVersion=2,
                  attributes=dict(messageCount=attributes.integer(),
                                  installedOn=attributes.reference(),
                                  portNumber=attributes.integer(),
                                  securePortNumber=attributes.integer(),
                                  certificateFile=attributes.bytes(),
                                  domain=attributes.bytes()))

def upgradeMailTransferAgent1to2(oldMTA):
    """
    MailTransferAgent has been replaced with MailDeliveryAgent on B{user
    stores}.  Delete it from user stores and create a MailDelivery agent
    there, but leave it alone on the site store.
    """
    loginSystem = oldMTA.store.findUnique(userbase.LoginSystem, default=None)
    if loginSystem is not None:
        newMTA = oldMTA.upgradeVersion(
            'mantissa_mta', 1, 2,
            messageCount=oldMTA.messageCount,
            installedOn=oldMTA.installedOn,
            portNumber=oldMTA.portNumber,
            securePortNumber=oldMTA.securePortNumber,
            certificateFile=oldMTA.certificateFile,
            domain=oldMTA.domain)
        return newMTA
    else:
        mda = MailDeliveryAgent(store=oldMTA.store)
        mda.installedOn = oldMTA.store
        oldMTA.store.powerUp(mda, smtp.IMessageDeliveryFactory)
        oldMTA.store.powerDown(oldMTA, smtp.IMessageDeliveryFactory)
        oldMTA.deleteFromStore()
        # The MTA was deleted, there's no sensible Item to return here.
        return mda

registerUpgrader(upgradeMailTransferAgent1to2, 'mantissa_mta', 1, 2)

def upgradeMailTransferAgent2to3(old):
    """
    Add the userbase field since MTA depends on it and remove installedOn.

    The isinstance check here is to avoid doing anything to MDA
    instances returned by the 1to2 upgrader.
    """
    if isinstance(old, MailDeliveryAgent):
        return old
    mta = old.upgradeVersion(MailTransferAgent.typeName, 2, 3,
                             messageCount=old.messageCount,
                             portNumber=old.portNumber,
                             securePortNumber=old.securePortNumber,
                             certificateFile=old.certificateFile,
                             domain=old.domain)
    mta.userbase = old.store.findOrCreate(userbase.LoginSystem)
    return mta
registerUpgrader(upgradeMailTransferAgent2to3, MailTransferAgent.typeName, 2, 3)


item.declareLegacyItem(
    MailTransferAgent.typeName, 3, dict(messageCount=integer(default=0),
                                        portNumber=integer(default=0),
                                        securePortNumber=integer(default=0),
                                        certificateFile=bytes(default=None),
                                        domain=bytes(default=None),
                                        userbase=reference(doc="dependsOn(LoginSystem)")))

def upgradeMailTransferAgent3to4(oldMTA):
    """
    Create TCPPort and SSLPort items as appropriate.
    """
    if isinstance(oldMTA, MailDeliveryAgent):
        return oldMTA
    newMTA = oldMTA.upgradeVersion(
        MailTransferAgent.typeName, 3, 4,
        userbase=oldMTA.userbase,
        certificateFile=oldMTA.certificateFile,
        messageCount=oldMTA.messageCount,
        domain=oldMTA.domain)

    if oldMTA.portNumber is not None:
        port = TCPPort(store=newMTA.store, portNumber=oldMTA.portNumber, factory=newMTA)
        installOn(port, newMTA.store)

    securePortNumber = oldMTA.securePortNumber
    certificateFile = oldMTA.certificateFile
    if securePortNumber is not None and certificateFile:
        oldCertPath = newMTA.store.dbdir.preauthChild(certificateFile)
        if oldCertPath.exists():
            newCertPath = newMTA.store.newFilePath('mta.pem')
            oldCertPath.copyTo(newCertPath)
            port = SSLPort(store=newMTA.store, portNumber=securePortNumber, certificatePath=newCertPath, factory=newMTA)
            installOn(port, newMTA.store)

    newMTA.store.powerDown(newMTA, IService)

    return newMTA
registerUpgrader(upgradeMailTransferAgent3to4, MailTransferAgent.typeName, 3, 4)


class NullMessage(object):
    """
    Void implementation of L{smtp.IMessage}.  Accepts and discards all events
    which can occur.
    """
    implements(smtp.IMessage)

    def lineReceived(self, line):
        pass


    def eomReceived(self):
        pass


    def connectionLost(self):
        pass



class OutgoingMessageWrapper(object):
    """
    L{smtp.IMessage} provider which wraps another provider of the same
    interface and uses an L{iquotient.IMessageSender} to deliver the message
    someplace else after it has been completed.

    @type sender: L{iquotient.IMessageSender} provider
    @ivar sender: The object which will be used to send the created message
    when it is ready.

    @type recipients: C{list} of C{unicode}
    @ivar recipients: RFC2822 addresses to which the message will be sent.

    @ivar mimeReceiver: The wrapped L{smtp.IMessage} provider.  In addition to
    providing that interface, it must also have a C{message} attribute after
    C{messageDone} returns.  This is typically expected to be an instance of
    L{xquotient.mimestorage.IncomingMIMEMessageStorer}.
    """
    implements(smtp.IMessage)

    def __init__(self, sender, recipients, mimeReceiver):
        self.sender = sender
        self.recipients = recipients
        self.mimeReceiver = mimeReceiver


    def lineReceived(self, line):
        """
        Accept the next line from the message and pass it through to the
        wrapped L{smtp.IMessage}.
        """
        return self.mimeReceiver.lineReceived(line)


    def eomReceived(self):
        """
        Pass completion notification through to the wrapped L{smtp.IMessage}
        and then send the resulting message using C{self.sender.sendMessage}.
        """
        result = self.mimeReceiver.eomReceived()
        self.sender.sendMessage(
            self.recipients,
            self.mimeReceiver.message)
        return result


    def connectionLost(self):
        return self.mimeReceiver.connectionLost()



class MailDeliveryAgent(item.Item):
    """
    Class responsible for authenticated delivery.
    """
    implements(smtp.IMessageDeliveryFactory)

    installedOn = attributes.reference()

    powerupInterfaces = (smtp.IMessageDeliveryFactory,)

    def getMessageDelivery(self):
        realm = portal.IRealm(self.store.parent)
        chk = checkers.ICredentialsChecker(self.store.parent)
        return AuthenticatedMessageDelivery(
            iquotient.IMIMEDelivery(self.store),
            iquotient.IMessageSender(self.store))


    # Sometimes (depending on upgrader order) this can be used as an
    # IService (because MailTransferAgent used to be an IService powerup,
    # and an upgrade replaced some MailTransferAgent instances with
    # MailDeliveryAgent instances).  See #2922.
    def setServiceParent(self, parent):
        pass


class AuthenticatedMessageDelivery(object):
    """
    Class responsible for delivering messages from authenticated users.
    """
    implements(smtp.IMessageDelivery)

    origin = None
    _recipientAddresses = None

    def __init__(self, avatar, composer):
        self.avatar = avatar
        self.composer = composer


    def receivedHeader(self, helo, origin, recipients):
        return ""


    def validateFrom(self, helo, origin):
        """
        Verify that the given origin address is one this user is allowed to
        claim.
        """
        for local, domain in userbase.getAccountNames(self.avatar.store):
            if local == origin.local and domain == origin.domain:
                self.origin = origin
                return defer.succeed(origin)
        return defer.fail(smtp.SMTPBadSender(origin))


    def validateTo(self, user):
        """
        Determine whether the recipient is local to this system or not and
        dispatch to the appropriate helper method.
        """
        siteStore = self.avatar.store.parent
        if user.dest.domain in userbase.getDomainNames(siteStore):
            return self.localValidateTo(user)
        else:
            return self.remoteValidateTo(user)


    def localValidateTo(self, user):
        """
        Determine whether the given user exists locally.  If they do not,
        reject the address as invalid.  If they do, return a delivery object
        appropriate for that user.  Currently this delivery object is the same
        as the remote delivery object, but at some point it may make sense to
        optimize this codepath and skip the network for local<->local delivery.
        """
        siteStore = self.avatar.store.parent
        loginSystem = siteStore.findUnique(userbase.LoginSystem)
        account = loginSystem.accountByAddress(
            user.dest.local.decode('ascii'),
            user.dest.domain.decode('ascii'))
        if account is None:
            return defer.fail(smtp.SMTPBadRcpt(user))
        else:
            # XXX TODO - We could skip the network here.
            return self.remoteValidateTo(user)


    def remoteValidateTo(self, user):
        """
        Either create a new L{OutgoingMessageWrapper} around a MIME receiver
        which delivers into this user's store or add the given address to the
        list of addresses an existing L{OutgoingMessageWrapper} will deliver
        to.

        This takes care to only create one C{smtp.IMessage} provider per
        message so that only one sent message will appear in a user's account
        regardless of the number of recipients they specify.
        """
        address = u'@'.join((user.dest.local, user.dest.domain))
        if self._recipientAddresses is not None:
            self._recipientAddresses.append(address)
            return defer.succeed(NullMessage)
        self._recipientAddresses = [address]
        def createMIMEReceiver():
            return OutgoingMessageWrapper(
                self.composer,
                self._recipientAddresses,
                self.avatar.createMIMEReceiver(
                    u"sent://%s@%s" % (self.origin.local, self.origin.domain)))
        return defer.succeed(createMIMEReceiver)
