# -*- test-case-name: xquotient.test.test_compose -*-

import datetime

from zope.interface import implements

from twisted.internet import defer, error
from twisted.python import log
from twisted.mail import smtp, relaymanager
from twisted.names import client

from epsilon import descriptor, extime

from nevow.athena import LiveElement
from nevow.page import renderer

from axiom import attributes, iaxiom, item, userbase
from axiom.attributes import AND
from axiom.upgrade import registerUpgrader, registerAttributeCopyingUpgrader

from xmantissa import ixmantissa, liveform
from xmantissa.scrolltable import ScrollingFragment
from xmantissa.webtheme import getLoader

from xquotient import mimeutil



def _esmtpSendmail(username, password, smtphost, port, from_addr, to_addrs,
                   msg, reactor=None):
    """
    This should be the only function in this module that uses the reactor.
    """
    d = defer.Deferred()
    f = smtp.ESMTPSenderFactory(username, password, from_addr, to_addrs, msg,
                                d, requireTransportSecurity=False)
    if reactor is None:
        from twisted.internet import reactor
    reactor.connectTCP(smtphost, port, f)
    return d



def _getFromAddressFromStore(store):
    """
    Find a suitable outgoing email address by looking at the
    L{userbase.LoginMethod} items in C{store}.  Throws L{RuntimeError} if it
    can't find anything
    """
    for meth in userbase.getLoginMethods(store, protocol=u'email'):
        if meth.internal or meth.verified:
            return meth.localpart + '@' + meth.domain
    raise RuntimeError("cannot find a suitable LoginMethod")



class _TransientError(Exception):
    pass



class FromAddress(item.Item):
    """
    I hold information about an email addresses that a user can send mail from
    """
    schemaVersion = 2
    typeName = 'xquotient_compose_fromaddress'

    _address = attributes.text(doc="""
                The email address.  Don't set this directly; use
                C{self.address}.
                """)


    class address(descriptor.attribute):
        def get(self):
            """
            Substitute the result of C{_getFromAddressFromStore} on our store if
            C{self._address} is None, so we can avoid storing the system address
            in the database, as it will change if this store is migrated
            """
            if self._address is None:
                return _getFromAddressFromStore(self.store)
            return self._address

        def set(self, value):
            self._address = value


    _default = attributes.boolean(default=False, doc="""
                Is this the default from address?  Don't mutate this value
                directly, use L{setAsDefault}
                """)


    # if any of these are set, they should all be set
    smtpHost = attributes.text()
    smtpPort = attributes.integer(default=25)
    smtpUsername = attributes.text()
    smtpPassword = attributes.text()


    def setAsDefault(self):
        """
        Make this the default from address, revoking the defaultness of the
        previous default.
        """
        default = self.store.findUnique(
                    FromAddress, FromAddress._default == True,
                    default=None)
        if default is not None:
            default._default = False
        self._default = True


    def findDefault(cls, store):
        """
        Find the L{FromAddress} item which is the current default address
        """
        return store.findUnique(cls, cls._default == True)
    findDefault = classmethod(findDefault)


    def findSystemAddress(cls, store):
        """
        Find the L{FromAddress} item which represents the "system address" -
        i.e. the L{FromAddress} item we created out of the user's login
        credentials
        """
        return cls.findByAddress(store, None)
    findSystemAddress = classmethod(findSystemAddress)


    def findByAddress(cls, store, address):
        """
        Find the L{FromAddress} item with address C{address}
        """
        return store.findUnique(cls, cls._address == address)
    findByAddress = classmethod(findByAddress)



def fromAddress1to2(old):
    new = old.upgradeVersion(old.typeName, 1, 2,
                             _address=old.address,
                             _default=old._default,
                             smtpHost=old.smtpHost,
                             smtpPort=old.smtpPort,
                             smtpUsername=old.smtpUsername,
                             smtpPassword=old.smtpPassword)

    if new._address == _getFromAddressFromStore(new.store):
        new._address = None
    return new



