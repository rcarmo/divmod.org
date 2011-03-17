# -*- test-case-name: xquotient.test.test_grabber -*-

from epsilon import hotfix
hotfix.require('twisted', 'deferredgenerator_tfailure')

import time, datetime

from twisted.mail import pop3, pop3client
from twisted.internet import protocol, defer, ssl, error
from twisted.python import log, components, failure
from twisted.protocols import policies

from nevow import loaders, tags, athena
from nevow.flat import flatten
from nevow.athena import expose

from epsilon import descriptor, extime

from axiom import item, attributes, iaxiom
from axiom.dependency import dependsOn
from axiom.upgrade import registerUpgrader

from xmantissa import ixmantissa,  webtheme, liveform
from xmantissa.webapp import PrivateApplication

from xmantissa.scrolltable import ScrollingFragment, AttributeColumn, TYPE_FRAGMENT
from xmantissa.stats import BandwidthMeasuringFactory

from xquotient.mail import DeliveryAgent


PROTOCOL_LOGGING = True


class Status(item.Item):
    """
    Represents the latest status of a particular grabber.
    """

    when = attributes.timestamp(doc="""
    Time at which this status was set.
    """)

    message = attributes.text(doc="""
    A short string describing the current state of the grabber.
    """)

    success = attributes.boolean(doc="""
    Flag indicating whether this status indicates a successful action
    or not.
    """)

    changeObservers = attributes.inmemory(doc="""
    List of single-argument callables which will be invoked each time
    this status changes.
    """)


    def __repr__(self):
        return '<Status %r>' % (self.message,)


    def activate(self):
        self.changeObservers = []
        self.message = u"idle"


    def addChangeObserver(self, observer):
        self.changeObservers.append(observer)
        return lambda: self.changeObservers.remove(observer)


    def setStatus(self, message, success=True):
        self.when = extime.Time()
        self.message = message
        self.success = success
        for L in self.changeObservers:
            try:
                L(message)
            except:
                log.err(None, "Failure in status update")



class GrabberBenefactor(item.Item):
    """
    Installs a GrabberConfiguration (and any requisite website
    powerups) on avatars.
    """

    endowed = attributes.integer(doc="""
    The number of avatars who have been endowed by this benefactor.
    """, default=0)
    powerupNames = ["xquotient.grabber.GrabberConfiguration"]

class GrabberConfiguration(item.Item):
    """
    Manages the creation, operation, and destruction of grabbers
    (items which retrieve information from remote sources).
    """
    schemaVersion = 3

    paused = attributes.boolean(doc="""
    Flag indicating whether grabbers created by this Item will be
    allowed to run.
    """, default=False)

    privateApplication = dependsOn(PrivateApplication)
    deliveryAgent = dependsOn(DeliveryAgent)

    def addGrabber(self, username, password, domain, ssl):
        # DO IT
        if ssl:
            port = 995
        else:
            port = 110

        pg = POP3Grabber(
            store=self.store,
            username=username,
            password=password,
            domain=domain,
            port=port,
            config=self,
            ssl=ssl)
        # DO IT *NOW*
        self.scheduler.schedule(pg, extime.Time())
        # OR MAYBE A LITTLE LATER

item.declareLegacyItem(GrabberConfiguration.typeName, 1, dict(
    paused=attributes.boolean(default=False),
    installedOn=attributes.reference()))

def _grabberConfiguration1to2(old):
    new = old.upgradeVersion(GrabberConfiguration.typeName, 1, 2,
                             paused=old.paused,
                             privateApplication = old.store.findOrCreate(PrivateApplication),
                             deliveryAgent = old.store.findOrCreate(DeliveryAgent))
    return new
registerUpgrader(_grabberConfiguration1to2, GrabberConfiguration.typeName, 1, 2)

item.declareLegacyItem(GrabberConfiguration.typeName, 2, dict(
    paused=attributes.boolean(default=False),
    scheduler=attributes.reference(),
    privateApplication=attributes.reference(),
    deliveryAgent=attributes.reference(),
    ))


