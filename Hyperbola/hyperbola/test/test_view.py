# -*- test-case-name: hyperbola.test.test_view.ViewTestCase.test_scrollViewRenderer -*-
"""
Tests for Hyperbola view logic
"""
from xml.dom import minidom

from twisted.trial.unittest import TestCase

from epsilon.extime import Time
from epsilon.scripts import certcreate

from axiom import userbase
from axiom.store import Store
from axiom.dependency import installOn

from nevow import context, tags, loaders, athena, flat, page, inevow
from nevow.testutil import FakeRequest, FragmentWrapper, renderLivePage
from nevow.flat import flatten
from nevow.page import renderer

from xmantissa import sharing, websharing, scrolltable
from xmantissa.sharing import SharedProxy
from xmantissa.publicweb import PublicAthenaLivePage, LoginPage
from xmantissa.ixmantissa import IWebTranslator
from xmantissa.web import SiteConfiguration
from xmantissa.test.test_people import emptyMantissaSiteStore

from hyperbola import hyperbola_view, hyperblurb, ihyperbola
from hyperbola.hyperblurb import FLAVOR
from hyperbola.hyperbola_view import BlurbViewer
from hyperbola.ihyperbola import IViewable
from hyperbola.test.util import HyperbolaTestMixin



def createStore(testCase):
    """
    Create a new Store in a temporary directory retrieved from C{testCase}.
    Give it a LoginSystem and create an SSL certificate in its files directory.

    @param testCase: The L{unittest.TestCase} by which the returned Store will
    be used.

    @rtype: L{Store}
    """
    dbdir = testCase.mktemp()
    store = Store(dbdir)
    login = userbase.LoginSystem(store=store)
    installOn(login, store)
    certPath = store.newFilePath('server.pem')
    certcreate.main(['--filename', certPath.path, '--quiet'])
    return store



