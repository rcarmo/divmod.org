# -*- test-case-name: hyperbola.test -*-
"""
This module mostly implements the L{Blurb} class, which is a piece of
public, shared, or private textual data.  They correspond to blog posts, wiki
pages, forum posts, comments, threads (etc, etc) in other systems.
"""


from zope.interface import implements

from twisted.python.reflect import qual, namedAny

from epsilon.extime import Time

from axiom.item import Item
from axiom.attributes import text, reference, integer, timestamp, textlist, AND
from axiom.tags import Catalog, Tag
from axiom import batch

from xmantissa.sharing import Role, shareItem, asAccessibleTo, unShare

from hyperbola import ihyperbola

class FLAVOR:
    """
    Although in principle the same, many types of published electronic text
    have subtly different user-interface expectations associated with them.
    This class is simply a namespace to hold constants that describe those
    expectations.
    """

    BLOG = u'FLAVOR.BLOG'
    BLOG_POST = u'FLAVOR.BLOG_POST'

    BLOG_COMMENT = u'FLAVOR.BLOG_COMMENT'

    FORUM = u'FLAVOR.FORUM'
    FORUM_TOPIC = u'FLAVOR.FORUM_TOPIC'
    FORUM_POST = u'FLAVOR.FORUM_POST'

    WIKI = u'FLAVOR.WIKI'
    WIKI_NODE = u'FLAVOR.WIKI_NODE'

    commentFlavors = {

        BLOG: BLOG_POST,
        BLOG_POST: BLOG_COMMENT,
        BLOG_COMMENT: BLOG_COMMENT,

        FORUM_POST: FORUM_POST,
        FORUM_TOPIC: FORUM_POST,
        FORUM: FORUM_TOPIC,

        WIKI: WIKI_NODE,
        WIKI_NODE: WIKI_NODE,

        }


ALL_FLAVORS = set((FLAVOR.BLOG, FLAVOR.BLOG_POST, FLAVOR.BLOG_COMMENT,
    FLAVOR.FORUM, FLAVOR.FORUM_TOPIC, FLAVOR.FORUM_POST, FLAVOR.WIKI,
    FLAVOR.WIKI_NODE))

class FlavorPermission(Item):
    """
    I am associated with a top-level Blurb and specify the associated roles for
    all of its children.  For example: if there is a top-level blurb X with the
    BLOG flavor, there might be a FlavorPermission associated with it that
    makes reference to a 'writer staff' role for the BLOG_POST flavor, which
    has permissions IViewable, ICommentable - but conspicuously omits
    IEditable.  That collection of properties means that when posts are made on
    blog X they will be viewable and commentable by the writer staff, but not
    editable by them.  A separate flavor permission might deal with the
    editorial staff.

    Each permission is a zope Interface object.
    """
    # XXX "FlavorPermission" is a terrible name for this class, but I hope this
    # docstring is explanitory enough that someone else might help me think of
    # a better one.  at any rate, it's *mainly* an implementation detail,
    # although there does need to be some UI for managing this.

    typeName = 'hyperbola_flavor_permission'

    flavor = text(
        doc="""
        The 'flavor' attribute is the name of the flavor of a potential child
        of the blurb this permission applies to.

        For example, if this permission controls comments on a blurb that has
        the flavor FLAVOR.BLOG_POST, this attribute will be
        FLAVOR.BLOG_COMMENT.
        """)

    blurb = reference(
        doc="""
        The 'blurb' attribute is a reference to a L{Blurb}, whose children this
        object is controlling the permissions of.
        """)

    role = reference(
        doc="""
        The 'role' attribute is a reference to a L{Role}, which is the role
        that the permissions will be shared to.
        """)

    # XXX TODO -- right now sharing has a list of interfaces, axiom.dependecy
    # has a list of typeclasses, and hyperbola has this list of interfaces that
    # are slightly different than sharing's.  we should implement a "list of
    # interface objects" attribute, and a "list of typeName" attribute, so the
    # logic around this can be more abstract.

    permissions = textlist(
        doc="""
        A list of the names of Python interfaces that will be exposed to this
        permission's role.
        """)