def _grabberConfiguration2to3(old):
    """
    Copy all the remaining attributes.
    """
    new = old.upgradeVersion(GrabberConfiguration.typeName, 2, 3,
                             paused=old.paused,
                             privateApplication = old.store.findOrCreate(PrivateApplication),
                             deliveryAgent = old.store.findOrCreate(DeliveryAgent))
    return new
registerUpgrader(_grabberConfiguration2to3, GrabberConfiguration.typeName, 2, 3)


class POP3UID(item.Item):
    grabberID = attributes.text(doc="""
    A string identifying the email-address/port parts of a
    configured grabber
    """, indexed=True)

    value = attributes.bytes(doc="""
    A POP3 UID which has already been retrieved.
    """, indexed=True)

    failed = attributes.boolean(doc="""
    When set, indicates that an attempt was made to retrieve this UID,
    but for some reason was unsuccessful.
    """, indexed=True, default=False)



class POP3Grabber(item.Item):
    """
    Item for retrieving email messages from a remote POP server.
    """

    config = attributes.reference(doc="""
    The L{GrabberConfiguration} which created this grabber.
    """)

    status = attributes.reference(doc="""
    The current state of this grabber.  This indicates whether a grab
    is currently being run, if a password is incorrect, etc.
    """)

    paused = attributes.boolean(doc="""
    Flag indicating whether this particular grabber will try to get
    scheduled to retrieve messages.
    """, default=False)

    username = attributes.text(doc="""
    Username in the remote system with which to authenticate.
    """, allowNone=False)

    password = attributes.text(doc="""
    Password in the remote system with which to authenticate.
    """, allowNone=False)

    domain = attributes.text(doc="""
    The address of the remote system to which to connect.
    """, allowNone=False)

    port = attributes.integer(doc="""
    TCP port number on the remote system to which to connect.
    """, default=110)

    ssl = attributes.boolean(doc="""
    Flag indicating whether to connect using SSL (note: this does not
    affect whether TLS will be negotiated post-connection.)
    """, default=False)

    messageCount = attributes.integer(doc="""
    The number of messages which have been retrieved by this grabber.
    """, default=0)

    running = attributes.inmemory(doc="""
    Flag indicating whether an attempt to retrieve messages is
    currently in progress.  Only one attempt is allowed outstanding at
    any given time.
    """)

    protocol = attributes.inmemory(doc="""
    While self.running=True this attribute will point to the
    ControlledPOP3GrabberProtocol that is grabbing stuff
    for me""")

    connector = attributes.inmemory(doc="""
    implementor of L{twisted.internet.interfaces.IConnector}, representing
    our connection to the POP server
    """)

    scheduled = attributes.timestamp(doc="""
    When this grabber is next scheduled to run.
    """)

    debug = attributes.boolean(doc="""
    Flag indicating whether to log traffic from this grabber or not.
    """, default=False)

    created = attributes.timestamp(doc="""
    Creation time of this grabber.  Used when deciding whether a grabbed
    message is old enough to automatically archive.
    """)

    _pop3uids = attributes.inmemory(doc="""
    A set of strings representing all the POP3 UIDs which have already been
    downloaded by this grabber.
    """)


    class installedOn(descriptor.attribute):
        def get(self):
            return self.config.installedOn


    def __init__(self, **kw):
        if 'created' not in kw:
            kw['created'] = extime.Time()
        return super(POP3Grabber, self).__init__(**kw)


    def activate(self):
        self._pop3uids = None
        self.running = False
        self.protocol = None
        if self.status is None:
            self.status = Status(store=self.store, message=u'idle')

    def delete(self):
        self.config.scheduler.unscheduleAll(self)
        if self.running:
            if self.protocol is not None:
                self.protocol.stop()
                self.protocol.grabber = None
            else:
                self.connector.disconnect()
        self.deleteFromStore()

    def grab(self):
        # Don't run concurrently, ever.
        if self.running:
            return
        self.running = True

        from twisted.internet import reactor

        port = self.port
        if self.ssl:
            if port is None:
                port = 995
            connect = lambda h, p, f: reactor.connectSSL(h, p, f, ssl.ClientContextFactory())
        else:
            if port is None:
                port = 110
            connect = reactor.connectTCP

        factory = POP3GrabberFactory(self, self.ssl)
        if self.debug:
            factory = policies.TrafficLoggingFactory(
                factory,
                'pop3client-%d-%f' % (self.storeID, time.time()))

        self.status.setStatus(u"Connecting to %s:%d..." % (self.domain, port))
        self.connector = connect(self.domain, port, BandwidthMeasuringFactory(factory, 'pop3-grabber'))


    def run(self):
        """
        Retrieve some messages from the account associated with this
        grabber.
        """
        try:
            if not self.paused:
                try:
                    self.grab()
                except:
                    log.err(None, "Failure in scheduled event")
        finally:
            # XXX This is not a good way for things to work.  Different, later.
            delay = datetime.timedelta(seconds=300)
            self.scheduled = extime.Time() + delay
            return self.scheduled


    def _grabberID(self):
        if self.ssl and self.port == 995 or not self.ssl and self.port == 110:
            port = 'default'
        else:
            port = self.port

        return '%s@%s:%s' % (self.username, self.domain, port)
    grabberID = property(_grabberID)


    def shouldRetrieve(self, uidList):
        """
        Return a list of (index, uid) pairs from C{uidList} which have not
        already been grabbed.
        """
        if self._pop3uids is None:
            before = time.time()
            # Load all the POP3 UIDs at once and put them in a set for
            # super-fast lookup later.
            self._pop3uids = set(self.store.query(POP3UID, POP3UID.grabberID == self.grabberID).getColumn("value"))
            after = time.time()
            log.msg(interface=iaxiom.IStatEvent, stat_pop3uid_load_time=after - before)
        log.msg(interface=iaxiom.IStatEvent, stat_pop3uid_check=len(uidList))
        return [pair for pair in uidList if pair[1] not in self._pop3uids]


    def markSuccess(self, uid, msg):
        """
        Mark the retrieval of a message as successful with a particular UID.

        This grabber will no longer retrieve the message with that UID from the
        server.

        Archive that message if its sent date indicates it was sent more than
        one day before this grabber was created.

        @param uid: a POP3 UID specified by the server
        @type uid: L{str}

        @param msg: a L{xquotient.exmess.Message} which corresponds to that
        UID.

        @return: None
        """
        if msg.sentWhen + datetime.timedelta(days=1) < self.created:
            msg.archive()
        log.msg(interface=iaxiom.IStatEvent, stat_messages_grabbed=1,
                userstore=self.store)
        POP3UID(store=self.store, grabberID=self.grabberID, value=uid)
        if self._pop3uids is not None:
            self._pop3uids.add(uid)


    def markFailure(self, uid, err):
        POP3UID(store=self.store, grabberID=self.grabberID, value=uid, failed=True)
        if self._pop3uids is not None:
            self._pop3uids.add(uid)



