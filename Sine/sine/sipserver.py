import time

from zope.interface import implements

from twisted.python.util import sibpath
from twisted.internet import reactor, defer
from twisted.python.components import registerAdapter
from twisted.application.service import IService, Service
from twisted.cred.portal import Portal

from nevow import athena, tags

from epsilon.extime import Time

from axiom import userbase, batch
from axiom.attributes import integer, inmemory, bytes, text, reference, timestamp
from axiom.item import Item, declareLegacyItem
from axiom.errors import NoSuchUser
from axiom.userbase import LoginSystem
from axiom.dependency import dependsOn
from axiom.upgrade import registerUpgrader

from xmantissa import ixmantissa, liveform
from xmantissa import webnav, tdb, tdbview
from xmantissa.webtheme import getLoader

import sine
from sine import sip, useragent, tpcc


class SIPConfigurationError(RuntimeError):
    """You specified some invalid configuration."""


def getHostnames(store):
    """
    Like L{axiom.userbase.getDomainNames}, but also default to just
    C{['localhost']} if there are no domains.
    """
    return userbase.getDomainNames(store) or ['localhost']


class SIPServer(Item, Service):
    typeName = 'mantissa_sip_powerup'
    schemaVersion = 3
    portno = integer(default=5060)
    pstn = bytes()
    parent = inmemory()
    running = inmemory()
    name = inmemory()

    proxy = inmemory()
    dispatcher = inmemory()
    mediaController = inmemory()
    port = inmemory()
    site = inmemory()
    transport = inmemory()

    userbase = dependsOn(LoginSystem)

    powerupInterfaces = (IService,)

    def installed(self):
        self.setServiceParent(self.store)

    def startService(self):
        tacPath = sibpath(sine.__file__, "media.tac")
        self.mediaController = batch.ProcessController(
            "rtp-transceiver",
            useragent.LocalControlProtocol(False),
            tacPath=tacPath)

        if self.pstn:
            pstnurl = sip.parseURL(self.pstn)
            portal = PSTNPortalWrapper(Portal(self.userbase, [self.userbase]), pstnurl.host, pstnurl.port)
        else:
            portal = Portal(self.userbase, [self.userbase])
        self.proxy = sip.Proxy(portal)
        self.dispatcher = sip.SIPDispatcher(portal, self.proxy)
        regs = list(self.store.query(Registration, Registration.parent==self))
        if regs:
            rc = sip.RegistrationClient()
            self.proxy.installRegistrationClient(rc)
            for reg in regs:
                if not (reg.username and reg.domain):
                    raise SIPConfigurationError("Bad registration URL:", "You need both a username and a domain to register")
                rc.register(reg.username, reg.password, reg.domain)
                self.proxy.addProxyAuthentication(reg.username, reg.domain, reg.password)
        self.transport = sip.SIPTransport(self.dispatcher, getHostnames(self.store), self.portno)
        self.port = reactor.listenUDP(self.portno, self.transport)


    def setupCallBetween(self, partyA, partyB):
        """
        Set up a call between party A and party B, and control the
        signalling for the call.  Either URL may refer to any SIP
        address, there is no requirement that either participant be
        registered with this proxy.

        @param partyA: a SIP address (a three-tuple of (name, URL,
        parameters)) that represents the party initiating the call,
        i.e. the SIP address of the user who is logged in to the web
        UI and pushing the button to place the call. (Specifically,
        this is the user who will be called first and will have to
        wait for the other user to pick up the call.)

        @param partyB: a SIP address that represents the party receiving
        the call.

        @return: None
        """
        # XXX TODO should probably return a deferred which
        # fires... something... that would let us take advantage of
        # the intermediary call signalling, such as ending the call
        # early...
        localpart = "clicktocall"
        host = getHostnames(self.store)[0]
        controller = tpcc.ThirdPartyCallController(self.dispatcher, localpart, host, self.mediaController, partyA[0], partyB[1])
        uac = useragent.UserAgent.client(controller, localpart, host, self.mediaController, self.dispatcher.dialogs)
        uac.transport = self.dispatcher.transport
        self.dispatcher.installTemporaryProcessor(sip.URL(host, localpart), uac)

        uac._doCall(partyA[1], fromName="Divmod")

def sipServer1to2(old):
    ss = old.upgradeVersion(old.typeName, 1, 2)
    ss.portno = old.portno
    ss.pstn = old.pstn
    ss.userbase = old.store.findOrCreate(LoginSystem)
    return ss

registerUpgrader(sipServer1to2, SIPServer.typeName, 1, 2)

declareLegacyItem(
    SIPServer.typeName, 2,
    dict(portno=integer(),
         pstn=bytes(),
         scheduler=reference(),
         userbase=reference()))

def sipServer2to3(old):
    ss = old.upgradeVersion(old.typeName, 2, 3)
    ss.portno = old.portno
    ss.pstn = old.pstn
    ss.userbase = old.userbase
    return ss