class Blurb(Item):
    """
    I am some text written by a user.

    'Blurb' is the super-generic term used to refer to all forms of publishing
    and commentary within Hyperbola.  Traditionally entirely different software
    packages have been constructed to handle 'forums', 'blogs', 'posts',
    'comments', 'articles', etc.  In hyperbola, text written by a user in any
    context becomes a blurb; whether it is displayed as forum software or blog
    software would display it (and how: as a comment, as a topic, as a post) is
    determined by its 'flavor'.

    Normally these should only be created by the L{Blurb.permitChildren}
    method, not created directly.

    Flavors are described by L{FLAVOR}.
    """
    implements(
        ihyperbola.IViewable,
        ihyperbola.IEditable,
        ihyperbola.ICommentable)

    typeName = 'hyperbola_blurb'
    schemaVersion = 1

    dateCreated = timestamp()
    dateLastEdited = timestamp()

    title = text(
        doc="""
        A short summary of this blurb.  This is formatted as XHTML mixed
        content.
        """)
    body = text(
        doc="""
        A short summary of this blurb.  This is formatted as XHTML mixed
        content.
        """)

    hits = integer(
        doc="The number of times that this blurb has been displayed to users.",
        default=0)

    author = reference(
        reftype=Role,
        allowNone=False)

    parent = reference()        # to Blurb, but you can't spell that AGGUGHH
    flavor = text(doc="One of FLAVOR's capitalized attributes.",
                  allowNone=False)

    def edit(self, newTitle, newBody, newAuthor, newTags):
        """
        Edit an existing blurb, saving a PastBlurb of its current state for
        rollback purposes.
        """
        # Edit is only called on subsequent edits, not the first time, so we
        # need to save our current contents as history.
        editDate = Time()
        pb = PastBlurb(
            store=self.store,
            title=self.title,
            body=self.body,
            author=self.author,
            blurb=self,
            dateEdited=self.dateLastEdited,
            hits=self.hits)

        catalog = self.store.findOrCreate(Catalog)
        for tag in self.tags():
            catalog.tag(pb, tag)

        self.title = newTitle
        self.body = newBody
        self.dateLastEdited = editDate
        self.author = newAuthor

        self.store.query(Tag, Tag.object == self).deleteFromStore()
        for tag in newTags:
            catalog.tag(self, tag)

    def editPermissions(self, roleToPerms):
        """
        Change the permissions of this blurb

        @param roleToPerms: mapping of roles to interfaces
        @type roleToPerms: C{dict} of L{xmantissa.sharing.Role} to C{list} of
        L{zope.interface.Interface}

        @return: A share ID.
        """
        unShare(self)
        return self._setBlurbPermissions(self, roleToPerms)

    def _getChildPerms(self, childAuthor):
        """
        Get the permissions that should be applied to a child of this blurb

        @param childAuthor: the author of the child blurb
        @type childAuthor: L{xmantissa.sharing.Role}

        @return: mapping of roles to interfaces
        @rtype: C{dict} of L{xmantissa.sharing.Role} to C{list} of
        L{zope.interface.Interface}
        """
        # By default, the author is allowed to edit and comment upon their own
        # entries.  Not even the owner of the area gets to edit (although they
        # probably get to delete).
        roleToPerms = {childAuthor: [ihyperbola.IEditable,
                                     ihyperbola.ICommentable]}
        currentBlurb = self

        # With regards to permission, children supersede their parents.  For
        # example, if you want to lock comments on a particular entry, you can
        # give it a new FlavorPermission and its parents will no longer
        # override.  We are specifically iterating upwards from the child here
        # for this reason.
        newFlavor = FLAVOR.commentFlavors[self.flavor]
        while currentBlurb is not None:
            for fp in self.store.query(FlavorPermission,
                                    AND(FlavorPermission.flavor == newFlavor,
                                        FlavorPermission.blurb == currentBlurb)):
                # This test makes sure the parent doesn't override by
                # clobbering the entry in the dictionary.
                if fp.role not in roleToPerms:
                    roleToPerms[fp.role] = [
                        namedAny(x.encode('ascii')) for x in fp.permissions]
            currentBlurb = currentBlurb.parent
        return roleToPerms


    def _setBlurbPermissions(self, blurb, roleToPerms):
        # We want the shareIDs of the same post for different roles to all be
        # the same, so that users can trade URLs - since "None" will allocate a
        # new one, we just use this value for the first iteration...
        firstShareID = None
        for role, interfaceList in roleToPerms.items():
            shareObj = shareItem(blurb, interfaces=interfaceList,
                                 toRole=role, shareID=firstShareID)
            # ... and then save the initially allocated shareID for each
            # subsequent share.
            firstShareID = shareObj.shareID
        return firstShareID


    def post(self, childTitle, childBody, childAuthor, roleToPerms=None):
        """
        Create a new child of this Blurb, with a flavor derived from the
        mapping into FLAVOR.commentFlavors of self.flavor, shared to every role
        specified by FlavorPermission items that refer to the new flavor of
        blurb that will be created, and this blurb or any of my parents.

        For example, if I am a FLAVOR.BLOG, the child will be a
        FLAVOR.BLOG_POST.  If the FlavorPermissions are set up correctly for
        me, one role will be able to view that post, another to comment on it.

        By using FlavorPermissions appropriately, you can have a blog that
        allows public posting, and a blog that allows private posting and no
        public viewing, and a blog that allows public viewing but only
        permissioned posting and commenting, all in the same store.

        @return: A share ID.
        """
        newFlavor = FLAVOR.commentFlavors[self.flavor]
        newBlurb = Blurb(
            store=self.store,
            flavor=newFlavor,
            parent=self,
            body=childBody,
            title=childTitle,
            author=childAuthor,
            dateCreated=Time(),
            dateLastEdited=Time(),
            hits=0)

        if roleToPerms is None:
            roleToPerms = self._getChildPerms(childAuthor)

        return self._setBlurbPermissions(newBlurb, roleToPerms)


    def view(self, role):
        """
        Collect the children of this blurb that are visible to this role.

        @param role: a L{Role} which can observe some children of this blurb.

        @return: an iterable of L{xmantissa.sharing.SharedProxy} instances.
        """
        children = self.store.query(Blurb, Blurb.parent == self, sort=Blurb.dateCreated.descending)
        return asAccessibleTo(role, children)


    def viewByTag(self, role, tag):
        """
        Collect the children of this blurb that are visible to this role, and
        have been tagged with C{tag}

        @param role: a L{Role} which can observe some children of this blurb.
        @param tag: the tag name
        @type tag: C{unicode}

        @return: an iterable of L{xmantissa.sharing.SharedProxy} instances.
        """
        children = self.store.query(
            Blurb, AND(Blurb.parent == self,
                       Tag.object == Blurb.storeID,
                       Tag.name == tag),
            sort=Blurb.dateCreated.descending)
        return asAccessibleTo(role, children)


    def permitChildren(self, role, flavor, *interfaces):
        """
        Allow people from a given role to manipulate a given set of interfaces
        on children of this blurb.  For example, allow anonymous users to view
        but not comment, or allow friends to view.

        @param role: a L{Role} that you wish to allow some action on children
        of this blurb for.

        @param flavor: See L{FLAVOR} - a flavor of a type of child of this
        blurb.

        @param interfaces: a list of zope Interface objects.
        """
        FlavorPermission(
            store=self.store,
            flavor=flavor,
            role=role,
            permissions=[qual(i).decode('ascii') for i in interfaces],
            blurb=self)

    def tags(self):
        """
        Figure out the tags that have been applied to this blurb

        @rtype: iterable of C{unicode}
        """
        return self.store.findOrCreate(Catalog).tagsOf(self)

    def tag(self, tagName):
        """
        Apply a tag to this blurb

        @param tagName: the tag name
        @type tagName: C{unicode}
        """
        self.store.findOrCreate(Catalog).tag(self, tagName)

    def delete(self):
        """
        Unshare & delete this blurb, and any descendent blurbs and
        L{PastBlurb}s
        """
        unShare(self)
        self.store.query(PastBlurb, PastBlurb.blurb == self).deleteFromStore()
        for blurb in self.store.query(Blurb, Blurb.parent == self):
            blurb.delete()
        self.deleteFromStore()

    def stored(self):
        """
        Hook the occurrence of a blurb being added to a store and notify the
        batch processor, if one exists, of the event so that it can schedule
        itself to handle the new blurb, if necessary.
        """
        source = self.store.findUnique(BlurbSource, default=None)
        if source is not None:
            source.itemAdded()



BlurbSource = batch.processor(Blurb)



class PastBlurb(Item):
    """
    This is an old version of a blurb.  It contains the text as it used to be
    at a particular point in time.
    """

    typeName = 'hyperbola_past_blurb'
    schemaVersion = 1

    dateEdited = timestamp()

    title = text()
    body = text()

    hits = integer(doc="The number of times that this blurb has been displayed to users.")
    author = reference(reftype=Role,
                       allowNone=False)

    blurb = reference(reftype=Blurb)
