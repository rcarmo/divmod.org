
"""
This module contains interfaces specific to Hypberbola blurb permissions.
"""

from zope.interface import Interface, Attribute

class IViewable(Interface):
    """
    This interfaces comprises the visible properties on a blurb which can be
    read.
    """

    title = Attribute('A unicode string, the title of this blurb.')

    body = Attribute('A unicode string, the body of this blurb.')

    dateLastEdited = Attribute(
        'An L{epsilon.extime.Time} instance, when this blurb was last edited.')

    dateCreated = Attribute(
        'An L{epsilon.extime.Time} instance, when this blurb was first created.')

    author = Attribute(
        'An L{xmantissa.sharing.Role} instance, the last editor of this '
        'blurb.')

    flavor = Attribute(
        'A unicode string, indicating the way this blurb should be formatted; '
        'further documentation can be found on L{hyperblurb.FLAVOR}')

    hits = Attribute(
        'An integer, the number of posts attached to this ')

    parent = Attribute(
        'A reference to another L{IViewable} provider, which this was in '
        'response to.')

    def view(role):
        """
        Return an iterator of all the children of this viewable, which are
        themselves providers of IViewable (and possibly other interfaces in
        this module).  Only IViewable providers visible to the current role
        will be yielded.
        """

    def viewByTag(role, tag):
        """
        Same as L{view}, but only children tagged with C{tag} will be returned

        @param tag: the tag name
        @type tag: C{unicode}
        """

    def tags():
        """
        Return an iterable of the names of tags that have been applied to this
        viewable
        """



class ICommentable(IViewable):
    """
    This interfaces comprises the methods which are available on a blurb which
    can be commented upon.
    """
    def post(childTitle, childBody, childAuthor, roleToPerms=None):
        """
        Create a subordinate IViewable provider in the same database as this
        L{ICommentable}.

        @param childTitle: the title of the new blurb.
        @type childTitle: L{unicode}

        @param childBody: the body text of the new blurb.
        @type childBody: L{unicode}

        @param childAuthor: the primary role of the entity which is attempting
        to create the child posting.
        @type childAuthor: L{xmantissa.sharing.Role}

        @param roleToPerms: a mapping of roles to permissions.  if supplied,
        these permissions will override the default permissions, and any
        persistent permissions
        @type roleToPerms: C{dict} mapping L{xmantissa.sharing.Role} to
        C{lists} of L{zope.interface.Interface}

        @param ignorePersistentPerms: ignore any
        L{hyperbola.hyperblurb.FlavorPermission} objects that pertain to this
        blurb or any of its ancestors
        @type ignorePersistentPerms: boolean

        @rtype: L{unicode}
        @return: The shareID of the new L{IViewable} provider.
        """



class IEditable(IViewable):
    """
    This interface comprises the methods which are available on a blurb which
    can be edited directly.
    """
    def edit(newTitle, newBody, newAuthor, newTags):
        """
        Change the contents of this blurb to refer to a new body, title, and
        author.

        @param newTitle: the title of the new blurb.
        @type newTitle: L{unicode}

        @param newBody: the body text of the new blurb.
        @type newBody: L{unicode}

        @param newAuthor: the primary role of the entity which is attempting
        to create the child posting.
        @type newAuthor: L{xmantissa.sharing.Role}

        @param newTags: the tags of the new blurb
        @type newTags: sequence of C{unicode}
        """


    def tag(tagName):
        """
        Apply a tag to this blurb

        @param tagName: the tag name
        @type tagName: C{unicode}
        """

    def delete():
        """
        Unshare & delete this blurb, and any descendent blurbs and previous
        versions of this blurb
        """