class ScrollerTestCase(TestCase, HyperbolaTestMixin):
    """
    Tests for L{hyperbola_view.ShareScrollingElement} and related
    functionality.
    """
    def setUp(self):
        """
        Set up an environment suitable for testing the share-handling
        functionality of L{hyperbola_view.ShareScrollingElement}.
        """
        self._setUpStore()

        blogShare = self._shareAndGetProxy(self._makeBlurb(FLAVOR.BLOG))
        EVERYBODY = sharing.getEveryoneRole(self.userStore)
        sharing.itemFromProxy(blogShare).permitChildren(
            EVERYBODY, FLAVOR.BLOG_POST, ihyperbola.IViewable)

        # For sanity's sake, let's not have the role of the view and the role
        # implicitly chosen by not calling 'customizeFor' disagree.  (This
        # shouldn't be possible anyway, and in the future getRole should just
        # be looking at its proxy.)
        self.publicBlogShare = sharing.getShare(
            self.userStore, EVERYBODY, blogShare.shareID)
        selfRole = sharing.getSelfRole(self.userStore)
        blogPostShareID = blogShare.post(u'', u'', selfRole)
        self.blogPostSharedToEveryone = sharing.getShare(
            self.userStore, EVERYBODY, blogPostShareID)
        self.blogPostItem = sharing.itemFromProxy(self.blogPostSharedToEveryone)


    def _getRenderViewScroller(self):
        """
        Get a L{hyperbola_view.ShareScrollingElement} by way of
        L{hyperbola_view.BlogBlurbViewer.view}.
        """
        fragment = hyperbola_view.BlogBlurbViewer(self.publicBlogShare)
        return fragment.view(FakeRequest(), tags.invisible())


    def test_scrollViewRenderer(self):
        """
        Verify that L{hyperbola_view.BlogBlurbViewer.render_view} returns a
        L{hyperbola.hyperbola_view.ShareScrollTable} when posts are available.
        """
        scroller = self._getRenderViewScroller()
        self.failUnless(isinstance(scroller,
                                   hyperbola_view.ShareScrollingElement))


    def test_renderedScrollerInitializedCorrectly(self):
        """
        L{hyperbola_view.BlogBlurbViewer.render_view} should return a
        L{hyperbola.hyperbola_view.ShareScrollTable} that is aware of
        all of the posts that have been made to the blog.
        """
        scroller = self._getRenderViewScroller()
        rows = scroller.rowsAfterValue(None, 10)
        self.assertEqual(len(rows), 1)
        theRow = rows[0]
        self.assertEqual(
            theRow['dateCreated'],
            self.blogPostItem.dateCreated.asPOSIXTimestamp())
        self.assertEqual(
            theRow['__id__'],
            IWebTranslator(self.userStore).toWebID(self.blogPostItem))
        blogPostFragment = theRow['blurbView']
        # the scrolltable fragment is not customized, so we want to
        # ensure that the proxy passed to the IColumns is the facet
        # shared to Everyone
        self.assertEqual(
            list(blogPostFragment.original.sharedInterfaces),
            list(self.blogPostSharedToEveryone.sharedInterfaces))
        self.assertIdentical(
            sharing.itemFromProxy(blogPostFragment.original),
            self.blogPostItem)


    def test_renderedScrollerRenderable(self):
        """
        L{hyperbola_view.BlogBlurbViewer.render_view} should return a
        L{hyperba.hyperbola_view.ShareScrollTable} that is renderable
        - i.e. has a docFactory and is not an orphan.
        """
        scroller = self._getRenderViewScroller()
        self.failUnless(scroller.fragmentParent is not None)
        return renderLivePage(FragmentWrapper(scroller))


    def test_blurbTimestampColumn(self):
        """
        Verify the L{xmantissa.ixmantissa.IColumn} implementation of
        L{hyperbola_view._BlurbTimestampColumn}.
        """
        col = hyperbola_view._BlurbTimestampColumn()
        self.assertEqual(col.attributeID, 'dateCreated')
        self.assertEqual(col.getType(), 'timestamp')
        self.blogPostItem.dateCreated = Time.fromPOSIXTimestamp(345)
        value = col.extractValue(None, self.blogPostItem)
        self.assertEqual(value, 345)
        self.assertIdentical(col.sortAttribute(), hyperblurb.Blurb.dateCreated)
        comparable = col.toComparableValue(345)
        self.assertEqual(comparable, self.blogPostItem.dateCreated)


    def test_blurbViewColumn(self):
        """
        Verify the L{xmantissa.ixmantissa.IColumn} implementation of
        L{hyperbola_view.BlurbViewColumn}.
        """
        col = hyperbola_view.BlurbViewColumn()
        self.assertEqual(col.attributeID, 'blurbView')
        self.assertEqual(col.getType(), scrolltable.TYPE_WIDGET)
        model = athena.LivePage()
        frag = col.extractValue(model, self.blogPostSharedToEveryone)
        fragClass = hyperbola_view.blurbViewDispatcher(
            self.blogPostSharedToEveryone).__class__
        self.failUnless(isinstance(frag, fragClass))
        self.assertIdentical(frag.fragmentParent, model)
        self.failUnless(frag.docFactory)
        self.assertIdentical(col.sortAttribute(), None)
        self.assertRaises(NotImplementedError, col.toComparableValue, None)



