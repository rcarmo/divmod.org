
from datetime import timedelta

from epsilon.extime import Time

from nevow.page import renderer
from nevow.loaders import stan
from nevow.tags import div
from nevow.athena import LiveElement

from xmantissa.liveform import TEXT_INPUT, LiveForm, Parameter


class CalendarElement(LiveElement):

    docFactory = stan(div[
            "It's a calendar!",
            div(render="appointments"),
            div(render="appointmentForm")])

    def __init__(self, calendar):
        LiveElement.__init__(self)
        self.calendar = calendar


    @renderer
    def appointments(self, request, tag):
        appointments = self.calendar.getAppointments()
        for appointment in appointments:
            appDiv = div[
                "Appointment with ",
                appointment.withWhomUsername, "@",
                appointment.withWhomDomain, " at ",
                appointment.when.asHumanly()]
            if appointment.failed is not None:
                appDiv[" (Rejected: ", appointment.failed, ")"]
            elif appointment.remoteID is None:
                appDiv[" (Pending confirmation)"]
            tag[appDiv]
        return tag


    def _requestAppointment(self, whom):
        local, domain = whom.split(u"@")
        target = self.calendar.calendarIDFor(local, domain)
        self.calendar.requestAppointmentWith(target, Time() + timedelta(days=2))


    @renderer
    def appointmentForm(self, request, tag):
        form = LiveForm(
            self._requestAppointment,
            [Parameter(u"whom", TEXT_INPUT, unicode, u"Whom:",
                       u"The username of the person with whom "
                       u"to create an appointment (user@domain).",
                       None)],
            "Request An Appointment")
        form.setFragmentParent(self)
        return form


