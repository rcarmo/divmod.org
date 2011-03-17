"""
This module contains tests which verify the permissioned sharing and
viewing logic in Hyperbola.
"""

from axiom.store import Store

from twisted.python.reflect import qual
from twisted.trial import unittest

from epsilon.extime import Time

from axiom.userbase import LoginSystem, LoginMethod
from axiom.plugins.mantissacmd import Mantissa

from xmantissa.product import Product
from xmantissa.ixmantissa import IWebViewer
from xmantissa.sharing import Role, getShare, itemFromProxy, shareItem, NoSuchShare
from xmantissa.sharing import getEveryoneRole, getSelfRole
from xmantissa.publicresource import PublicAthenaLivePage
from xmantissa.websharing import SharingIndex

from hyperbola import hyperbola_model, hyperblurb, ihyperbola

from hyperbola.hyperbola_view import BlurbViewer


class BootstrappingTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        # Cheat so getSelfRole will work...
        lm = LoginMethod(store=self.store, localpart=u'me', domain=u'here',
                         internal=True, protocol=u'*', account=self.store,
                         verified=True)

    def test_myFirstBlog(self):
        """
        Verify that when the user creates a blog via the default public interface,
        createBlog, it is editable by the author (e.g. the owner of the store)
        and viewable by the public.
        """
        self.publicPresence = hyperbola_model.HyperbolaPublicPresence(
            store=self.store)
        self.publicPresence.createBlog(u"A wonderful blog", u"Here it is")
        myBlogs = list(self.publicPresence.getTopLevelFor(getSelfRole(self.store)))
        yourBlogs = list(self.publicPresence.getTopLevelFor(getEveryoneRole(
            self.store)))
        self.failUnless(len(myBlogs) == 1)
        self.failUnless(len(yourBlogs) == 1)
        self.failUnless(ihyperbola.IEditable.providedBy(myBlogs[0]))
        self.failIf(ihyperbola.IEditable.providedBy(yourBlogs[0]))
        self.failUnless(ihyperbola.IViewable.providedBy(myBlogs[0]))
        self.failUnless(ihyperbola.IViewable.providedBy(yourBlogs[0]))
        self.failUnless(ihyperbola.ICommentable.providedBy(myBlogs[0]))
        self.failIf(ihyperbola.ICommentable.providedBy(yourBlogs[0]))