class ViewTestCase(TestCase, HyperbolaTestMixin):
    """
    Tests for Hyperbola view logic
    """
    def setUp(self):
        self._setUpStore()


    def test_blogView(self):
        """
        L{hyperbola_view.BlogBlurbViewer.view} should render a pattern
        indicating that there are no blog posts, if it has no children.
        """
        blogShare = self._shareAndGetProxy(self._makeBlurb(FLAVOR.BLOG))
        fragment = hyperbola_view.BlogBlurbViewer(blogShare)
        tag = tags.div(pattern="no-child-blurbs", id="correct")
        result = fragment.view(FakeRequest(), tag)
        self.assertEqual(result.attributes['id'], "correct")
        self.assertEqual(
            result.slotData['child-type-name'], fragment._childTypeName)


    def test_blogsRenderer(self):
        """
        Test that L{hyperbola_view.BlogListFragment.blogs} renders a list of blogs.
        """
        site = self.siteStore.findUnique(SiteConfiguration)
        site.hostname = u'blogs.renderer'
        blog1 = self._shareAndGetProxy(self._makeBlurb(FLAVOR.BLOG))
        blog2 = self._shareAndGetProxy(self._makeBlurb(FLAVOR.BLOG))
        blf = hyperbola_view.BlogListFragment(
            athena.LivePage(), self.publicPresence)
        blf.docFactory = loaders.stan(
            tags.div(pattern='blog')[
                tags.span[tags.slot('title')],
                tags.span[tags.slot('link')],
                tags.span[tags.slot('post-url')]])
        tag = tags.invisible
        markup = flat.flatten(tags.div[blf.blogs(None, tag)])
        doc = minidom.parseString(markup)
        blogNodes = doc.firstChild.getElementsByTagName('div')
        self.assertEqual(len(blogNodes), 2)

        for (blogNode, blog) in zip(blogNodes, (blog1, blog2)):
            (title, blogURL, postURL) = blogNode.getElementsByTagName('span')
            blogURL = blogURL.firstChild.nodeValue
            expectedBlogURL = str(websharing.linkTo(blog))
            self.assertEqual(blogURL, expectedBlogURL)
            postURL = postURL.firstChild.nodeValue
            self.assertEqual(
                postURL, 'https://blogs.renderer' + expectedBlogURL + '/post')


    def test_addComment(self):
        """
        Test adding a comment to a blurb of each flavor through
        L{hyperbola.hyperbola_view.addCommentDispatcher}
        """
        for flavor in hyperblurb.ALL_FLAVORS:
            share = self._shareAndGetProxy(self._makeBlurb(flavor))

            parent = hyperbola_view.blurbViewDispatcher(share)
            parent.customizeFor(self.role.externalID)

            frag = hyperbola_view.addCommentDispatcher(parent)
            frag.addComment(u'title', u'body!', ())

            (comment,) = share.view(self.role)
            self.assertEquals(comment.title, 'title')
            self.assertEquals(comment.body, 'body!')
            self.assertEquals(list(comment.tags()), [])

    def test_addCommentWithTags(self):
        """
        Same as L{test_addComment}, but specify some tags to be applied to the
        comment
        """
        for flavor in hyperblurb.ALL_FLAVORS:
            share = self._shareAndGetProxy(self._makeBlurb(flavor))

            parent = hyperbola_view.blurbViewDispatcher(share)
            parent.customizeFor(self.role.externalID)

            frag = hyperbola_view.addCommentDispatcher(parent)
            frag.addComment(u'title', u'body!', (u't', u'a', u'gs'))

            (comment,) = share.view(self.role)
            self.assertEquals(set(comment.tags()), set(('t', 'a', 'gs')))

    def test_blurbPostingResourceCustomized(self):
        """
        Test that the L{hyperbola.hyperbola_view.BlurbPostingResource} is
        customized so that the blurb that is created will have the correct
        author
        """
        blog = self._shareAndGetProxy(
            self._makeBlurb(hyperblurb.FLAVOR.BLOG))

        bpr = hyperbola_view.BlurbPostingResource(
            self.userStore, blog, self.role.externalID)

        bpr.fragment.addComment(u'', u'', ())

        (comment,) = blog.view(self.role)
        self.assertEquals(comment.author, self.role)

    def test_parseTagsExtraneousWhitespace(self):
        """
        Test that L{hyperbola.hyperbola_view.parseTags}
        removes any whitespace surrounding the tags it is passed
        """
        self.assertEquals(
            hyperbola_view.parseTags(' a , b,c,d,  '), ['a', 'b', 'c', 'd'])

    def test_parseTagsAllWhitespace(self):
        """
        Test that L{hyperbola.hyperbola_view.AddCommentFragment.parseTags}
        returns the empty list when given a string of whitespace
        """
        self.assertEquals(
            hyperbola_view.parseTags('  '), [])

    def test_htmlifyLineBreaks(self):
        """
        Test that L{hyperbola.hyperbola_view.BlurbViewer._htmlifyLineBreaks}
        replaces new lines with <br> elements
        """
        share = self._shareAndGetProxy(
            self._makeBlurb(
                hyperblurb.FLAVOR.BLOG_POST,
                body=u'foo\nbar\r\nbaz'))

        frag = hyperbola_view.blurbViewDispatcher(share)
        self.assertEquals(
            flatten(frag._htmlifyLineBreaks(frag.original.body)),
            'foo<br />bar<br />baz<br />')


    def test_bodyRenderer(self):
        """
        L{BlurbViewer.body} should return a well-formed XHTML document
        fragment even if the body of the blurb being rendered is not
        well-formed.
        """
        body = u'<i>hello'
        expectedBody = u'<i>hello</i><br />'
        view = BlurbViewer(self._makeBlurb(hyperblurb.FLAVOR.BLOG, None, body))
        result = flatten(view.body(None, None))
        self.assertEqual(result, expectedBody)


    def test_bodyRendererEmptyBody(self):
        """
        L{BlurbViewer.body} should be able to render Blurbs
        with empty bodies.
        """
        body = u''
        view = BlurbViewer(self._makeBlurb(hyperblurb.FLAVOR.BLOG, None, body))
        result = flatten(view.body(None, None))
        self.assertEqual(result, body)


    def test_htmlBlurbBody(self):
        """
        Test that we can set and retrieve a blurb body containing HTML through
        the view APIs
        """
        share = self._shareAndGetProxy(
            self._makeBlurb(
                hyperblurb.FLAVOR.BLOG))

        parent = hyperbola_view.blurbViewDispatcher(share)
        parent.customizeFor(self.role.externalID)

        commenter = hyperbola_view.addCommentDispatcher(parent)
        commenter.addComment(u'title', u'<div>body</div>', ())

        (post,) = share.view(self.role)
        postFragment = hyperbola_view.blurbViewDispatcher(post)
        result = postFragment.body(None, None)
        self.assertEqual(flatten(result), '<div>body</div><br />')


    def test_blogTags(self):
        """
        Test that the implementation of C{_getAllTags} on the view for a blog
        post returns all tags that have been applied to blurbs, without
        duplicates
        """
        postShare = self._shareAndGetProxy(
            self._makeBlurb(hyperblurb.FLAVOR.BLOG_POST))
        postShare.tag(u'foo')

        otherPostShare = self._shareAndGetProxy(
            self._makeBlurb(hyperblurb.FLAVOR.BLOG_POST))
        otherPostShare.tag(u'foo')
        otherPostShare.tag(u'bar')

        blogShare = self._shareAndGetProxy(
            self._makeBlurb(hyperblurb.FLAVOR.BLOG))
        blogView = hyperbola_view.blurbViewDispatcher(blogShare)

        self.assertEquals(
            list(sorted(blogView._getAllTags())),
            [u'bar', u'foo'])


    def test_editLinkIfEditable(self):
        """
        Test that L{hyperbola_view.BlogPostBlurbViewer} renders an 'edit' link
        if the underlying blurb is editable.
        """
        post = self._makeBlurb(hyperblurb.FLAVOR.BLOG_POST)

        authorShareID = sharing.shareItem(
            post, toRole=sharing.getSelfRole(self.userStore),
            interfaces=[ihyperbola.IEditable]).shareID
        authorPostShare = sharing.getShare(
            self.userStore, sharing.getSelfRole(self.userStore), authorShareID)

        authorPostView = hyperbola_view.blurbViewDispatcher(authorPostShare)
        tag = tags.invisible(foo='bar')
        result = authorPostView.editLink(None, tag)
        self.assertIdentical(result, tag)


    def test_titleLink(self):
        """
        Verify that L{hyperbola_view.BlogPostBlurbViewer.titleLink} links to
        the correct url.
        """
        share = self._shareAndGetProxy(self._makeBlurb(FLAVOR.BLOG_POST))
        tag = tags.div[tags.slot('link')]
        frag = hyperbola_view.BlogPostBlurbViewer(share)
        tag = page.renderer.get(frag, 'titleLink')(None, tag)
        self.assertEqual(
            str(tag.slotData['link']),
            str(websharing.linkTo(share).child('detail')))



