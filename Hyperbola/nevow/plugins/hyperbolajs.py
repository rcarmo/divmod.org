
from twisted.python import filepath

from nevow import athena

import hyperbola

hyperbolaJS = athena.AutoJSPackage(filepath.FilePath(hyperbola.__file__).parent().child('js').path)