registerUpgrader(fromAddress1to2, FromAddress.typeName, 1, 2)



class MessageDelivery(item.Item):
    """
    Handles the delivery of a single message to multiple addresses.
    """

    composer = attributes.reference()
    message = attributes.reference()


    def allBounced(self):
        """
        Did all of the addresses bounce?

        @return: L{True} if all addresses bounced. L{False} otherwise.
        """
        return self.store.findFirst(
            DeliveryToAddress,
            AND(DeliveryToAddress.delivery == self,
                DeliveryToAddress.status.oneOf([UNSENT, SENT]))) is None


    def allDone(self):
        """
        Has the message been delivered (or failed to be delivered) to all of
        the addresses?

        @return: L{True} if there are no messages pending. L{False} otherwise.
        """
        return self.store.findFirst(
            DeliveryToAddress, AND(DeliveryToAddress.status == UNSENT,
                                   DeliveryToAddress.delivery == self)) is None


    def send(self, fromAddress, toAddresses, reallySend=True):
        """
        Send the message to a number of addresses using the given From address.

        @param fromAddress: The address to send from.
        @param toAddresses: A collection of Unicode email addresses.
        @param reallySend: If C{True}, actually try to send messages. Otherwise,
        just create the delivery objects.

        @return: None
        """
        self.message.startedSending()
        for toAddress in toAddresses:
            d = DeliveryToAddress(store=self.store,
                                  delivery=self,
                                  message=self.message,
                                  fromAddress=fromAddress,
                                  toAddress=toAddress)
            if reallySend:
                d.run()


    def sent(self, delivery):
        """
        Called by a L{DeliveryToAddress} object after it has successfully sent
        a message to a particular address.

        @param delivery: A L{DeliveryToAddress} item.

        @return: None
        """
        delivery.status = SENT
        self.message.sent()
        log.msg('%r probably delivered to %r' % (self.message,
                                                 delivery.toAddress))
        if self.allDone():
            self.message.finishedSending()


    def bounced(self, delivery, log):
        """
        Called by a L{DeliveryToAddress} object after it has failed to send
        a message to a particular address.

        @param delivery: A L{DeliveryToAddress} item.
        @param log: A string log of the exchange leading up to and
        including the error.

        @return: None
        """
        delivery.status = BOUNCED
        self.composer.messageBounced(log, delivery.toAddress, self.message)
        if self.allDone():
            self.message.finishedSending()
            if self.allBounced():
                self.message.allBounced()



UNSENT, SENT, BOUNCED = range(3)


