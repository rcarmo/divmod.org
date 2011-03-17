# -*- test-case-name: hyperbola.test.test_view -*-

"""
This module contains web-based views onto L{hyperbola.hyperblurb.Blurb}
objects published by Hyperbola.
"""

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.web.microdom import parseString

from epsilon.extime import Time

from axiom.tags import Catalog, Tag

from nevow import athena, inevow, page, tags, rend
from nevow.flat import flatten

from xmantissa import ixmantissa, webtheme, websharing, publicresource
from xmantissa.publicweb import LoginPage
from xmantissa import sharing, liveform
from xmantissa.scrolltable import ScrollingElement, TYPE_WIDGET

from hyperbola.hyperblurb import FLAVOR, Blurb
from hyperbola import ihyperbola, rss


def _docFactorify(publicViewElement):
    """
    Normally in the course of rendering one of these widgets, the theming
    system (in the guise of xmantissa.websharing.SharingIndex) will assign the
    docFactory attribute to the public INavigableFragment (athena element or
    fragment) of choice.

    There's currently a huge mess of dependencies worming their way through
    websharing, publicweb, hyperbola, and others, which prevents the correct
    solution, which is to use a ThemedElement or themed doc factory from
    webtheme as a basis for all of the themable public views.  This should
    eventually be fixed, and then more general testing fixtures can be used.
    For the moment this function tries to provide a temporary simulacrum of
    correctness; calls to it should be taken to mean "just adjust this fragment
    or element so that it has a usable docFactory for the moment, and fix this
    code later to invoke something that actually honors the store".

    @param publicViewElement: a L{athena.LiveFragment} or an
    L{athena.LiveElement} with a 'fragmentName' attribute, intended to be used
    with the Mantissa theming system.
    """
    publicViewElement.docFactory = webtheme.getLoader(
        publicViewElement.fragmentName)


class _BlurbTimestampColumn(object):
    """
    A timestamp column provider specific to the blurb viewing interface.
    """
    implements(ixmantissa.IColumn)

    attributeID = 'dateCreated'

    def getType(self):
        """
        Return 'timestamp', since this is a timestamp column.
        """
        return 'timestamp'


    def extractValue(self, model, viewable):
        """
        Extract the creation date from an IViewable provider.
        """
        return viewable.dateCreated.asPOSIXTimestamp()


    def sortAttribute(self):
        """
        Return the 'dateCreated' column from Blurb as the sort key for this
        column.
        """
        return Blurb.dateCreated


    def toComparableValue(self, value):
        """
        Convert a float from the client back into a timestamp.
        """
        return Time.fromPOSIXTimestamp(value)



class BlurbViewColumn(object):
    """
    L{ixmantissa.IColumn} which returns the approriate view for the blurb item.
    """
    implements(ixmantissa.IColumn)
    attributeID = 'blurbView'

    def sortAttribute(self):
        """
        BlurbViewColumns cannot be sorted.
        """
        return None


    def extractValue(self, model, share):
        """
        Use L{blurbViewDispatcher} to find the right view for the blurb share
        C{share}.

        @type model: L{ShareScrollingElement}

        @param share: a SharedProxy providing at least L{IViewable}.
        @type share: L{sharing.SharedProxy}

        @return: a blurb view.
        @rtype: L{BlurbViewer} subclass
        """
        fragment = blurbViewDispatcher(share)
        fragment.setFragmentParent(model)
        _docFactorify(fragment)
        return fragment


    def getType(self):
        """
        Return L{TYPE_WIDGET}
        """
        return TYPE_WIDGET


    def toComparableValue(self, value):
        """
        We are not sortable, so explode if anyone tries to do this.
        """
        raise NotImplementedError()



