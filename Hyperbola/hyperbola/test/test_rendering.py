# Copyright (c) 2008 Divmod.  See LICENSE for details.

"""
Test that the Hyperbola view classes can be rendered
"""

from xml.dom import minidom
from lxml.etree import XPathEvaluator, fromstring

def evaluateXPath(path, document):
    return XPathEvaluator(fromstring(document)).evaluate(path)


from twisted.trial.unittest import TestCase
from twisted.internet import defer

from epsilon.extime import Time

from xmantissa import ixmantissa, webtheme

from nevow.testutil import renderLivePage, FragmentWrapper, AccumulatingFakeRequest, renderPage

from hyperbola import hyperblurb, hyperbola_view
from hyperbola.test.util import HyperbolaTestMixin


class RenderingTestCase(TestCase, HyperbolaTestMixin):
    """
    Test that the Hyperbola view classes can be rendered
    """
    def setUp(self):
        self._setUpStore()

    def _renderFragment(self, fragment, *a, **k):
        """
        Render the fragment C{fragment}

        @rtype: L{twisted.internet.defer.Deferred} firing with string
        rendering result
        """
        fragment.docFactory = webtheme.getLoader(fragment.fragmentName)
        return renderLivePage(FragmentWrapper(fragment), *a, **k)


    def test_adaption(self):
        """
        Test that we can adapt a blurb of any flavor to
        L{xmantissa.ixmantissa.INavigableFragment} and then render the result
        """
        deferreds = list()
        for flavor in hyperblurb.ALL_FLAVORS:
            proxy = self._shareAndGetProxy(self._makeBlurb(flavor))
            deferreds.append(self._renderFragment(
                ixmantissa.INavigableFragment(proxy)))
        return defer.gatherResults(deferreds)


    def test_blurbViewDispatch(self):
        """
        Test that we can pass a blurb of any flavor to
        L{hyperbola.hyperbola_view.blurbViewDispatcher} and then render the
        result
        """
        deferreds = list()
        for flavor in hyperblurb.ALL_FLAVORS:
            proxy = self._shareAndGetProxy(self._makeBlurb(flavor))
            deferreds.append(self._renderFragment(
                hyperbola_view.blurbViewDispatcher(proxy)))
        return defer.gatherResults(deferreds)


    def test_blurbViewDetailDispatch(self):
        """
        Test that we can pass a blurb of any flavor to
        L{hyperbola.hyperbola_view.blurbViewDetailDispatcher} and then render
        the result
        """
        deferreds = list()
        for parentFlavor in hyperblurb.ALL_FLAVORS:
            childFlavor = hyperblurb.FLAVOR.commentFlavors[parentFlavor]

            parent = self._makeBlurb(parentFlavor)
            child = self._makeBlurb(childFlavor)
            child.parent = parent

            childProxy = self._shareAndGetProxy(child)
            deferreds.append(self._renderFragment(
                hyperbola_view.blurbViewDetailDispatcher(childProxy)))
        return defer.gatherResults(deferreds)


    def test_blogPostDetailRendering(self):
        """
        Test that we can pass a blog post blurb to
        L{hyperbola.hyperbola_view.blurbViewDetailDispatcher} and that the
        rendered result contains the title and body of the parent
        """
        child = self._makeBlurb(hyperblurb.FLAVOR.BLOG_POST)
        child.parent = self._makeBlurb(
            hyperblurb.FLAVOR.BLOG, title=u'Parent Title', body=u'Parent Body')

        childProxy = self._shareAndGetProxy(child)
        D = self._renderFragment(
            hyperbola_view.blurbViewDetailDispatcher(childProxy))

        def rendered(xml):
            elements = {}
            doc = minidom.parseString(xml)
            for elt in doc.getElementsByTagName('*'):
                cls = elt.getAttribute('class')
                if not cls:
                    continue
                if cls not in elements:
                    elements[cls] = []
                elements[cls].append(elt)

            self.assertEquals(
                len(elements['hyperbola-blog-main-title']), 1)
            self.assertEquals(
                elements['hyperbola-blog-main-title'][0].firstChild.nodeValue,
                'Parent Title')
            self.assertEquals(
                len(elements['hyperbola-blog-sub-title']), 1)
            self.assertEquals(
                elements['hyperbola-blog-sub-title'][0].firstChild.nodeValue,
                'Parent Body')

        D.addCallback(rendered)
        return D


    def test_addCommentDispatch(self):
        """
        Test that we can pass a blurb of any flavor to
        L{hyperbola.hyperbola_view.addCommentDispatcher} and then render the
        result
        """
        deferreds = list()
        for flavor in hyperblurb.ALL_FLAVORS:
            proxy = self._shareAndGetProxy(self._makeBlurb(flavor))
            deferreds.append(self._renderFragment(
                hyperbola_view.addCommentDispatcher(
                    hyperbola_view.blurbViewDispatcher(proxy))))
        return defer.gatherResults(deferreds)


    def test_addCommentDialogDispatch(self):
        """
        Test that we can pass a blurb of any flavor to
        L{hyperbola.hyperbola_view.addCommentDialogDispatcher} and then render
        the result
        """
        class RequestWithArgs(AccumulatingFakeRequest):
            def __init__(self, *a, **k):
                AccumulatingFakeRequest.__init__(self, *a, **k)
                self.args = {'title': [''], 'body': [''], 'url': ['']}

        deferreds = list()
        for flavor in hyperblurb.ALL_FLAVORS:
            proxy = self._shareAndGetProxy(self._makeBlurb(flavor))
            deferreds.append(self._renderFragment(
                hyperbola_view.addCommentDialogDispatcher(
                    hyperbola_view.blurbViewDispatcher(proxy)),
                reqFactory=RequestWithArgs))
        return defer.gatherResults(deferreds)


    def test_editBlurbDispatch(self):
        """
        Test that we can pass a blurb of any flavor to
        L{hyperbola.hyperbola_view.editBlurbDispatcher} and then render the
        result
        """
        deferreds = list()
        for flavor in hyperblurb.ALL_FLAVORS:
            proxy = self._shareAndGetProxy(self._makeBlurb(flavor))
            deferreds.append(self._renderFragment(
                hyperbola_view.editBlurbDispatcher(proxy)))
        return defer.gatherResults(deferreds)