class BlurbViewerTests(HyperbolaTestMixin, TestCase):
    """
    Tests for L{BlurbViewer}.
    """
    def setUp(self):
        self._setUpStore()


    def test_postWithoutPrivileges(self):
        """
        Attempting to post to a blog should result in a L{LoginPage} which
        remembers the parameters of the attempted post.
        """
        class StubBlurb(object):
            """
            L{Blurb}-alike for testing purposes.
            """
            def __init__(self, store, flavor):
                self.store = store
                self.flavor = flavor

        currentSegments = ['foo', 'bar']
        postSegments = ['post', 'baz']
        arguments = {'quux': ['1', '2']}
        request = FakeRequest(
            uri='/'.join([''] + currentSegments + postSegments),
            currentSegments=currentSegments, args=arguments)
        blurb = StubBlurb(self.userStore, FLAVOR.BLOG)
        sharedBlurb = SharedProxy(blurb, (IViewable,), 'abc')
        view = BlurbViewer(sharedBlurb)
        child, segments = view.locateChild(request, postSegments)
        self.assertTrue(isinstance(child, LoginPage))
        self.assertEqual(child.segments, currentSegments + postSegments[:1])
        self.assertEqual(child.arguments, arguments)
        self.assertEqual(segments, postSegments[1:])


    def test_absoluteURL(self):
        """
        Verify that L{BlurbViewer._absoluteURL} returns something that looks
        correct.
        """
        share = self._shareAndGetProxy(self._makeBlurb(FLAVOR.BLOG_POST))
        frag = BlurbViewer(share)
        self.assertEqual(
            frag._absoluteURL(), 'https://localhost' + str(websharing.linkTo(share)))