registerUpgrader(sipServer2to3, SIPServer.typeName, 2, 3)

class Registration(Item):
    typename = "sine_registration"
    schemaVersion = 1
    parent = reference()
    username = text()
    domain = text()
    password = text()

class ListenToRecordingAction(tdbview.Action):
    def __init__(self):
        tdbview.Action.__init__(self, 'listen',
                            '/static/Sine/images/listen.png',
                            'Listen to this recording')
    def toLinkStan(self, idx, item):
            return tags.a(href='/' + item.prefixURL)[
                tags.img(src=self.iconURL, border=0)]

    def performOn(self, recording):
        raise NotImplementedError()

    def actionable(self, thing):
        return True

class SinePublicPage(Item):
    """
    Needed for schema compatibility only.
    """
    typeName = 'sine_public_page'
    schemaVersion = 1

    installedOn = reference()



class SineBenefactor(Item):
    """
    Needed for schema compatibility only.
    """
    typeName = 'sine_benefactor'
    schemaVersion = 1
    domain=text()
    endowed = integer(default = 0)

class PSTNContact:
    implements(sip.IContact)
    def __init__(self, avatarId, targethost, targetport):
        self.id = avatarId
        self.targetport = targetport
        self.targethost = targethost

    def getRegistrationInfo(self, caller):
        return [(sip.URL(self.targethost, port=self.targetport, username=self.id), 0)]

    def callIncoming(self, name, uri, caller):
        if caller is None:
            # ta da
            raise sip.SIPError(401)

    def registerAddress(self, *args):
        from twisted.cred.error import UnauthorizedLogin
        raise UnauthorizedLogin

    def incompleteImplementation(self, *args, **kw):
        raise NotImplementedError("Asterisk PSTN numbers are NOT general-purpose IContacts!")

    unregisterAddress = incompleteImplementation
    callOutgoing = incompleteImplementation



class PSTNPortalWrapper:

    def __init__(self, realPortal, targetHost, targetPort):
        self.realPortal = realPortal
        self.targethost = targetHost
        self.targetport = targetPort

    def login(self, credentials, mind, interface):
        D = self.realPortal.login(credentials, mind, interface)
        def logcb(thing):
            return thing
        def eb(fail):
            fail.trap(NoSuchUser)
            localpart = credentials.username.split('@')[0]
            if interface == sip.IContact and localpart.isdigit():
                return (interface, PSTNContact(localpart, self.targethost, self.targetport), lambda: None)
            else:
                return fail
        D.addCallback(logcb)
        D.addErrback(eb)
        return D



class TrivialContact(Item):
    implements(sip.IContact, ixmantissa.INavigableElement)

    typeName = "sine_trivialcontact"
    schemaVersion = 1

    physicalURL = bytes()
    altcontact = bytes()
    expiryTime = timestamp()
    installedOn = reference()

    powerupInterfaces = (ixmantissa.INavigableElement, sip.IContact)

    def registerAddress(self, physicalURL, expiryTime):
        self.physicalURL = physicalURL.toString()
        self.expiryTime = Time.fromPOSIXTimestamp(time.time() + expiryTime)
        return [(physicalURL, self.expiryTime)]

    def unregisterAddress(self, physicalURL):
        storedURL = sip.parseURL(self.physicalURL)
        if storedURL != physicalURL:
            raise ValueError, "what"
        self.physicalURL = None
        return [(physicalURL, 0)]

    def getRegistrationInfo(self, caller):
        registered = False
        if self.physicalURL is not None:
            now = time.time()
            if now < self.expiryTime.asPOSIXTimestamp():
                registered = True
        if registered:
            return [(sip.parseURL(self.physicalURL), int(self.expiryTime.asPOSIXTimestamp() - now))]
        elif self.altcontact:
            return [(sip.parseURL(self.altcontact), -1)]
        else:
            return defer.fail(sip.RegistrationError(480))

    def placeCall(self, target):
        svc = self.store.parent.findUnique(SIPServer)
        svc.setupCallBetween(("", self.getRegistrationInfo(target)[0][0], {}),
                             ("", target, {}))

    def callIncoming(self, name, uri, caller):
        Call(store=self.store, name=name, time=Time(), uri=unicode(str(uri)), kind=u'from')

    def callOutgoing(self, name, uri):
        Call(store=self.store, name=name, time=Time(), uri=unicode(str(uri)), kind=u'to')

    def getTabs(self):
        return [webnav.Tab('Voice', self.storeID, 0.25)]