class ShareScrollingElement(ScrollingElement):
    """
    A L{ShareScrollingElement} is a L{ScrollingElement} subclass which wraps its
    query in an L{asAccessibleTo} call to restrict access to the items it is
    browsing.

    @ivar role: The role of the user that is viewing this scrolltable.
    @type role: L{xmantissa.sharing.Role}

    NB: For compatibility with L{ScrollingElement}, all sharing proxies are
    unwrapped before being passed to axiom columns.  This has the security
    implication that any attributes passed to this class's constructor are
    considered public for the purposes of this scrolltable, even if other
    interfaces would have hidden them.
    """
    jsClass = u'Hyperbola.ScrollTable'

    def __init__(self, role, *a, **k):
        """
        Create a L{ShareScrollingElement}.  Take all the same arguments as a
        L{ScrollingElement}, in addition to a L{Role} object that this
        scrolling view will be restricted to.
        """
        self.role = role
        ScrollingElement.__init__(self, *a, **k)


    def linkToItem(self, proxy):
        """
        This table's query results are proxies rather than items, so unwrap
        them to generate unique IDs.

        @param proxy: a shared proxy.
        @type proxy: L{xmantissa.sharing.SharedProxy}

        @return: the web ID of the item that C{proxy} is wrapping.
        @rtype: C{str}
        """
        return super(ShareScrollingElement, self).linkToItem(
            sharing.itemFromProxy(proxy))


    def inequalityQuery(self, constraint, count, isAscending):
        """
        Perform the query in L{ScrollingElement} in a slightly different way: wrap
        it in L{asAccessibleTo} for this L{ShareScrollingElement}'s role.

        @param constraint: an additional constraint to apply to the
        query.
        @type constraint: L{axiom.iaxiom.IComparison}.

        @param count: the maximum number of rows to return.
        @type count: C{int}

        @param isAscending: a boolean describing whether the query
        should be yielding ascending or descending results.
        @type isAscending: C{bool}

        @return: an query which will yield some results from this
        model.
        @rtype: L{axiom.iaxiom.IQuery}
        """
        theQuery = super(ShareScrollingElement, self).inequalityQuery(
            constraint, count, isAscending)
        return sharing.asAccessibleTo(self.role, theQuery.query)



class HyperbolaView(athena.LiveFragment):
    """
    Fragment responsible for rendering the initial hyperbola page
    """
    # This is a Fragment of a Page
    implements(ixmantissa.INavigableFragment)

    # This View will use the hyperbola-start.html template
    fragmentName = 'hyperbola-start'

    iface = {}

    def head(self):
        """
        Override L{ixmantissa.INavigableFragment.head} to do nothing, since we
        don't have to add anything to the header.
        """
        # XXX somebody kill this framework requirement please --glyph


    def render_listBlogs(self, ctx, data):
        """
        Render a list of all blogs.
        """
        return BlogListFragment(self.page, self.original)


    def render_addBlog(self, ctx, data):
        """
        Render an add blog form.
        """
        return BlogAddingFragment(self.page, self.original)



class BlurbPostingResource(publicresource.PublicAthenaLivePage):
    """
    L{nevow.inevow.IResource} which wraps and renders the appropriate add
    comment fragment for the blurb it is passed
    """
    def __init__(self, store, parentBlurb, forUser):
        blurbView = blurbViewDispatcher(parentBlurb)
        blurbView.customizeFor(forUser)

        super(BlurbPostingResource, self).__init__(
            store.parent,
            addCommentDialogDispatcher(blurbView),
            forUser=forUser)



