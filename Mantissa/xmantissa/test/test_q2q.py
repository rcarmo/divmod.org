
from twisted.trial import unittest

from axiom import store

from xmantissa import ixmantissa, endpoint

class MantissaQ2Q(unittest.TestCase):
    def testInstallation(self):
        d = self.mktemp()
        s = store.Store(unicode(d))
        q = endpoint.UniversalEndpointService(store=s)
        q.installOn(s)
        self.assertIdentical(ixmantissa.IQ2QService(s), q)