class BlurbTests(unittest.TestCase):
    def setUp(self):
        self.siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.siteStore, u'example.com', u"", False)
        self.loginSystem = self.siteStore.findUnique(LoginSystem)

        userAccount = self.loginSystem.addAccount(
            u'alice', u'example.com', u'password')
        self.userStore = userAccount.avatars.open()

        product = Product(
            store=self.siteStore,
            types=[qual(hyperbola_model.HyperbolaPublicPresence)])
        product.installProductOn(self.userStore)
        self.publicPresence = self.userStore.findUnique(
            hyperbola_model.HyperbolaPublicPresence)

        self.me = Role(store=self.userStore,
                       externalID=u'armstrong@example.com', description=u'foobar')
        self.you = Role(store=self.userStore,
                        externalID=u'radix@example.com', description=u'rad yo')

        blog = self.blog = hyperblurb.Blurb(
            store=self.userStore, title=u"Hello World",
            body=u"Hello World!~!!", author=self.me, hits=0,
            dateCreated=Time(), dateLastEdited=Time(),
            flavor=hyperblurb.FLAVOR.BLOG)

        blog.permitChildren(
            self.me, hyperblurb.FLAVOR.BLOG_POST, ihyperbola.ICommentable)
        blog.permitChildren(
            self.me, hyperblurb.FLAVOR.BLOG_COMMENT, ihyperbola.ICommentable)
        blog.permitChildren(
            self.you, hyperblurb.FLAVOR.BLOG_POST, ihyperbola.ICommentable)
        blog.permitChildren(
            self.you, hyperblurb.FLAVOR.BLOG_COMMENT, ihyperbola.ICommentable)
        shareItem(blog, getEveryoneRole(self.userStore), shareID=u'blog',
                  interfaces=[ihyperbola.IViewable])


    def test_postPermissions(self):
        """
        Verify that a post made on the blog by its owner cannot be commented on by
        people who are not authorized to comment on it.
        """
        postShareID = self.blog.post(u'My First Post', u'Hello, Viewers', self.me)
        self.assertNotIdentical(postShareID, None)
        sharedPost = getShare(self.userStore, self.you, postShareID)
        commentShareID = sharedPost.post(u'My Comemnt To Your Post',
                                         u'Your Bolg Sucks, man', self.you)
        self.assertNotIdentical(commentShareID, None)
        sharedComment = getShare(self.userStore, self.you, commentShareID)
        self.assertIdentical(sharedComment.parent, itemFromProxy(sharedPost))
        self.assertRaises(AttributeError,
                          lambda: sharedPost.edit(
                u'Ima Haxer', u'Haxed u', self.you, ()))
        newTitle = u'My Comment To Your Post'
        newBody = u'Your Blog Sucks, man'
        sharedComment.edit(newTitle, newBody, self.you, ())
        self.assertEquals(sharedComment.body, newBody)
        self.assertEquals(sharedComment.title, newTitle)


    def test_editTags(self):
        """
        Test that L{hyperbola.hyperblurb.Blurb.edit} changes the tags of the
        blurb
        """
        postShareID = self.blog.post(u'', u'', self.me)
        sharedPost = getShare(self.userStore, self.me, postShareID)
        sharedPost.tag(u'foo')
        sharedPost.tag(u'bar')
        self.assertEquals(set(sharedPost.tags()), set(('foo', 'bar')))
        sharedPost.edit(u'', u'', self.me, (u'foo', u'baz'))
        self.assertEquals(set(sharedPost.tags()), set(('foo', 'baz')))


    def test_viewability(self):
        """
        Verify that a blog may be viewed publicly, by retrieving it
        through the web sharing index and inspecting the result to
        verify that it will have appropriate properties set.
        """
        er = getEveryoneRole(self.userStore)
        si = SharingIndex(self.userStore, IWebViewer(self.siteStore))
        child, segs = si.locateChild(None, ['blog'])
        self.assertEquals(len(segs), 0)
        self.failUnless(isinstance(child, PublicAthenaLivePage))
        viewer = child.fragment
        self.failUnless(isinstance(viewer, BlurbViewer))
        blurbish = viewer.original
        self.failUnless(blurbish.title, self.blog.title)
        self.assertEquals(viewer.getRole(), er)


    def test_listingChildren(self):
        """
        Verify that if a series of posts are made on a blog, they will be
        returned by listing the children of that blog.
        """
        shareID1 = self.blog.post(
            u'My First Post', u'Hello, Viewers', self.me)
        shareID2 = self.blog.post(
            u'My Second Post', u'Are the new viewers gone yet?', self.me)
        shareID3 = self.blog.post(
            u'My Third Post', u'duckies', self.me)
        posts = list(self.blog.view(self.you))
        self.assertEquals(len(posts), 3)
        self.assertEquals([post.shareID for post in posts], [shareID3, shareID2, shareID1])

    def test_listingNestedChildren(self):
        """
        Verify that if a post is made on a blog and comments are made on it,
        they will be returned by listing the children of that blog.
        """
        shareID1 = self.blog.post(
            u'My First Post', u'Hello, Viewers', self.me)
        post = getShare(self.userStore, self.you, shareID1)
        shareID2 = post.post(u'a comment', u'O RLY?', self.you)
        post2 = getShare(self.userStore, self.me, shareID2)
        shareID3 = post2.post(u'another comment', u'YA RLY!', self.me)

        posts = list(post.view(self.you))
        self.assertEquals(len(posts), 1)
        self.assertEquals(posts[0].shareID, shareID2)

    def test_tagging(self):
        """
        Test that blurb tagging works
        """
        shareID = self.blog.post(u'', u'', self.me)
        post = getShare(self.userStore, self.me, shareID)
        post.tag(u'foo')
        post.tag(u'bar')
        self.assertEquals(list(post.tags()), ['foo', 'bar'])

    def test_tagsNoTags(self):
        """
        Test that L{hyperbola.hyperblurb.Blurb.tags} returns an empty iterable
        when there are no tags
        """
        shareID = self.blog.post(u'', u'', self.me)
        post = getShare(self.userStore, self.me, shareID)
        self.assertEquals(list(post.tags()), [])

    def test_viewByTag(self):
        """
        Test that L{hyperbola.hyperblurb.Blurb.viewByTag} only returns
        children with the given tag
        """
        post1 = getShare(
            self.userStore, self.me, self.blog.post(u'', u'', self.me))
        post2 = getShare(
            self.userStore, self.me, self.blog.post(u'', u'', self.me))
        post3 = getShare(
            self.userStore, self.me, self.blog.post(u'', u'', self.me))

        post1.tag(u'foo')
        post1.tag(u'bar')

        post2.tag(u'bar')

        self.assertEquals(
            [p.shareID for p in self.blog.viewByTag(self.me, u'bar')],
            [post2.shareID, post1.shareID])

    def test_deleteDeletesChildren(self):
        """
        Test that L{hyperbola.hyperblurb.Blurb.delete} deletes child blurbs
        """
        self.blog.post(u'', u'', self.me)
        self.blog.delete()
        self.assertEquals(self.userStore.query(hyperblurb.Blurb).count(), 0)

    def test_shareToAuthorOnly(self):
        """
        Test that creating a blurb with a single entry for the author in the
        C{roleToPerms} dictionary results in a share that can't be accessed by
        anybody else
        """
        shareID = self.blog.post(
            u'', u'', self.me, {self.me: [ihyperbola.IViewable]})
        self.failUnless(getShare(self.userStore, self.me, shareID))
        self.assertRaises(
            NoSuchShare,
            lambda: getShare(self.userStore, self.you, shareID))

    def test_editPermsAuthorOnly(self):
        """
        Test that creating a blurb with the default permissions and then
        editing the perms to only allow the author to view the post results in
        a share that can't be accessed by anybody else
        """
        shareID = self.blog.post(u'', u'', self.me)
        share = getShare(self.userStore, self.me, shareID)
        shareID = itemFromProxy(share).editPermissions(
            {self.me: [ihyperbola.IViewable]})
        share = getShare(self.userStore, self.me, shareID)
        self.assertRaises(
            NoSuchShare,
            lambda: getShare(self.userStore, self.you, shareID))



class BlurbSourceTestCase(unittest.TestCase):
    """
    Tests for L{hyperbola.hyperblurb.BlurbSource}
    """
    def setUp(self):
        self.store = Store(self.mktemp())
        self.me = Role(store=self.store,
                       externalID=u'armstrong@example.com',
                       description=u'foobar')

    def test_blurbCreationNoSource(self):
        """
        Test that blurb creation goes OK when there is no
        L{hyperbola.hyperblurb.BlurbSource} installed
        """
        hyperblurb.Blurb(
            store=self.store, title=u'',
            body=u'', author=self.me, hits=0,
            dateCreated=Time(), dateLastEdited=Time(),
            flavor=hyperblurb.FLAVOR.BLOG)
