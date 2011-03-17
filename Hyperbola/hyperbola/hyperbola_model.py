# -*- test-case-name: hyperbola.test.test_hyperbola -*-

"""
This module contains code which interacts with Mantissa to provide an
interface to installing the Hyperbola functionality for a user and creating
blogs.
"""

from zope.interface import implements

from epsilon.extime import Time

from axiom.item import Item

from axiom.dependency import dependsOn

from axiom.upgrade import registerUpgrader

from xmantissa import ixmantissa, webapp, webnav, sharing

from twisted.python.components import registerAdapter

from hyperbola.ihyperbola import IViewable
from hyperbola.hyperbola_view import HyperbolaView
from hyperbola.hyperblurb import Blurb, FLAVOR


class HyperbolaPublicPresence(Item):
    """
    This is a powerup which provides a user with a public presence.  It
    provides a 'Hyperbola' tab,
    """
    # This object can be browsed from the web
    implements(ixmantissa.INavigableElement)

    schemaVersion = 2                  # There was a previous version,
                                       # but... let's ignore that.
    typeName = 'hyperbola_start'       # Database table name.

    privateApplication = dependsOn(webapp.PrivateApplication)

    powerupInterfaces = (ixmantissa.INavigableElement,)

    def getTabs(self):
        """
        Implementation of L{ixmantissa.INavigableElement.getTabs} which yields a
        'Hyperbola' tab pointing at this item.
        """
        return [webnav.Tab('Hyperbola', self.storeID, 0)]


    def getTopLevelFor(self, role):
        """
        Return an iterator of all top-level Blurbs in this store.

        @param role: a L{xmantissa.sharing.Role}.
        """
        blogs = self.store.query(Blurb, Blurb.parent == None)
        return sharing.asAccessibleTo(role, blogs)


    def createBlog(self, title, description):
        """
        Create a top-level BLOG-flavored Blurb with the given title and
        description, shared for edit with the owner of this store and for
        viewing with everyone, and return it.

        @param title: the blog title
        @type title: C{unicode}

        @param description: the blog description
        @type description: C{unicode}
        """
        store = self.store

        now = Time()
        blog = Blurb(store=self.store,
                     dateCreated=now,
                     dateLastEdited=now,
                     title=title,
                     body=description,
                     flavor=FLAVOR.BLOG,
                     author=sharing.getSelfRole(self.store))

        authorsRole = sharing.getPrimaryRole(store, title + u' blog', True)
        sharing.getSelfRole(store).becomeMemberOf(authorsRole)

        sharing.shareItem(blog, authorsRole, shareID=u'blog')

        everyoneRole = sharing.getEveryoneRole(store)
        sharing.shareItem(blog, everyoneRole, shareID=u'blog',
                          interfaces=[IViewable])

        # this should be configurable
        blog.permitChildren(everyoneRole, FLAVOR.BLOG_POST, IViewable)


def hyperbolaPublicPresence1to2(old):
    """
    Provide a simple, and probably wrong upgrader, from completely broken
    previous version of Hyperbola.  This is really just so that stores will
    open.
    """
    return old.upgradeVersion(old.typeName, 1, 2)

registerUpgrader(hyperbolaPublicPresence1to2,
                 HyperbolaPublicPresence.typeName, 1, 2)


# Notify the system that this Fragment class will be responsible of rendering
# the model. The 'self.original' attribute of the HyperbolaView instance is
# actually an instance of the HyperbolaPublicPresence class.
registerAdapter(HyperbolaView,
                HyperbolaPublicPresence,
                ixmantissa.INavigableFragment)