class BlogListFragment(athena.LiveElement):
    """
    Fragment which renders a list of all blogs
    """
    docFactory = webtheme.ThemedDocumentFactory(
        'hyperbola-blog-list', '_resolver')

    def __init__(self, page, hyperbola):
        """
        @type hyperbola: L{hyperbola.hyperbola_model.HyperbolaPublicPresence
        """
        self.setFragmentParent(page)
        self.hyperbola = hyperbola
        self._resolver = ixmantissa.ITemplateNameResolver(self.hyperbola.store)
        super(BlogListFragment, self).__init__()

    def _getPostURL(self, blog):
        """
        Figure out a URL which could be used for posting to C{blog}

        @type blog: L{xmantissa.sharing.SharedProxy}
        @rtype: L{nevow.url.URL}
        """
        site = ixmantissa.ISiteURLGenerator(self.hyperbola.store.parent)
        blogURL = websharing.linkTo(blog)
        siteURL = site.encryptedRoot()
        blogURL.netloc = siteURL.netloc
        blogURL.scheme = siteURL.scheme
        return blogURL.child('post')

    def blogs(self, req, tag):
        """
        Render all blogs
        """
        p = inevow.IQ(self.docFactory).patternGenerator('blog')
        webapp = ixmantissa.IWebTranslator(self.hyperbola.store)
        blogs = list()
        primaryRole = sharing.getSelfRole(self.hyperbola.store)
        for blog in self.hyperbola.getTopLevelFor(primaryRole):
            blogs.append(p.fillSlots(
                    'title', blog.title).fillSlots(
                    'link', websharing.linkTo(blog)).fillSlots(
                    'post-url', self._getPostURL(blog)))
        return tag[blogs]
    page.renderer(blogs)



class BlogAddingFragment(liveform.LiveForm):
    """
    Fragment which renders a form for adding a new blog
    """
    fragmentName = 'hyperbola-add-blog'
    jsClass = u'Hyperbola.AddBlog'

    def __init__(self, page, hyperbola):
        super(BlogAddingFragment, self).__init__(
            hyperbola.createBlog,
            [liveform.Parameter(
                'title',
                liveform.TEXT_INPUT,
                unicode,
                "A title for your blog",
                "A Blog"),
             liveform.Parameter(
                'description',
                liveform.TEXT_INPUT,
                unicode,
                "A description of your blog",
                "A Blog that I write")])
        self.setFragmentParent(page)
        self.hyperbola = hyperbola
        _docFactorify(self)



flavorNames = {
    FLAVOR.BLOG_POST: 'Post',
    FLAVOR.BLOG_COMMENT: 'Comment',
    FLAVOR.BLOG: 'Blog',
    FLAVOR.FORUM: 'Forum',
    FLAVOR.FORUM_TOPIC: 'Forum Topic',
    FLAVOR.FORUM_POST: 'Forum Post',
    FLAVOR.WIKI: 'Wiki',
    FLAVOR.WIKI_NODE: 'Wiki Node'}



def parseTags(tagString):
    """
    Turn a comma delimited string of tag names into a list of tag names

    @type tagString: C{unicode}
    @rtype: C{list} of C{unicode}
    """
    tagList = []
    for tag in tagString.split(','):
        tag = tag.strip()
        if tag:
            tagList.append(tag)
    return tagList



class AddCommentFragment(liveform.LiveForm):
    """
    Base/default fragment which renders into some UI for commenting on a blub
    """
    fragmentName = 'add-comment/default'
    jsClass = u'Hyperbola.AddComment'

    def __init__(self, parent):
        self.parent = parent
        self._commentTypeName = flavorNames[
            FLAVOR.commentFlavors[parent.original.flavor]]

        super(AddCommentFragment, self).__init__(
            self.addComment,
            (liveform.Parameter(
                'title',
                liveform.TEXT_INPUT,
                unicode,
                'Title'),
             liveform.Parameter(
                'body',
                liveform.TEXT_INPUT,
                unicode,
                'Body'),
             liveform.Parameter(
                'tags',
                liveform.TEXT_INPUT,
                parseTags)))

        _docFactorify(self)


    def addComment(self, title, body, tags):
        """
        Add a comment blurb to our parent blurb

        @param title: the title of the comment
        @type title: C{unicode}

        @param body: the body of the comment
        @type body: C{unicode}

        @param tags: tags to apply to the comment
        @type tags: iterable of C{unicode}

        @rtype: C{None}
        """
        shareID = self.parent.original.post(title, body, self.parent.getRole())
        role = self.parent.getRole()
        # is role.store correct?
        post = sharing.getShare(role.store, role, shareID)
        for tag in tags:
            post.tag(tag)

    def commentTypeName(self, req, tag):
        """
        Figure out what this type of comment would be called (e.g. a comment
        on a blog is a 'blog post')
        """
        return self._commentTypeName
    page.renderer(commentTypeName)

    def head(self):
        return None


