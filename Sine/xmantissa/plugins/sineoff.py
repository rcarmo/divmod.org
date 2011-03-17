
from twisted.python.filepath import FilePath

from axiom import userbase

from xmantissa import website, offering

import sine
from sine import sipserver, sinetheme
from sine.voicemail import VoicemailDispatcher

plugin = offering.Offering(
    name = u"Sine",

    description = u"""
    The Sine SIP proxy and registrar.
    """,

    siteRequirements = (
        (userbase.IRealm, userbase.LoginSystem),
        (None, website.WebSite),
        (None, sipserver.SIPServer)),

    appPowerups = (),
    installablePowerups = [("SIP", "Gives user a SIP URL and the ability to send and receive calls through a SIP proxy",
                            sipserver.TrivialContact),
                           ("Voicemail", "Records voicemail for calls to user's SIP URL when no user agent is registered.",
                            VoicemailDispatcher)],
    loginInterfaces=(),
    themes = (sinetheme.SineTheme('base'),),
    staticContentPath=FilePath(sine.__file__).sibling('static'))
