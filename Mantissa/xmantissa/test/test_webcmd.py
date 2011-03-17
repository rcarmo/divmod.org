
import os, sys

from cStringIO import StringIO

from twisted.python.usage import UsageError
from twisted.trial.unittest import TestCase

from axiom.plugins import webcmd

from axiom.store import Store
from axiom.test.util import CommandStubMixin
from axiom.plugins.mantissacmd import Mantissa

from xmantissa.web import SiteConfiguration
from xmantissa.website import APIKey

def _captureStandardOutput(f, *a, **k):
    """
    Capture standard output produced during the invocation of a function, and
    return it.

    Since this is for testing command-line tools, SystemExit errors that
    indicate a successful return are caught.
    """
    io = StringIO()
    oldout = sys.stdout
    sys.stdout = io
    try:
        try:
            f(*a, **k)
        finally:
            sys.stdout = oldout
    except SystemExit, se:
        if se.args[0]:
            raise
    return io.getvalue()


class TestIdempotentListing(CommandStubMixin, TestCase):

    def setUp(self):
        self.store = Store()
        self.options = webcmd.WebConfiguration()
        self.options.parent = self


    def test_requiresBaseOffering(self):
        """
        L{WebConfiguration.postOptions} raises L{UsageError} if it is used on a
        store which does not have the Mantissa base offering installed.
        """
        self.assertRaises(UsageError, self.options.postOptions)


    def _list(self):
        wconf = webcmd.WebConfiguration()
        wconf.parent = self
        wout = _captureStandardOutput(wconf.parseOptions, ['--list'])
        return wout

    def testListDoesNothing(self):
        """
        Verify that 'axiomatic -d foo.axiom web --list' does not modify
        anything, by running it twice and verifying that the generated output
        is identical the first and second time.
        """
        self.assertEquals(self._list(),
                          self._list())


class ConfigurationTestCase(CommandStubMixin, TestCase):
    def setUp(self):
        self.store = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.store, u"example.com", u"", False)


    def test_shortOptionParsing(self):
        """
        Test that the short form of all the supported command line options are
        parsed correctly.
        """
        opt = webcmd.WebConfiguration()
        opt.parent = self
        certFile = self.store.filesdir.child('name')
        opt.parseOptions(['-h', 'http.log', '-H', 'example.com'])
        self.assertEquals(opt['http-log'], 'http.log')
        self.assertEquals(opt['hostname'], 'example.com')


    def test_longOptionParsing(self):
        """
        Test that the long form of all the supported command line options are
        parsed correctly.
        """
        opt = webcmd.WebConfiguration()
        opt.parent = self
        certFile = self.store.filesdir.child('name')
        opt.parseOptions([
                '--http-log', 'http.log', '--hostname', 'example.com',
                '--urchin-key', 'A123'])
        self.assertEquals(opt['http-log'], 'http.log')
        self.assertEquals(opt['hostname'], 'example.com')
        self.assertEquals(opt['urchin-key'], 'A123')


    def test_staticParsing(self):
        """
        Test that the --static option parses arguments of the form
        "url:filename" correctly.
        """
        opt = webcmd.WebConfiguration()
        opt.parent = self
        opt.parseOptions([
                '--static', 'foo:bar',
                '--static', 'quux/fooble:/bar/baz'])
        self.assertEquals(
            opt.staticPaths,
            [('foo', os.path.abspath('bar')),
             ('quux/fooble', '/bar/baz')])


    def test_hostname(self):
        """
        The I{hostname} option changes the C{hostname} attribute of the
        L{SiteConfiguration} object installed on the store.  The hostname
        cannot be set to the empty string.
        """
        opt = webcmd.WebConfiguration()
        opt.parent = self
        opt['hostname'] = 'example.com'
        opt.postOptions()

        opt['hostname'] = ''
        self.assertRaises(UsageError, opt.postOptions)

        self.assertEqual(
            self.store.findUnique(SiteConfiguration).hostname,
            u"example.com")


    def test_urchinKey(self):
        """
        Specifying a Google Analytics key inserts an item into the database
        recording it.
        """
        opt = webcmd.WebConfiguration()
        opt.parent = self
        opt['urchin-key'] = 'A123'
        opt.postOptions()

        self.assertEquals(APIKey.getKeyForAPI(self.store, APIKey.URCHIN).apiKey,
                          u'A123')