class TrivialContactFragment(athena.LiveFragment):
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'trivial-contact'
    live = 'athena'
    title = ''

    def data_physicalURL(self, ctx, data):
        return self.original.physicalURL or self.original.altcontact or 'Unregistered'

    def data_expiryTime(self, ctx, data):
        expiryTime = self.original.expiryTime
        if expiryTime is not None and expiryTime != -1:
            return expiryTime.asHumanly()
        return 'No Expiry'

    def render_callTDB(self, ctx, data):
        prefs = ixmantissa.IPreferenceAggregator(self.original.store)

        tdm = tdb.TabularDataModel(self.original.store,
                                   Call, (Call.time, Call.uri, Call.kind),
                                   itemsPerPage=prefs.getPreferenceValue('itemsPerPage'))

        cviews = (tdbview.DateColumnView('time'),
                  tdbview.ColumnViewBase('uri'),
                  tdbview.ColumnViewBase('kind'))

        tdv = tdbview.TabularDataView(tdm, cviews, width='100%')
        tdv.docFactory = getLoader(tdv.fragmentName)
        tdv.setFragmentParent(self)
        return tdv

    def render_voicemailTDB(self, ctx, data):
        from sine.confession import Recording
        prefs = ixmantissa.IPreferenceAggregator(self.original.store)

        tdm = tdb.TabularDataModel(self.original.store,
                                   Recording, (Recording.fromAddress, Recording.length, Recording.time),
                                   itemsPerPage=prefs.getPreferenceValue('itemsPerPage'))

        cviews = (tdbview.ColumnViewBase('fromAddress'),
                  tdbview.ColumnViewBase('length'),
                  tdbview.DateColumnView('time'))

        tdv = tdbview.TabularDataView(tdm, cviews,  (ListenToRecordingAction(),),width='100%')
        tdv.docFactory = getLoader(tdv.fragmentName)
        tdv.setFragmentParent(self)
        return tdv

    def render_altcontactForm(self, ctx, data):
        lf = liveform.LiveForm(self.setAltContact, [liveform.Parameter(
        "altcontact", liveform.TEXT_INPUT, self.parseURLorPhoneNum, "An alternate SIP URL or phone number to forward calls to when you are not registered", "")], "Set")
        lf.setFragmentParent(self)
        return lf

    def render_placeCall(self, ctx, data):
        lf = liveform.LiveForm(self.original.placeCall, [liveform.Parameter(
            "target", liveform.TEXT_INPUT, self.parseURLorPhoneNum, "Place call:")])
        lf.setFragmentParent(self)
        return lf

    def parseURLorPhoneNum(self, val):
        pstn = self.original.store.parent.findUnique(SIPServer).pstn
        if '@' in val:
            if not val.startswith("sip:"):
                val = "sip:" + val
            return sip.parseURL(val)
        elif pstn:
            pstnurl = sip.parseURL(pstn)
            num = ''.join([c for c in val if c.isdigit()])
            pstn = self.original.store.parent.findUnique(SIPServer).pstn
            if len(num) == 10:
                return sip.URL(host=pstnurl.host, username="1"+num, port=pstnurl.port)
            elif len(num) == 11 and num[0] == '1':
                return sip.URL(host=pstnurl.host, username=num, port=pstnurl.port)
            else:
                raise liveform.InvalidInput("Please enter a SIP URL or a North American ten-digit phone number.")
        else:
            raise liveform.InvalidInput("Please enter a SIP URL.")

    def setAltContact(self, altcontact):
        self.original.altcontact = str(altcontact)

    def head(self):
        return None

registerAdapter(TrivialContactFragment, TrivialContact, ixmantissa.INavigableFragment)



class SIPDispatcherService(Item, Service):
    typeName = 'sine_sipdispatcher_service'
    schemaVersion = 3
    portno = integer(default=5060)

    parent = inmemory()
    running = inmemory()
    name = inmemory()

    dispatcher = inmemory()
    proxy = inmemory()
    port = inmemory()
    site = inmemory()

    userbase = dependsOn(LoginSystem)

    powerupInterfaces = (IService,)


    def privilegedStartService(self):
        portal = Portal(self.userbase, [self.userbase])
        self.proxy = sip.Proxy(portal)
        self.dispatcher = sip.SIPDispatcher(portal, self.proxy)
        f = sip.SIPTransport(self.dispatcher, getHostnames(self.store), self.portno)
        self.port = reactor.listenUDP(self.portno, f)


def sipDispatcher1to2(old):
    ss = old.upgradeVersion(old.typeName, 1, 2)
    ss.portno = old.portno
    ss.userbase = old.store.findOrCreate(LoginSystem)
    return ss

registerUpgrader(sipDispatcher1to2, SIPDispatcherService.typeName, 1, 2)

declareLegacyItem(
    SIPDispatcherService.typeName, 2,
    dict(portno=integer(),
         scheduler=reference(),
         userbase=reference()))

def sipDispatcher2to3(old):
    return old.upgradeVersion(SIPDispatcherService.typeName, 2, 3,
                              portno=old.portno,
                              userbase=old.userbase)

registerUpgrader(sipDispatcher2to3, SIPDispatcherService.typeName, 2, 3)


class Call(Item):
    typeName = "sine_call"
    schemaVersion = 1
    name=text()
    uri = text()
    time = timestamp()
    kind = text()
