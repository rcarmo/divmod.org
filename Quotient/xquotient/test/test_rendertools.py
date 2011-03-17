
from twisted.trial.unittest import TestCase

from nevow.athena import LiveFragment, LiveElement
from nevow.loaders import stan
from nevow.tags import p, directive

from xquotient.benchmarks.rendertools import render


class LivePageRendererTestCase(TestCase):
    """
    Test utility function L{render} to make sure it can render various kinds of
    fragments.
    """

    message = 'Hello, world.'
    docFactory = stan(p(render=directive('liveElement'))[message])

    def testRenderLiveFragment(self):
        """
        Test that L{render} spits out the right thing for a L{LiveFragment}.
        """
        self.assertIn(
            self.message,
            render(LiveFragment(docFactory=self.docFactory)))


    def testRenderLiveElement(self):
        """
        Test that L{render} spits out the right thing for a L{LiveElement}.
        """
        self.assertIn(
            self.message,
            render(LiveElement(docFactory=self.docFactory)))
