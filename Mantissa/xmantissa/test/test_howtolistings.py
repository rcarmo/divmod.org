# Copyright 2008 Divmod, Inc. See LICENSE file for details

"""
This module tests the code listings used in the Mantissa lore documentation, in
the top-level 'doc/' directory.

See also L{nevow.test.test_howtolistings}.
"""

import sys

from zope.interface import implements

from zope.interface.verify import verifyObject

from twisted.python.filepath import FilePath

from twisted.trial.unittest import TestCase

from epsilon.structlike import record

from nevow.testutil import FakeRequest
from nevow.flat import flatten
from nevow.url import URL

from axiom.store import Store

from xmantissa.ixmantissa import ISiteRootPlugin, IMantissaSite, IWebViewer
from xmantissa.ixmantissa import IMessageReceiver
from xmantissa.publicweb import AnonymousSite
from axiom.plugins.mantissacmd import Mantissa


class StubShellPage(record('model')):
    """
    A stub implementation of the shell-page object that should be returned from
    wrapModel.
    """


class StubViewer(object):
    """
    A stub implementation of IWebViewer.
    """
    implements(IWebViewer)

    def wrapModel(self, thingy):
        """
        Wrap a model and return myself, with the model set.
        """
        self.shell = StubShellPage(thingy)
        return self.shell


class ExampleTestBase(object):
    """
    This mixin provides setUp and tearDown methods for adding a specific
    example to the path.

    See ticket #2713 for certain issues that this test has with operating in an
    installed environment.
    """

    def setUp(self):
        """
        Add the example dictated by C{self.examplePath} to L{sys.path}.
        """
        here = FilePath(__file__).parent().parent().parent().child('doc')
        for childName in self.examplePath:
            here = here.child(childName)
        sys.path.append(here.path)
        self.addCleanup(sys.path.remove, here.path)



class SiteRootDocumentationTest(ExampleTestBase, TestCase):
    """
    Tests for doc/siteroot.xhtml and friends.
    """

    examplePath = ['listings', 'siteroot']

    def setUp(self):
        """
        Do the example setup and import the module.
        """
        ExampleTestBase.setUp(self)
        import aboutpage
        import adminpage
        self.aboutpage = aboutpage
        self.adminpage = adminpage


    def test_powerItUp(self):
        """
        Powering up a store with an C{AboutPlugin} results in it being installed
        as an L{ISiteRootPlugin} powerup.
        """
        s = Store()
        ap = self.aboutpage.AboutPlugin(store=s)
        s.powerUp(ap)
        self.assertEquals([ap], list(s.powerupsFor(ISiteRootPlugin)))


    def test_interface(self):
        """
        C{AboutPlugin} implements L{ISiteRootPlugin}.
        """
        self.assertTrue(verifyObject(ISiteRootPlugin, self.aboutpage.AboutPlugin()))


    def test_produceAboutResource(self):
        """
        When C{AboutPlugin} is installed on a site store created by 'axiomatic
        mantissa', requests for 'about.php' will be responded to by a helpful
        message wrapped in a shell page.
        """
        s = Store(self.mktemp())
        s.powerUp(self.aboutpage.AboutPlugin(store=s))
        m = Mantissa()
        m.installSite(s, u"localhost", u"", False)
        root = IMantissaSite(s)
        viewer = StubViewer()
        result, segments = root.siteProduceResource(FakeRequest(),
                                                    tuple(['about.php']),
                                                    viewer)
        self.assertIdentical(result, viewer.shell)
        self.assertIsInstance(result.model, self.aboutpage.AboutText)


    def test_notOtherResources(self):
        """
        C{AboutPlugin} will only respond to about.php, not every page on the
        site.
        """
        s = Store(self.mktemp())
        s.powerUp(self.aboutpage.AboutPlugin(store=s))
        s.powerUp(AnonymousSite(store=s))
        root = IMantissaSite(s)
        viewer = StubViewer()
        result = root.siteProduceResource(FakeRequest(),
                                          tuple(['undefined']),
                                          viewer)
        self.assertIdentical(result, None)


    def test_rendering(self):
        """
        C{AboutText} should render a <div> with a string in it.
        """
        self.assertEquals("<div>Hello, world!</div>",
                          flatten(self.aboutpage.AboutText(u'Hello, world!')))


    def test_adminRedirect(self):
        """
        When the admin redirect is installed on a store, it should return an
        URL which should redirect to /private.
        """
        s = Store(self.mktemp())
        s.powerUp(self.adminpage.RedirectPlugin(store=s))
        m = Mantissa()
        m.installSite(s, u'localhost', u'', False)
        root = IMantissaSite(s)
        viewer = StubViewer()
        result, segments = root.siteProduceResource(FakeRequest(),
                                                    tuple(['admin.php']),
                                                    viewer)
        self.assertEquals(result, URL.fromString("http://localhost/private"))



class InterstoreMessagingDocumentationTests(ExampleTestBase, TestCase):
    """
    Tests for doc/interstore.xhtml and related files.
    """
    examplePath = ['listings', 'interstore']

    def setUp(self):
        """
        Import the interstore messaging example code.
        """
        ExampleTestBase.setUp(self)
        import cal
        self.cal = cal


    def test_powerUp(self):
        """
        L{Calendar} is an L{IMessageReceiver} powerup.
        """
        store = Store()
        calendar = self.cal.Calendar(store=store)
        self.assertTrue(verifyObject(IMessageReceiver, calendar))
        store.powerUp(calendar)
        self.assertEquals(
            list(store.powerupsFor(IMessageReceiver)), [calendar])