class DeliveryToAddress(item.Item):
    schemaVersion = 3
    typeName = 'xquotient_compose__needsdelivery'

    delivery = attributes.reference()
    message = attributes.reference()
    fromAddress = attributes.reference()
    toAddress = attributes.text()
    tries = attributes.integer(default=0)
    status = attributes.integer(default=UNSENT)

    running = attributes.inmemory()

    # Retry for about five days, backing off to trying once every 6 hours gradually.
    RETRANS_TIMES = ([60] * 5 +          #     5 minutes
                     [60 * 5] * 5 +      #    25 minutes
                     [60 * 30] * 3 +     #    90 minutes
                     [60 * 60 * 2] * 2 + #   240 minutes
                     [60 * 60 * 6] * 19) # + 114 hours   = 5 days


    def activate(self):
        self.running = False


    def _createCalculator(self):
        """
        Return a L{relaymanager.MXCalculator} which can be used to look up
        the mail exchange for a domain.
        """
        resolver = client.Resolver(resolv='/etc/resolv.conf')
        return relaymanager.MXCalculator(resolver)


    def getMailExchange(self, recipientDomain):
        """
        Look up the mail exchange host for the given domain.

        @param recipientDomain: A C{str} giving the mail domain for which to
            perform the lookup.

        @return: A L{Deferred} which will fire with a C{str} giving the mail
            exchange hostname, or which will will errback if no mail
            exchange can be found.
        """
        return self._createCalculator().getMX(recipientDomain)


    def _getMessageSource(self):
        return self.delivery.message.impl.source.open()


    def sendmail(self):
        """
        Send this queued message.

        @param fromAddress: An optional address to use in the SMTP
            conversation.
        """
        fromAddress = self.fromAddress
        if fromAddress is None:
            fromAddress = FromAddress.findDefault(self.store)

        if fromAddress.smtpHost:
            return _esmtpSendmail(
                fromAddress.smtpUsername,
                fromAddress.smtpPassword,
                fromAddress.smtpHost,
                fromAddress.smtpPort,
                fromAddress.address,
                [self.toAddress],
                self._getMessageSource())
        else:
            d = self.getMailExchange(mimeutil.EmailAddress(
                    self.toAddress, mimeEncoded=False).domain)
            def sendMail(mx):
                host = str(mx.name)
                log.msg(interface=iaxiom.IStatEvent, stat_messagesSent=1,
                        userstore=self.store)
                return smtp.sendmail(
                    host,
                    fromAddress.address,
                    [self.toAddress],
                    # XXX
                    self._getMessageSource())
            d.addCallback(sendMail)
            return d


    def mailSent(self, ignored, sch):
        """
        Called by L{run} when the message has been successfully sent.
        """
        # Success!  Don't bother to try again.
        sch.unscheduleAll(self)
        self.delivery.sent(self)


    def failureSending(self, err, sch):
        """
        Called by L{run} after an unsuccessful attempt to send the message.

        @param err: The error that stopped the message from being sent.
        @type err: L{twisted.python.failure.Failure}
        """
        t = err.trap(smtp.SMTPDeliveryError, error.DNSLookupError)
        if t is smtp.SMTPDeliveryError:
            code = err.value.code
            log = err.value.log
            if 500 <= code < 600 or self.tries >= len(self.RETRANS_TIMES):
                # Fatal, don't bother to try again.
                self.delivery.bounced(self, log)
                sch.unscheduleAll(self)
        elif t is error.DNSLookupError:
            # Lalala
            pass
        else:
            assert False, "Cannot arrive at this branch."


    def run(self):
        """
        Try to reliably deliver this message. If errors are encountered, try
        harder.
        """
        sch = iaxiom.IScheduler(self.store)
        if self.tries < len(self.RETRANS_TIMES):
            # Set things up to try again, if this attempt fails
            nextTry = datetime.timedelta(seconds=self.RETRANS_TIMES[self.tries])
            sch.schedule(self, extime.Time() + nextTry)

        if not self.running:
            self.running = True
            self.tries += 1

            d = self.sendmail()
            d.addCallback(self.mailSent, sch)
            d.addErrback(self.failureSending, sch)
            d.addErrback(log.err)



item.declareLegacyItem(DeliveryToAddress.typeName, 2,
                       dict(composer = attributes.reference(),
                            message = attributes.reference(),
                            fromAddress = attributes.reference(),
                            toAddress = attributes.text(),
                            tries = attributes.integer(default=0)))



def deliveryToAddress2to3(old):
    delivery = MessageDelivery(composer=old.composer,
                               message=old.message,
                               store=old.store)
    new = old.upgradeVersion(old.typeName, 2, 3,
                             delivery=delivery,
                             message=old.message,
                             fromAddress=old.fromAddress,
                             toAddress=old.toAddress,
                             tries=old.tries,
                             status=UNSENT)
    return new



registerAttributeCopyingUpgrader(DeliveryToAddress, 1, 2)
registerUpgrader(deliveryToAddress2to3, DeliveryToAddress.typeName, 2, 3)