class POP3GrabberProtocol(pop3.AdvancedPOP3Client):
    _rate = 50
    _delay = 2.0

    # An hour without bytes from the server and we'll just give up.  The exact
    # duration is arbitrary.  It is intended to be long enough to deal with
    # really slow servers or really big mailboxes or some combination of the
    # two, but still short enough so that if something actually hangs we won't
    # be stuck on it for long enough so as to upset the user.  This is probably
    # an insufficient solution to the problem of hung SSL connections, which is
    # the problem it is primarily targetted at solving.
    timeout = (60 * 60)

    def timeoutConnection(self):
        """
        Idle timeout expired while waiting for some bytes from the server.
        Disassociate the protocol object from the POP3Grabber and drop the
        connection.
        """
        addr, peer = self.transport.getHost(), self.transport.getPeer()
        log.msg("POP3GrabberProtocol/%s->%s timed out" % (addr, peer))
        self.transientFailure(failure.Failure(
            error.TimeoutError("Timed out waiting for server response.")))
        self.stoppedRunning()
        self.transport.loseConnection()


    def setCredentials(self, username, password):
        self._username = username
        self._password = password


    def _consumerFactory(self, msg):
        def consume(line):
            msg.lineReceived(line)
        return consume


    def serverGreeting(self, status):
        def ebGrab(err):
            log.err(err, "Failure while grabbing")
            self.setStatus(u'Internal error: ' + unicode(err.getErrorMessage()))
            self.transport.loseConnection()
        return self._grab().addErrback(ebGrab)


    def _grab(self):
        source = self.getSource()

        d = defer.waitForDeferred(self.login(self._username, self._password))
        self.setStatus(u"Logging in...")
        yield d
        try:
            d.getResult()
        except pop3client.ServerErrorResponse, e:
            self.setStatus(
                u'Login failed: ' + str(e).decode('ascii', 'replace'),
                False)
            self.transport.loseConnection()
            return
        except pop3.InsecureAuthenticationDisallowed:
            self.setStatus(
                u'Login aborted: server not secure.',
                False)
            self.transport.loseConnection()
            return
        except (error.ConnectionDone, error.ConnectionLost):
            self.setStatus(u"Connection lost", False)
            return
        except:
            f = failure.Failure()
            log.err(f, "Failure logging in")
            self.setStatus(
                u'Login failed: internal error.',
                False)
            self.transport.loseConnection()
            return


        N = 100

        # Up to N (index, uid) pairs which have been received but not
        # checked against shouldRetrieve
        uidWorkingSet = []

        # All the (index, uid) pairs which should be retrieved
        uidList = []

        # Consumer for listUID - adds to the working set and processes
        # a batch if appropriate.
        def consumeUIDLine(ent):
            uidWorkingSet.append(ent)
            if len(uidWorkingSet) >= N:
                processBatch()

        def processBatch():
            L = self.shouldRetrieve(uidWorkingSet)
            L.sort()
            uidList.extend(L)
            del uidWorkingSet[:]


        d = defer.waitForDeferred(self.listUID(consumeUIDLine))
        self.setStatus(u"Retrieving message list...")
        yield d
        try:
            d.getResult()
        except (error.ConnectionDone, error.ConnectionLost):
            self.setStatus(u"Connection lost", False)
            return
        except:
            f = failure.Failure()
            log.err(f, "Failure retrieving UIDL")
            self.setStatus(unicode(f.getErrorMessage()), False)
            self.transport.loseConnection()
            return

        # Clean up any stragglers.
        if uidWorkingSet:
            processBatch()

        log.msg(
            '%s: Retrieving %d messages.' % (self.getSource(),
                                             len(uidList)))

        # XXX This is a bad loop.
        for idx, uid in uidList:
            if self.stopped:
                return
            if self.paused():
                break

            rece = self.createMIMEReceiver(source)
            if rece is None:
                return # ONO
            d = defer.waitForDeferred(self.retrieve(idx, self._consumerFactory(rece)))
            self.setStatus(u"Downloading %d of %d" % (idx, uidList[-1][0]))
            yield d
            try:
                d.getResult()
            except (error.ConnectionDone, error.ConnectionLost):
                self.setStatus(unicode(u"Connection lost"), False)
                return
            except:
                f = failure.Failure()
                rece.connectionLost()
                self.markFailure(uid, f)
                if f.check(pop3client.LineTooLong):
                    # reschedule, the connection has dropped
                    self.transientFailure(f)
                    break
                else:
                    log.err(f, "Failure retrieving message")
            else:
                try:
                    rece.eomReceived()
                except:
                    # message could not be delivered.
                    f = failure.Failure()
                    log.err(f, "Failure delivering message")
                    self.markFailure(uid, f)
                else:
                    self.markSuccess(uid, rece.message)

        self.setStatus(u"Logging out...")
        d = defer.waitForDeferred(self.quit())
        yield d
        try:
            d.getResult()
        except (error.ConnectionDone, error.ConnectionLost):
            self.setStatus(u"idle")
        except:
            f = failure.Failure()
            log.err(f, "Failure quitting")
            self.setStatus(unicode(f.getErrorMessage()), False)
        else:
            self.setStatus(u"idle")
        self.transport.loseConnection()
    _grab = defer.deferredGenerator(_grab)


    def connectionLost(self, reason):
        # XXX change status here - maybe?
        pop3.AdvancedPOP3Client.connectionLost(self, reason)
        self.stoppedRunning()


    stopped = False
    def stop(self):
        self.stopped = True