class AddBlogPostDialogFragmentTests(TestCase):
    """
    Tests for L{AddBlogPostDialogFragment}.
    """
    def setUp(self):
        """
        Create a post enough state to have a view for commenting on it.
        """
        self.store = emptyMantissaSiteStore()
        self.flavor = hyperblurb.FLAVOR.BLOG_POST
        self.author = sharing.getSelfRole(self.store)
        self.post = hyperblurb.Blurb(
            store=self.store, author=self.author, flavor=self.flavor)
        self.postShare = self.author.shareItem(self.post)
        self.sharedPost = self.author.getShare(self.postShare.shareID)
        self.postView = hyperbola_view.BlurbViewer(self.sharedPost)
        self.fragment = hyperbola_view.AddBlogPostDialogFragment(
            self.postView)


    def test_rendering(self):
        """
        L{AddBlogPostDialogFragment} can be rendered as part of a Mantissa
        public Athena page.
        """
        page = PublicAthenaLivePage(self.store, self.fragment, None, None)
        request = FakeRequest()
        request.args = {'title': ['foo'],
                        'body': ['bar'],
                        'url': ['baz']}
        return renderLivePage(page, reqFactory=lambda: request)


    def test_postTitle(self):
        """
        L{AddBlogPostDialogFragment.postTitle} returns the first value of the
        I{title} request argument.
        """
        request = FakeRequest(args={'title': ['foo']})
        self.assertEqual(
            renderer.get(self.fragment, 'postTitle')(request, None),
            'foo')
