from twisted.python import filepath
from nevow import athena

import xquotient
quotient = athena.AutoJSPackage(filepath.FilePath(xquotient.__file__).parent().child('js').path)
