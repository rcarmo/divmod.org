import sha

from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from nevow.inevow import IRequest
from nevow.context import WovenContext
from nevow.testutil import FakeRequest

from xmantissa.cachejs import HashedJSModuleProvider, CachedJSModule


class JSCachingTestCase(TestCase):
    """
    Tests for L{xmantissa.cachejs}.
    """
    hostname = 'test-mantissa-js-caching.example.com'

    def setUp(self):
        """
        Create a L{HashedJSModuleProvider} and a dummy module.
        """
        self.MODULE_NAME = 'Dummy.Module'
        self.MODULE_CONTENT = '/* Hello, world. /*\n'
        self.moduleFile = self.mktemp()
        fObj = file(self.moduleFile, 'w')
        fObj.write(self.MODULE_CONTENT)
        fObj.close()
        m = HashedJSModuleProvider()
        self.moduleProvider = m
        self._wasModified = CachedJSModule.wasModified.im_func
        self.callsToWasModified = 0
        def countCalls(other):
            self.callsToWasModified += 1
            return self._wasModified(other)
        CachedJSModule.wasModified = countCalls


    def tearDown(self):
        """
        put L{CachedJSModule} back the way we found it
        """
        CachedJSModule.wasModified = self._wasModified


    def _render(self, resource):
        """
        Test helper which tries to render the given resource.
        """
        ctx = WovenContext()
        req = FakeRequest(headers={'host': self.hostname})
        ctx.remember(req, IRequest)
        return req, resource.renderHTTP(ctx)


    def test_hashExpiry(self):
        """
        L{HashedJSModuleProvider.resourceFactory} should return a L{static.Data}
        with an C{expires} value far in the future.
        """
        self.moduleProvider.moduleCache[self.MODULE_NAME] = CachedJSModule(
            self.MODULE_NAME, FilePath(self.moduleFile))
        d, segs = self.moduleProvider.locateChild(None,
                                     [sha.new(self.MODULE_CONTENT).hexdigest(),
                                      self.MODULE_NAME])
        self.assertEqual([], segs)
        d.time = lambda: 12345
        req, result = self._render(d)
        self.assertEquals(
            req.headers['expires'],
            'Tue, 31 Dec 1974 03:25:45 GMT')
        self.assertEquals(
            result,
            '/* Hello, world. /*\n')


    def test_getModule(self):
        """
        L{HashedJSModuleProvider.getModule} should only load modules once;
        subsequent calls should return the cached module object.
        """
        module = self.moduleProvider.getModule("Mantissa.Test.Dummy")
        self.failUnlessIdentical(module, self.moduleProvider.getModule(
            "Mantissa.Test.Dummy"))


    def test_dontStat(self):
        """
        L{HashedJSModuleProvider.getModule} shouldn't hit the disk more than
        once per module.
        """
        module1 = self.moduleProvider.getModule("Mantissa.Test.Dummy")
        module2 = self.moduleProvider.getModule("Mantissa.Test.Dummy")
        self.assertEqual(self.callsToWasModified, 1)
