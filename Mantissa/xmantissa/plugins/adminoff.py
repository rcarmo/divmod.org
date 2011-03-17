
from xmantissa import offering, stats
from xmantissa.webadmin import (TracebackViewer, LocalUserBrowser,
                                DeveloperApplication,
                                PortConfiguration)
from xmantissa.signup import SignupConfiguration

adminOffering = offering.Offering(
    name = u'mantissa',
    description = u'Powerups for administrative control of a Mantissa server.',
    siteRequirements = [],
    appPowerups = [stats.StatsService],
    installablePowerups = [("Signup Configuration", "Allows configuration of signup mechanisms", SignupConfiguration),
                           ("Traceback Viewer", "Allows viewing unhandled exceptions which occur on the server", TracebackViewer),
                           ("Port Configuration", "Allows manipulation of network service configuration.", PortConfiguration),
                           ("Local User Browser", "A page listing all users existing in this site's store.", LocalUserBrowser),
                           ("Admin REPL", "An interactive python prompt.", DeveloperApplication),
                           ("Offering Configuration", "Allows installation of Offerings on this site", offering.OfferingConfiguration),
                           ("Stats Observation", "Allows remote observation via AMP of gathered performance-related stats",
                            stats.RemoteStatsCollectorFactory),
                           ],
    loginInterfaces=(),
    themes = ())