class ControlledPOP3GrabberProtocol(POP3GrabberProtocol):
    def _transact(self, *a, **kw):
        return self.grabber.store.transact(*a, **kw)


    def getSource(self):
        return u'pop3://' + self.grabber.grabberID


    def setStatus(self, msg, success=True):
        self._transact(self.grabber.status.setStatus, msg, success)


    def shouldRetrieve(self, uidList):
        if self.grabber is not None:
            return self._transact(self.grabber.shouldRetrieve, uidList)


    def createMIMEReceiver(self, source):
        if self.grabber is not None:
            def createIt():
                agent = self.grabber.config.deliveryAgent
                return agent.createMIMEReceiver(source)
            return self._transact(createIt)


    def markSuccess(self, uid, msg):
        if self.grabber is not None:
            return self._transact(self.grabber.markSuccess, uid, msg)


    def markFailure(self, uid, reason):
        if self.grabber is not None:
            return self._transact(self.grabber.markFailure, uid, reason)


    def paused(self):
        if self.grabber is not None:
            return self.grabber.paused


    _transient = False
    def transientFailure(self, f):
        self._transient = True


    def stoppedRunning(self):
        if self.grabber is None:
            return
        self.grabber.running = False
        if self._transient:
            self.grabber.config.scheduler.reschedule(
                self.grabber,
                self.grabber.scheduled,
                extime.Time())
        self.grabber = None