class FromAddressConfigFragment(LiveElement):
    """
    Fragment which contains some stuff that helps users configure their from
    addresses, such as an L{xmantissa.liveform.LiveForm} for adding new ones,
    and an L{xmantissa.scrolltable.ScrollingFragment} for looking at and
    editing existing ones
    """
    implements(ixmantissa.INavigableFragment)
    fragmentName = 'from-address-config'
    title = 'From Addresses'

    def __init__(self, composePrefs):
        self.composePrefs = composePrefs
        LiveElement.__init__(self)


    def addAddress(self, address, smtpHost, smtpPort, smtpUsername, smtpPassword, default):
        """
        Add a L{FromAddress} item with the given attribute values
        """
        addr = FromAddress(store=self.composePrefs.store,
                           address=address,
                           smtpHost=smtpHost,
                           smtpPort=smtpPort,
                           smtpUsername=smtpUsername,
                           smtpPassword=smtpPassword)

        if default:
            addr.setAsDefault()


    def addAddressForm(self, req, tag):
        """
        @return: an L{xmantissa.liveform.LiveForm} instance which allows users
                 to add from addresses
        """
        def makeRequiredCoercer(paramName, coerce=lambda v: v):
            def notEmpty(value):
                if not value:
                    raise liveform.InvalidInput('value required for ' + paramName)
                return coerce(value)
            return notEmpty

        def textParam(name, label, *a):
            return liveform.Parameter(
                    name, liveform.TEXT_INPUT, makeRequiredCoercer(name), label, *a)

        # ideally we would only show the "address" input by default and have a
        # "SMTP Info" disclosure link which exposes the rest of them

        lf = liveform.LiveForm(
                self.addAddress,
                (textParam('address',  'Email Address'),
                 textParam('smtpHost', 'SMTP Host'),
                 liveform.Parameter(
                    'smtpPort',
                    liveform.TEXT_INPUT,
                    makeRequiredCoercer('smtpPort', int),
                    'SMTP Port',
                    default=25),
                 textParam('smtpUsername', 'SMTP Username'),
                 liveform.Parameter(
                    'smtpPassword',
                     liveform.PASSWORD_INPUT,
                     makeRequiredCoercer('smtpPassword'),
                     'SMTP Password'),
                 liveform.Parameter(
                    'default',
                    liveform.CHECKBOX_INPUT,
                    bool,
                    'Default?',
                    'Use this as default from address')),
                 description='Add From Address')
        lf.jsClass = u'Quotient.Compose.AddAddressFormWidget'
        lf.docFactory = getLoader('liveform-compact')
        lf.setFragmentParent(self)
        return lf
    renderer(addAddressForm)


    def fromAddressScrollTable(self, req, tag):
        """
        @return: L{FromAddressScrollTable}
        """
        f = FromAddressScrollTable(self.composePrefs.store)
        f.docFactory = getLoader(f.fragmentName)
        f.setFragmentParent(self)
        return f
    renderer(fromAddressScrollTable)


    def head(self):
        return None



class FromAddressAddressColumn(object):
    implements(ixmantissa.IColumn)

    attributeID = '_address'

    def sortAttribute(self):
        return FromAddress._address


    def extractValue(self, model, item):
        return item.address


    def getType(self):
        return 'text'



class FromAddressScrollTable(ScrollingFragment):
    """
    L{xmantissa.scrolltable.ScrollingFragment} subclass for browsing
    and editing L{FromAddress} items.
    """
    jsClass = u'Quotient.Compose.FromAddressScrollTable'


    def __init__(self, store):
        ScrollingFragment.__init__(
                self, store,
                FromAddress,
                None,
                (FromAddressAddressColumn(),
                 FromAddress.smtpHost,
                 FromAddress.smtpPort,
                 FromAddress.smtpUsername,
                 FromAddress._default))


    def action_setDefaultAddress(self, item):
        """
        Make the C{item} the default L{FromAddress} for outgoing mail
        """
        item.setAsDefault()


    def action_delete(self, item):
        """
        Delete the given L{FromAddress}
        """
        item.deleteFromStore()


    def getInitialArguments(self):
        """
        Include the web ID of the L{FromAddress} item which represents
        the system address, so the client can prevent it from being deleted
        """
        systemAddress = FromAddress.findSystemAddress(self.store)
        return super(FromAddressScrollTable, self).getInitialArguments() + [
            unicode(self.webTranslator.toWebID(systemAddress), 'ascii')]