class AddBlogCommentFragment(AddCommentFragment):
    """
    L{AddCommentFragment} subclass for making comments of type
    L{FLAVOR.BLOG_COMMENT}
    """
    fragmentName = 'add-comment/' + FLAVOR.BLOG_COMMENT

class AddBlogPostFragment(AddCommentFragment):
    """
    L{AddCommentFragment} subclass for making comments of type
    L{FLAVOR.BLOG_POST}
    """
    jsClass = u'Hyperbola.AddBlogPost'
    fragmentName = 'add-comment/' + FLAVOR.BLOG_POST

    def _getAllTags(self):
        """
        Get all the tags in the same store as the underlying item of our
        parent blurb

        @rtype: C{list} of C{unicode}
        """
        store = sharing.itemFromProxy(self.parent.original).store
        return list(store.findOrCreate(Catalog).tagNames())

    def getInitialArguments(self):
        """
        Override default implementation to include the list of all tags
        """
        return (self._getAllTags(),)



class AddBlogPostDialogFragment(AddBlogPostFragment):
    """
    L{AddBlogPostFragment} subclass for making comments of type L{FLAVOR.BLOG_POST}
    """
    jsClass = u'Hyperbola.AddBlogPostDialog'
    fragmentName = 'add-comment/' + FLAVOR.BLOG_POST + '-dialog'

    def postTitle(self, req, tag):
        """
        Determine a preset value for the title of the comment, by looking at the
        C{title} argument in the request.
        """
        return req.args['title'][0]
    page.renderer(postTitle)


    def body(self, req, tag):
        """
        Determine a preset value for the body of the comment, by looking at the
        C{body} argument in the request, and inserting a link to the url
        specified in the C{url} argument.
        """
        body = req.args['body'][0]
        url = req.args['url'][0]
        link = tags.a(href=url)[self.postTitle(req, tag)]
        return flatten((link, tags.br, body))
    page.renderer(body)


ADD_COMMENT_VIEWS = {FLAVOR.BLOG: AddBlogPostFragment,
                     FLAVOR.BLOG_COMMENT: AddCommentFragment}

def addCommentDispatcher(parent):
    """
    Figure out the view class that should render an add comment form for the
    parent blurb C{parent}

    @type parent: L{BlurbViewer}
    @rtype: L{AddCommentFragment}
    """
    return ADD_COMMENT_VIEWS.get(
        parent.original.flavor, AddCommentFragment)(parent)

ADD_COMMENT_DIALOG_VIEWS = {FLAVOR.BLOG: AddBlogPostDialogFragment}

def addCommentDialogDispatcher(parent):
    """
    Figure out the view class that should render an add comment dialog form
    for the parent blurb C{parent}

    @type parent: L{BlurbViewer}
    @rtype: L{AddCommentDialogFragment}
    """
    return ADD_COMMENT_DIALOG_VIEWS.get(
        # this isn't a sensible default
        parent.original.flavor, AddCommentFragment)(parent)