class POP3GrabberFactory(protocol.ClientFactory):
    protocol = ControlledPOP3GrabberProtocol

    def __init__(self, grabber, ssl):
        self.grabber = grabber
        self.ssl = ssl


    def clientConnectionFailed(self, connector, reason):
        self.grabber.status.setStatus(u"Connection failed: " + reason.getErrorMessage())
        self.grabber.running = False
        self.grabber.protocol = None


    def buildProtocol(self, addr):
        self.grabber.status.setStatus(u"Connection established...")
        p = protocol.ClientFactory.buildProtocol(self, addr)
        if self.ssl:
            p.allowInsecureLogin = True
        p.setCredentials(
            self.grabber.username.encode('ascii'),
            self.grabber.password.encode('ascii'))
        p.grabber = self.grabber
        self.grabber.protocol = p
        return p



# This might be useful when we get an IMAP grabber online.

# grabberTypes = {
#     'POP3': POP3Grabber,
#     }


class GrabberConfigFragment(athena.LiveFragment):
    fragmentName = 'grabber-configuration'
    live = 'athena'
    jsClass = u'Quotient.Grabber.Controller'
    title = 'Incoming'

    def head(self):
        return ()

    def render_addGrabberForm(self, ctx, data):
        f = liveform.LiveForm(
            self.addGrabber,
            [liveform.Parameter('domain',
                                liveform.TEXT_INPUT,
                                unicode,
                                u'Domain',
                                u'The domain which hosts the account.'),
             liveform.Parameter('username',
                                liveform.TEXT_INPUT,
                                unicode,
                                u'Username',
                                u'The username portion of the address from which to retrieve messages.'),
             liveform.Parameter('password1',
                                liveform.PASSWORD_INPUT,
                                unicode,
                                u'Password',
                                u'The password for the remote account.'),
             liveform.Parameter('password2',
                                liveform.PASSWORD_INPUT,
                                unicode,
                                u'Repeat Password'),
# Along with the above, this might be useful if we had an IMAP grabber.
#              liveform.Parameter('protocol',
#                                 liveform.Choice(grabberTypes.keys()),
#                                 lambda value: grabberTypes[value],
#                                 u'Super secret computer science stuff',
#                                 'POP3'),
             liveform.Parameter('ssl',
                                liveform.CHECKBOX_INPUT,
                                bool,
                                u'Use SSL to fetch messages')],
             description='Add Grabber')
        f.jsClass = u'Quotient.Grabber.AddGrabberFormWidget'
        f.setFragmentParent(self)
        f.docFactory = webtheme.getLoader('liveform-compact')
        return ctx.tag[f]

    wt = None
    def getEditGrabberForm(self, targetID):
        if self.wt is None:
            self.wt = self.original.privateApplication

        grabber = self.wt.fromWebID(targetID)

        f = liveform.LiveForm(
                lambda **kwargs: self.editGrabber(grabber, **kwargs),
                (liveform.Parameter('password1',
                                    liveform.PASSWORD_INPUT,
                                    unicode,
                                    u'New Password'),
                liveform.Parameter('password2',
                                   liveform.PASSWORD_INPUT,
                                   unicode,
                                   u'Repeat Password'),
                liveform.Parameter('ssl',
                                   liveform.CHECKBOX_INPUT,
                                   bool,
                                   'Use SSL',
                                   default=grabber.ssl)),
                description='Edit Grabber')

        grabber.grab()
        f.setFragmentParent(self)
        return unicode(flatten(f), 'utf-8')
    expose(getEditGrabberForm)

    def editGrabber(self, grabber, password1, password2, ssl):
        if password1 != password2:
            raise ValueError("Passwords don't match")

        if ssl != grabber.ssl:
            if ssl:
                port = 995
            else:
                port = 110
            grabber.port = port
            grabber.ssl = ssl

        if password1 and password2:
            grabber.password = password1

        self.callRemote('hideEditForm')
        return u'Well Done'

    def addGrabber(self, domain, username, password1, password2, ssl):
        if password1 != password2:
            raise ValueError("Passwords don't match")
        self.original.addGrabber(username, password1, domain, ssl)


    def render_POP3Grabbers(self, ctx, data):
        self.configuredGrabbersView = ConfiguredGrabbersView(self.original.store)
        self.configuredGrabbersView.setFragmentParent(self)
        return self.configuredGrabbersView

