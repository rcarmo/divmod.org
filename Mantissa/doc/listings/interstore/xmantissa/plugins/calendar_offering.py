
from xmantissa.offering import Offering

from cal import Calendar

calendarOffering = Offering(
    name=u"Calendar",
    description=u"A simple appointment-tracking application.",
    siteRequirements=[],
    appPowerups=[],
    installablePowerups=[(u"Calendar", u"Appointment Tracking Powerup", Calendar)],
    loginInterfaces=[],
    themes=[],
    staticContentPath=None,
    version=None)