class BlurbViewer(athena.LiveElement, rend.ChildLookupMixin):
    """
    Base/default class for rendering blurbs
    """
    implements(ixmantissa.INavigableFragment)
    fragmentName = 'view-blurb/default'

    customizedFor = None

    def __init__(self, original, *a, **k):
        self.original = original
        super(BlurbViewer, self).__init__(original, *a, **k)
        self._childTypeName = flavorNames[
            FLAVOR.commentFlavors[original.flavor]]


    def _getSelectedTag(self, request):
        """
        Figure out which tag the user is filtering by, by looking at the URL

        @rtype: C{None} or C{unicode}
        """
        tag = request.args.get('tag', [None])[0]
        if not tag:
            return None
        return tag


    def customizeFor(self, username):
        """
        This method is invoked with the viewing user's identification when being
        viewed publicly.
        """
        self.customizedFor = username
        return self


    def getRole(self):
        """
        Retrieve the role currently viewing this blurb viewer.
        """
        store = sharing.itemFromProxy(self.original).store
        if self.customizedFor is None:
            # If this hasn't been customized, it's public.
            return sharing.getEveryoneRole(store)
        else:
            # Otherwise, get the primary role of the current observer.
            return sharing.getPrimaryRole(store, self.customizedFor)


    def child_post(self, ctx):
        """
        If the user is authorized, return a L{BlurbPostingResource}
        """
        store = sharing.itemFromProxy(self.original).store
        if ihyperbola.ICommentable.providedBy(self.original):
            return BlurbPostingResource(
                store, self.original, self.customizedFor)
        return LoginPage.fromRequest(store.parent, inevow.IRequest(ctx))


    def head(self):
        pass


    def title(self, request, tag):
        """
        @return: title of our blurb
        """
        return self.original.title
    page.renderer(title)


    def _htmlifyLineBreaks(self, body):
        """
        Replace line breaks with <br> elements
        """
        return [(tags.xml(line), tags.br) for line
                    in body.splitlines()]


    def body(self, request, tag):
        """
        @return: body of our blurb
        """
        if not self.original.body:
            return ''
        document = parseString(self.original.body, beExtremelyLenient=True)
        body = document.documentElement.toxml()
        return self._htmlifyLineBreaks(body)
    page.renderer(body)


    def dateCreated(self, request, tag):
        """
        @return: creation date of our blurb
        """
        return self.original.dateCreated.asHumanly()
    page.renderer(dateCreated)


    def childCount(self, request, tag):
        """
        @return: child count of our blurb
        """
        # XXX
        return str(sum(1 for ign in self.original.view(self.getRole())))
    page.renderer(childCount)


    def childTypeName(self, request, tag):
        """
        @return: the name of the type of our child blurbs
        """
        return self._childTypeName
    page.renderer(childTypeName)


    def _getChildBlurbs(self, request):
        """
        Get the child blurbs of this blurb

        @rtype: C{list} of L{xmantissa.sharing.SharedProxy}
        """
        return list(self.original.view(self.getRole()))


    def _getChildBlurbViews(self, blurbs):
        """
        Collect the view objects for these child blurbs.
        """
        for blurb in blurbs:
            f = blurbViewDispatcher(blurb)
            f.setFragmentParent(self)
            _docFactorify(f)
            yield f

    def view(self, request, tag):
        """
        Render the child blurbs of this blurb
        """
        blurbs = self._getChildBlurbs(request)
        if 0 < len(blurbs):
            blurbItem = sharing.itemFromProxy(self.original)
            fragment = ShareScrollingElement(
                self.getRole(),
                blurbItem.store,
                Blurb,
                Blurb.parent == blurbItem,
                [_BlurbTimestampColumn(), BlurbViewColumn()],
                Blurb.dateCreated, False,
                ixmantissa.IWebTranslator(blurbItem.store))
            _docFactorify(fragment)
            fragment.setFragmentParent(self)
            return fragment
        else:
            p = inevow.IQ(tag).onePattern('no-child-blurbs')
            return p.fillSlots('child-type-name', self._childTypeName)
    page.renderer(view)


    def addComment(self, request, tag):
        """
        Render some UI for commenting on this blurb
        """
        if not ihyperbola.ICommentable.providedBy(self.original):
            return ''
        f = addCommentDispatcher(self)
        f.setFragmentParent(self)
        _docFactorify(f)
        return f
    page.renderer(addComment)


    def author(self, request, tag):
        """
        Render the author of this blurb
        """
        # XXX this returns 'Everyone'
        return self.original.author.externalID
    page.renderer(author)


    def _absoluteURL(self):
        """
        Return the absolute URL the websharing system makes this blurb
        available at.
        """
        subStore = sharing.itemFromProxy(self.original).store
        site = ixmantissa.ISiteURLGenerator(subStore.parent)
        siteURL = site.encryptedRoot()
        blurbURL = websharing.linkTo(self.original)
        blurbURL.netloc = siteURL.netloc
        blurbURL.scheme = siteURL.scheme
        return str(blurbURL)


    def child_rss(self, ctx):
        return rss.Feed(self)

