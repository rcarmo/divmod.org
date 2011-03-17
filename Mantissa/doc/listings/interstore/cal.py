# Copyright (c) 2009 Divmod.  See LICENSE for details.

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.protocols.amp import Command, String, Unicode

from epsilon.extime import Time

from axiom.item import Item
from axiom.attributes import text, timestamp
from axiom.userbase import getAccountNames
from axiom.dependency import dependsOn

from xmantissa.ixmantissa import IMessageReceiver, INavigableElement, INavigableFragment
from xmantissa.sharing import Identifier, getEveryoneRole, getPrimaryRole
from xmantissa.interstore import DELIVERY_ERROR, ERROR_NO_USER, ERROR_NO_SHARE, ERROR_BAD_SENDER, ERROR_REMOTE_EXCEPTION
from xmantissa.interstore import MessageQueue, AMPMessenger, AMPReceiver, commandMethod, answerMethod, errorMethod
from xmantissa.interstore import SenderArgument
from xmantissa.webnav import Tab
from xmantissa.webapp import PrivateApplication

from webcal import CalendarElement


CALENDAR_SHARE_ID = u"exampleapp.root.calendar"

class Busy(Exception):
    pass


class MakeAppointment(Command):
    arguments = [("whom", SenderArgument()), ("when", String())]
    response = [("appointmentID", Unicode())]
    errors = {"busy": Busy}


class Appointment(Item, AMPReceiver):

    # It would be nice to roll up these three, see #2685.
    withWhomShareID = text(allowNone=False)
    withWhomUsername = text(allowNone=False)
    withWhomDomain = text(allowNone=False)

    when = timestamp(allowNone=False)
    remoteID = text(default=None)
    failed = text(default=None)

    # This really shouldn't be the way to handle these error cases.  See
    # #2896.
    def answerReceived(self, value, *args, **kwargs):
        if value.type == DELIVERY_ERROR:
            if value.data == ERROR_NO_USER:
                self.failed = u"No such user."
            elif value.data == ERROR_NO_SHARE:
                self.failed = u"That person does not have a calendar."
            elif value.data == ERROR_BAD_SENDER:
                self.failed = u"Programming error (bad sender)"
            elif value.data == ERROR_REMOTE_EXCEPTION:
                self.failed = u"Programming error (remote exception)"
            else:
                self.failed = u"Unknown error (%s)" % (value.data,)
        else:
            AMPReceiver.answerReceived(self, value, *args, **kwargs)


    @answerMethod.expose(MakeAppointment)
    def appointmentMade(self, appointmentID):
        self.remoteID = appointmentID
        print 'Appointment made'


    @errorMethod.expose(MakeAppointment, Busy)
    def appointmentFailed(self, failure):
        self.failed = u"Appointment not made, too busy."



class Calendar(Item, AMPReceiver):
    powerupInterfaces = (IMessageReceiver, INavigableElement)
    implements(*powerupInterfaces)

    messageQueue = dependsOn(MessageQueue)

    # Possibly inappropriate.  See #2573.
    privateApplication = dependsOn(PrivateApplication)

    def installed(self):
        getEveryoneRole(self.store).shareItem(self, CALENDAR_SHARE_ID, [IMessageReceiver])


    @commandMethod.expose(MakeAppointment)
    def peerRequestedAppointment(self, whom, when):
        app = Appointment(
            store=self.store, when=Time.fromISO8601TimeAndDate(when),
            withWhomUsername=whom.localpart, withWhomDomain=whom.domain,
            withWhomShareID=whom.shareID, remoteID=whom.shareID)
        role = getPrimaryRole(self.store, u"%s@%s" % (whom.localpart, whom.domain), True)
        appointmentID = role.shareItem(app, interfaces=[IMessageReceiver]).shareID
        return {'appointmentID': appointmentID}


    def requestAppointmentWith(self, whom, when):
        appointment = Appointment(
            store=self.store, when=when, withWhomShareID=whom.shareID,
            withWhomUsername=whom.localpart, withWhomDomain=whom.domain)
        role = getPrimaryRole(self.store, u"%s@%s" % (whom.localpart, whom.domain), True)
        appointmentID = role.shareItem(appointment, interfaces=[IMessageReceiver]).shareID

        messenger = AMPMessenger(
            self.messageQueue,
            Identifier(appointmentID, *getAccountNames(self.store).next()),
            whom)
        messenger.messageRemote(
            MakeAppointment, appointment, when=when.asISO8601TimeAndDate())


    def calendarIDFor(self, local, domain):
        return Identifier(CALENDAR_SHARE_ID, local, domain)


    def getAppointments(self):
        return self.store.query(Appointment)


    def getTabs(self):
        return [Tab("Calendar", self.storeID, 1.0)]



registerAdapter(CalendarElement, Calendar, INavigableFragment)
