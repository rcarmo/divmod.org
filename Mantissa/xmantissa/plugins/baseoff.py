
from twisted.python.filepath import FilePath
from twisted.protocols.amp import IBoxReceiver
from twisted.conch.interfaces import IConchUser

from nevow.inevow import IResource

from xmantissa.ixmantissa import ISiteURLGenerator
from xmantissa import offering
from xmantissa.web import SiteConfiguration
from xmantissa.webtheme import MantissaTheme
from xmantissa.publicweb import AnonymousSite
from xmantissa.ampserver import AMPConfiguration, AMPAvatar, EchoFactory
from xmantissa.terminal import SecureShellConfiguration
import xmantissa

baseOffering = offering.Offering(
    name=u'mantissa-base',
    description=u'Basic Mantissa functionality',
    siteRequirements=[
        (ISiteURLGenerator, SiteConfiguration),
        (IResource, AnonymousSite),
        (None, SecureShellConfiguration)],
    appPowerups=(),
    installablePowerups=(),
    loginInterfaces = [
        (IResource, "HTTP logins"),
        (IConchUser, "SSH logins")],
    # priority should be 0 for pretty much any other theme.  'base' is the theme
    # that all other themes should use as a reference for what elements are
    # required.
    themes=(MantissaTheme('base', 1),),
    staticContentPath=FilePath(xmantissa.__file__).sibling('static'),
    version=xmantissa.version)

# XXX This should be part of baseOffering, but because there is no
# functionality for upgrading installed offering state, doing so would create a
# class of databases which thought they had amp installed but didn't really.
# See #2723.
ampOffering = offering.Offering(
    name=u'mantissa-amp',
    description=u'Extra AMP-related Mantissa functionality',
    siteRequirements=[
        (None, AMPConfiguration),
        ],
    appPowerups=[],
    installablePowerups=[
        ("AMP Access", "Allows logins over AMP", AMPAvatar),
        ("AMP Echo Protocol",
         "Dead-simple AMP echoer, potentially useful for testing connections "
         "to a Mantissa AMP server or otherwise providing an example of the "
         "AMP functionality.",
         EchoFactory),
        ],
    loginInterfaces=[
        (IBoxReceiver, "AMP logins"),
        ],
    themes=[],
    staticContentPath=None,
    version=xmantissa.version)