class _BlogPostBlurbViewer(BlurbViewer):
    """
    L{BlurbViewer} subclass for rendering blurbs of type L{FLAVOR.BLOG_POST}
    """
    fragmentName = 'view-blurb/' + FLAVOR.BLOG_POST
    jsClass = u'Hyperbola.BlogPostBlurbController'

    NO_TAGS_MARKER = u'Uncategorized'

    def titleLink(self, request, tag):
        """
        @return: title of our blurb
        """
        url = websharing.linkTo(self.original)
        return tag.fillSlots(
            'link', url.child('detail')).fillSlots(
            'title', self.original.title)
    page.renderer(titleLink)


    def tags(self, request, tag):
        """
        Render the tags of this blurb
        """
        iq = inevow.IQ(self.docFactory)
        separatorPattern = iq.patternGenerator('tag-separator')
        tags = []
        selectedTag = self._getSelectedTag(request)

        for tag in self.original.tags():
            if tag == selectedTag:
                p = 'selected-tag'
            else:
                p = 'tag'
            tagPattern = iq.onePattern(p)
            tags.extend((tagPattern.fillSlots('name', tag),
                         separatorPattern()))
        if tags:
            return tags[:-1]
        return self.NO_TAGS_MARKER
    page.renderer(tags)


    def editor(self, request, tag):
        f = editBlurbDispatcher(self.original)
        f.setFragmentParent(self)
        _docFactorify(f)
        return f
    page.renderer(editor)


    def editLink(self, request, tag):
        if ihyperbola.IEditable.providedBy(self.original):
            return tag
        return ''
    page.renderer(editLink)


    def deleteLink(self, request, tag):
        """
        Render a delete link or not, depending on whether the user has the
        appropriate permissions
        """
        if ihyperbola.IEditable.providedBy(self.original):
            return tag
        return ''
    page.renderer(deleteLink)


    def delete(self):
        """
        Unshare and delete our blurb, and all of its children
        """
        self.original.delete()
    athena.expose(delete)



class BlogPostBlurbViewer(_BlogPostBlurbViewer):
    def child_detail(self, ctx):
        """
        Return a L{BlogPostBlurbViewerDetail} for this blog post
        """
        f = blurbViewDetailDispatcher(self.original)
        f.customizeFor(self.customizedFor)
        _docFactorify(f)

        return publicresource.PublicAthenaLivePage(
            sharing.itemFromProxy(self.original).store.parent,
            f,
            forUser=self.customizedFor)



class BlogPostBlurbViewerDetail(_BlogPostBlurbViewer):
    """
    L{_BlogPostBlurbViewer} subclass which includes renderers specific to the
    detail page
    """
    fragmentName = 'view-blurb/detail/' + FLAVOR.BLOG_POST

    def blogTitle(self, request, tag):
        """
        Return the title of the blog our blurb was posted in
        """
        return self.original.parent.title
    page.renderer(blogTitle)


    def blogBody(self, request, tag):
        """
        Return the body (subtitle) of the blog our blurb was posted in
        """
        return self.original.parent.body
    page.renderer(blogBody)



class BlogPostBlurbEditor(liveform.LiveForm):
    """
    Fragment for rendering blog post editing UI
    """
    jsClass = u'Hyperbola.BlogPostBlurbEditorController'
    fragmentName = 'edit-blog-post'

    def __init__(self, blogPost):
        super(BlogPostBlurbEditor, self).__init__(
            lambda *a, **k: blogPost.edit(newAuthor=blogPost.author, *a, **k),
            (liveform.Parameter(
                'newTitle',
                liveform.TEXT_INPUT,
                unicode),
             liveform.Parameter(
                'newBody',
                liveform.TEXT_INPUT,
                unicode),
             liveform.Parameter(
                'newTags',
                liveform.TEXT_INPUT,
                parseTags)))
        self.blogPost = blogPost


    def title(self, req, tag):
        """
        @return: title of our blurb
        """
        return self.blogPost.title
    page.renderer(title)


    def body(self, req, tag):
        """
        @return: body of our blurb
        """
        return self.blogPost.body
    page.renderer(body)


    def tags(self, req, tag):
        """
        @return tags of our blurb
        """
        return ', '.join(self.blogPost.tags())
    page.renderer(tags)



