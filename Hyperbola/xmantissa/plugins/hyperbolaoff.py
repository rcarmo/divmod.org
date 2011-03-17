
"""
This module is a plugin for Mantissa which provides a Hyperbola offering.
"""

from twisted.python.filepath import FilePath

from axiom import userbase

from xmantissa import website, offering

from hyperbola import hyperbola_model
from hyperbola.hyperbola_theme import HyperbolaTheme
from hyperbola.publicpage import HyperbolaPublicPage
import hyperbola

plugin = offering.Offering(
    name = u"Hyperbola",

    description = u"""
    A basic weblog system.
    """,

    siteRequirements = [
        (userbase.IRealm, userbase.LoginSystem),
        (None, website.WebSite)],
    appPowerups = (),
    installablePowerups = [(
        u'Publisher',
        u'Allows publishing of posts in a weblog format.',
        hyperbola_model.HyperbolaPublicPresence)],
    loginInterfaces = (),
    themes = [HyperbolaTheme('base', 0)],
    version = hyperbola.version,
    staticContentPath = FilePath(hyperbola.__file__).sibling('static'))
