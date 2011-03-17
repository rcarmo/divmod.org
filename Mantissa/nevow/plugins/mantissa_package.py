
from twisted.python import util

from nevow import athena

import xmantissa

mantissaPkg = athena.AutoJSPackage(util.sibpath(xmantissa.__file__, 'js'))