class BlogCommentBlurbViewer(BlurbViewer):
    """
    L{BlurbViewer} subclass for rendering blurbs of type L{FLAVOR.BLOG_COMMENT}
    """
    fragmentName = 'view-blurb/' + FLAVOR.BLOG_COMMENT



class BlogBlurbViewer(BlurbViewer):
    """
    L{BlurbViewer} subclass for rendering blurbs of type L{FLAVOR.BLOG}
    """
    fragmentName = 'view-blurb/' + FLAVOR.BLOG
    jsClass = u'Hyperbola.BlogBlurbController'

    def _getAllTags(self):
        """
        Get all the tags which have been applied to blurbs in the same store
        as the underlying item of our blurb.

        @rtype: C{list} of C{unicode}
        """
        store = sharing.itemFromProxy(self.original).store
        # query instead of using Catalog so that tags only applied to
        # PastBlurb items don't get included
        return list(store.query(
            Tag, Tag.object == Blurb.storeID).getColumn('name').distinct())

    def _getChildBlurbs(self, request):
        """
        Get the child blurbs of this blurb, filtering by the selected tag

        @rtype: C{list} of L{xmantissa.sharing.SharedProxy}
        """
        tag = self._getSelectedTag(request)
        if tag is not None:
            return list(self.original.viewByTag(
                self.getRole(), tag.decode('utf-8')))
        return list(self.original.view(self.getRole()))


    def tags(self, request, tag):
        """
        Render all tags
        """
        iq = inevow.IQ(self.docFactory)
        selTag = self._getSelectedTag(request)
        for tag in self._getAllTags():
            if tag == selTag:
                pattern = 'selected-tag'
            else:
                 pattern = 'tag'
            yield iq.onePattern(pattern).fillSlots('name', tag)
    page.renderer(tags)


BLURB_VIEWS = {FLAVOR.BLOG_POST: BlogPostBlurbViewer,
               FLAVOR.BLOG: BlogBlurbViewer,
               FLAVOR.BLOG_COMMENT: BlogCommentBlurbViewer}



def blurbViewDispatcher(blurb):
    """
    Figure out the view class that should render the blurb C{blurb}

    @type blurb: L{xmantissa.sharing.SharedProxy}
    @rtype: L{BlurbViewer}
    """
    return BLURB_VIEWS.get(blurb.flavor, BlurbViewer)(blurb)



registerAdapter(
    blurbViewDispatcher,
    ihyperbola.IViewable,
    ixmantissa.INavigableFragment)



BLURB_DETAIL_VIEWS = {FLAVOR.BLOG_POST: BlogPostBlurbViewerDetail}



def blurbViewDetailDispatcher(blurb):
    """
    Figure out the view class that should render the blurb detail for C{blurb}

    @type blurb: L{xmantissa.sharing.SharedProxy}
    @rtype: L{BlurbViewer}
    """
    return BLURB_DETAIL_VIEWS.get(blurb.flavor, BlurbViewer)(blurb)



EDIT_BLURB_VIEWS = {FLAVOR.BLOG_POST: BlogPostBlurbEditor}



def editBlurbDispatcher(blurb):
    """
    Figure out the view class that should render the edit blurb form for
    C{blurb}

    @type blurb: L{xmantissa.sharing.SharedProxy}
    @rtype: L{BlogPostBlurbEditor}
    """
    # not a great default for now
    return EDIT_BLURB_VIEWS.get(blurb.flavor, BlogPostBlurbEditor)(blurb)
