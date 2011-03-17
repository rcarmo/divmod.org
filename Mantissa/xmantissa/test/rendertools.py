# -*- test-case-name: xmantissa.test.test_rendertools -*-

"""
Simple Nevow-related rendering helpers for use in view tests only.
"""

from nevow.rend import Page
from nevow.athena import LivePage
from nevow.loaders import stan
from nevow.testutil import FakeRequest
from nevow.context import WovenContext
from nevow.inevow import IRequest


class TagTestingMixin:
    """
    Mixin defining various useful tag-related testing functionality.
    """
    def assertTag(self, tag, name, attributes, children):
        """
        Assert that the given tag has the given name, attributes, and children.
        """
        self.assertEqual(tag.tagName, name)
        self.assertEqual(tag.attributes, attributes)
        self.assertEqual(tag.children, children)



def _makeContext():
    """
    Create the request and context objects necessary for rendering a page.

    @return: A two-tuple of the created L{FakeRequest} and L{WovenContext},
    with the former remembered in the latter.
    """
    request = FakeRequest()
    context = WovenContext()
    context.remember(request, IRequest)
    return (request, context)



def renderLiveFragment(fragment):
    """
    Render the given fragment in a LivePage.

    This can only work for fragments which can be rendered synchronously.
    Fragments which involve Deferreds will be silently rendered incompletely.

    @type fragment: L{nevow.athena.LiveFragment} or L{nevow.athena.LiveElement}
    @param fragment: The page component to render.

    @rtype: C{str}
    @return: The result of rendering the fragment.
    """
    page = LivePage(docFactory=stan(fragment))
    fragment.setFragmentParent(page)
    (request, context) = _makeContext()
    page.renderHTTP(context)
    page.action_close(context)
    return request.v



def renderPlainFragment(fragment):
    """
    same as L{render}, but expects an L{nevow.rend.Fragment} or any
    other L{nevow.inevow.IRenderer}
    """
    page = Page(docFactory=stan(fragment))
    (request, context) = _makeContext()
    page.renderHTTP(context)
    return request.v
