from axiom.tags import Catalog

from nevow.livetrial.testcase import TestCase
from nevow.athena import expose

from xmantissa.webtheme import getLoader

from hyperbola.test.util import HyperbolaTestMixin
from hyperbola.hyperblurb import FLAVOR
from hyperbola import hyperbola_view

class BlurbTestCase(TestCase, HyperbolaTestMixin):
    """
    Tests for blurb rendering/behaviour
    """
    jsClass = u'Hyperbola.Test.BlurbTestCase'

    def _getBlurb(self, flavor):
        self._setUpStore()
        share = self._shareAndGetProxy(self._makeBlurb(flavor))

        f = hyperbola_view.blurbViewDispatcher(share)
        f.setFragmentParent(self)
        f.docFactory = getLoader(f.fragmentName)

        return f

    def getBlogPost(self, tags):
        """
        Make a L{FLAVOR.BLOG_POST}, wrap it in the appropriate fragment and
        return it

        @param tags: tags to apply to the blog post
        @type tags: iterable of C{unicode}

        @rtype: L{hyperbola_view.BlurbViewer}
        """
        f = self._getBlurb(FLAVOR.BLOG_POST)
        for tag in tags:
            f.original.tag(tag)
        return f
    expose(getBlogPost)

    def getBlog(self, tags):
        """
        Make a L{FLAVOR.BLOG}, wrap it in the appropriate fragment and
        return it

        @param tags: tags to insert in the store
        @type tags: iterable of C{unicode}

        @rtype: L{hyperbola_view.BlurbViewer}
        """
        f = self._getBlurb(FLAVOR.BLOG)
        catalog = self.store.findOrCreate(Catalog)
        for tag in tags:
            catalog.tag(self.store, tag)
        return f
    expose(getBlog)
