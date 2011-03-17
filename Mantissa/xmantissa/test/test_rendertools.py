
"""
Tests for L{xmantissa.test.rendertools}.
"""

from twisted.trial.unittest import TestCase

from nevow.athena import LiveFragment, LiveElement
from nevow.loaders import stan
from nevow.tags import p, directive

from xmantissa.test.rendertools import renderLiveFragment


class LivePageRendererTestCase(TestCase):
    """
    Test utility function L{render} to make sure it can render various kinds of
    fragments.
    """

    message = 'Hello, world.'

    def docFactory(self, renderer, message):
        return stan(p(render=directive(renderer))[message])

    def testRenderLiveFragment(self):
        """
        Test that L{render} spits out the right thing for a L{LiveFragment}.
        """
        docFactory = self.docFactory('liveFragment', self.message)
        self.assertIn(
            self.message,
            renderLiveFragment(LiveFragment(docFactory=docFactory)))


    def testRenderLiveElement(self):
        """
        Test that L{render} spits out the right thing for a L{LiveElement}.
        """
        docFactory = self.docFactory('liveElement', self.message)
        self.assertIn(
            self.message,
            renderLiveFragment(LiveElement(docFactory=docFactory)))