components.registerAdapter(GrabberConfigFragment, GrabberConfiguration, ixmantissa.INavigableFragment)



class LiveStatusFragment(athena.LiveFragment):
    docFactory = loaders.stan(tags.span(render=tags.directive('liveFragment')))
    jsClass = u'Quotient.Grabber.StatusWidget'
    _pending = False
    _pendingStatus = None

    def __init__(self, status):
        self.status = status


    def statusChanged(self, newStatus):
        if self._pending:
            self._pendingStatus = newStatus
        else:
            self._pending = True
            self.callRemote('setStatus', newStatus).addCallback(self._unpend)


    def _unpend(self, ign):
        pendingStatus = self._pendingStatus
        self._pendingStatus = None
        self._pending = False
        if pendingStatus is not None:
            self.statusChanged(pendingStatus)


    def startObserving(self):
        self.removeObserver = self.status.addChangeObserver(self.statusChanged)
        return self.status.message
    expose(startObserving)



class StatusColumn(AttributeColumn):
    def __init__(self, attribute, fragment):
        super(StatusColumn, self).__init__(attribute)
        self.fragment = fragment

    def extractValue(self, model, item):
        f = LiveStatusFragment(item.status)
        f.setFragmentParent(self.fragment)
        return unicode(flatten(f), 'utf-8')

    def getType(self):
        return TYPE_FRAGMENT



class ConfiguredGrabbersView(ScrollingFragment):
    jsClass = u'Quotient.Grabber.ScrollingWidget'

    def __init__(self, store):
        ScrollingFragment.__init__(self, store, POP3Grabber, None,
                                   [POP3Grabber.username,
                                    POP3Grabber.domain,
                                    POP3Grabber.paused,
                                    StatusColumn(POP3Grabber.status, self)])

        self.docFactory = webtheme.getLoader(self.fragmentName)

    def action_delete(self, grabber):
        grabber.delete()

    def action_pause(self, grabber):
        grabber.paused = True

    def action_resume(self, grabber):
        grabber.paused = False
