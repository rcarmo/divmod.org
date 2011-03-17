"""
An interactive demonstration of L{hyperbola.hyperblurb.BlogBlurbViewer}.

Run this test like this:
    $ twistd -n athena-widget --element=hyperbola.test.acceptance.blog.blog
    $ firefox http://localhost:8080/

This will display a blog, with some posts in it!
"""
from tempfile import mktemp

from axiom.store import Store
from axiom.plugins.mantissacmd import Mantissa
from axiom.plugins.userbasecmd import Create
from axiom.dependency import installOn

from xmantissa.sharing import getSelfRole

from hyperbola.hyperbola_view import BlogBlurbViewer, _docFactorify
from hyperbola.hyperbola_model import HyperbolaPublicPresence



def populate(siteStore):
    """
    Make a user with a blog and some blog posts.
    """
    Mantissa().installSite(siteStore, '/')
    userAccount = Create().addAccount(
        siteStore, u'testuser', u'localhost', u'asdf')
    userAccount.addLoginMethod(
        u'testuser', u'localhost', internal=True)

    userStore = userAccount.avatars.open()

    hpp = HyperbolaPublicPresence(store=userStore)
    installOn(hpp, userStore)
    hpp.createBlog(u'Title', u'Description')
    selfRole = getSelfRole(userStore)
    (blog,) = hpp.getTopLevelFor(selfRole)
    blog.post(u'Title', u'A pretty innocuous body', selfRole)
    blog.post(u'An HTML POST!',
              u'<div><h1>OMG A TITLE</h1><blockquote>A decent<p />post.<p />Several lines<p/>though.</blockquote></div>',
              selfRole)
    for i in xrange(60):
        blog.post(u'A post...', u'This is number %s' % (i+1,), selfRole)
    return blog



def blog():
    """
    Create a L{hyperbola.hyperblurb.BlurbViewerViewer}, looking at a
    blog with some posts in it.
    """
    store = Store(mktemp())
    blog = populate(store)
    fragment = BlogBlurbViewer(blog)
    _docFactorify(fragment)
    return fragment