class RSSTestCase(TestCase):
    """
    Tests for RSS generation.
    """
    BLOG_URL = 'http://example.com/blog'
    BLOG_AUTHOR = u'bob@example.com'

    def setUp(self):
        self.patch(
            hyperbola_view.BlurbViewer, '_absoluteURL',
            lambda x: self.BLOG_URL)
        self.patch(
            hyperbola_view.BlurbViewer, 'getRole', lambda x: None)


    def test_rssGeneration(self):
        """
        Test that the RSS generator produces the desired output.
        """
        BLOG_TITLE = u'Awesome! A Blog.'
        BLOG_DESC = u'A blog about stuff.'
        POST_TITLE = u'awesome title'
        POST_BODY = u'<div>body</div>'
        blurb = MockBlurb(flavor=hyperblurb.FLAVOR.BLOG,
                          title=BLOG_TITLE, body=BLOG_DESC,
                          author=self.BLOG_AUTHOR,
                          children=[MockBlurb(flavor=hyperblurb.FLAVOR.BLOG_POST,
                                              title=POST_TITLE,
                                              body=POST_BODY,
                                              author=self.BLOG_AUTHOR,
                                              children=[])])
        def checkData(rssData):
            def assertPathEqual(path, data):
                self.assertEqual(evaluateXPath(path, rssData)[0], data)
            assertPathEqual('/rss/channel/title/text()', BLOG_TITLE)
            assertPathEqual('/rss/channel/link/text()', self.BLOG_URL)
            assertPathEqual('/rss/channel/description/text()', BLOG_DESC)

            self.assertEqual(
                len(evaluateXPath('/rss/channel/item', rssData)), 1)
            assertPathEqual('/rss/channel/item[1]/title/text()', POST_TITLE)
            assertPathEqual('/rss/channel/item[1]/description/text()',
                            POST_BODY)
        rssView = hyperbola_view.blurbViewDispatcher(blurb).child_rss(None)
        return renderPage(rssView).addCallback(checkData)


    def test_emptyRSS(self):
        """
        Test that RSS generation works properly for blurbs with no children.
        """
        blurb = MockBlurb(flavor=hyperblurb.FLAVOR.BLOG,
                          title=u"blog title", body=u"blog desc",
                          children=[], author=self.BLOG_AUTHOR)

        def checkData(rssData):
            rssDoc = minidom.parseString(rssData)
            self.assertEqual(evaluateXPath('/rss/channel/item', rssData), [])
        rssView = hyperbola_view.blurbViewDispatcher(blurb).child_rss(None)
        return renderPage(rssView).addCallback(checkData)



class MockBlurb(object):
    """
    Mock version of L{hyperbola.hyperblurb.Blurb}.
    """

    def __init__(self, flavor, title, body, children, author):
        self.flavor = flavor
        self.title = title
        self.body = body
        self.children = children
        self.dateLastEdited = Time()
        #pretend to be a SharedProxy too
        self._sharedItem = self
        class author(object):
            externalID = author
        self.author = author


    def view(self, role):
        """
        Not testing sharing logic here, so just provide children as-is.
        """
        return self.children
