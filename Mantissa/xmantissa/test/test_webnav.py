# Copyright 2007 Divmod, Inc.
# See LICENSE file for details

"""
Tests for L{xmantissa.webnav}.
"""

from twisted.trial import unittest

from epsilon.structlike import record

from axiom.store import Store
from axiom.dependency import installOn

from nevow.url import URL
from nevow import tags, context
from nevow.testutil import FakeRequest

from xmantissa import webnav
from xmantissa.webapp import PrivateApplication



class FakeNavigator(record('tabs')):
    def getTabs(self):
        return self.tabs


class NavConfigTests(unittest.TestCase):
    """
    Tests for free functions in L{xmantissa.webnav}.
    """
    def test_tabMerge(self):
        """
        L{webnav.getTabs} should combine tabs from the L{INavigableElement}
        providers passed to it into a single structure.  It should preserve the
        attributes of all of the tabs and order them and their children by
        priority.
        """
        nav = webnav.getTabs([
                FakeNavigator([webnav.Tab('Hello', 1, 0.5,
                                          [webnav.Tab('Super', 2, 1.0, (), False, '/Super/2'),
                                           webnav.Tab('Mega', 3, 0.5, (), False, '/Mega/3')],
                                          False, '/Hello/1')]),
                FakeNavigator([webnav.Tab('Hello', 4, 1.,
                                          [webnav.Tab('Ultra', 5, 0.75, (), False, '/Ultra/5'),
                                           webnav.Tab('Hyper', 6, 0.25, (), False, '/Hyper/6')],
                                          True, '/Hello/4'),
                               webnav.Tab('Goodbye', 7, 0.9, (), True, '/Goodbye/7')])])

        hello, goodbye = nav
        self.assertEqual(hello.name, 'Hello')
        self.assertEqual(hello.storeID, 4)
        self.assertEqual(hello.priority, 1.0)
        self.assertEqual(hello.authoritative,True)
        self.assertEqual(hello.linkURL, '/Hello/4')

        super, ultra, mega, hyper = hello.children
        self.assertEqual(super.name, 'Super')
        self.assertEqual(super.storeID, 2)
        self.assertEqual(super.priority, 1.0)
        self.assertEqual(super.authoritative, False)
        self.assertEqual(super.linkURL, '/Super/2')

        self.assertEqual(ultra.name, 'Ultra')
        self.assertEqual(ultra.storeID, 5)
        self.assertEqual(ultra.priority, 0.75)
        self.assertEqual(ultra.authoritative, False)
        self.assertEqual(ultra.linkURL, '/Ultra/5')

        self.assertEqual(mega.name, 'Mega')
        self.assertEqual(mega.storeID, 3)
        self.assertEqual(mega.priority, 0.5)
        self.assertEqual(mega.authoritative, False)
        self.assertEqual(mega.linkURL, '/Mega/3')

        self.assertEqual(hyper.name, 'Hyper')
        self.assertEqual(hyper.storeID, 6)
        self.assertEqual(hyper.priority, 0.25)
        self.assertEqual(hyper.authoritative, False)
        self.assertEqual(hyper.linkURL, '/Hyper/6')

        self.assertEqual(goodbye.name, 'Goodbye')
        self.assertEqual(goodbye.storeID, 7)
        self.assertEqual(goodbye.priority, 0.9)
        self.assertEqual(goodbye.authoritative, True)
        self.assertEqual(goodbye.linkURL, '/Goodbye/7')


    def test_setTabURLs(self):
        """
        Check that L{webnav.setTabURLs} correctly sets the C{linkURL}
        attribute of L{webnav.Tab} instances to the result of
        passing tab.storeID to L{xmantissa.ixmantissa.IWebTranslator.linkTo}
        if C{linkURL} is not set, and that it leaves it alone if it is
        """

        s = Store()

        privapp = PrivateApplication(store=s)
        installOn(privapp,s)

        tabs = [webnav.Tab('PrivateApplication', privapp.storeID, 0),
                webnav.Tab('Something Else', None, 0, linkURL='/foo/bar')]

        webnav.setTabURLs(tabs, privapp)

        self.assertEqual(tabs[0].linkURL, privapp.linkTo(privapp.storeID))
        self.assertEqual(tabs[1].linkURL, '/foo/bar')


    def test_getSelectedTabExactMatch(self):
        """
        Check that L{webnav.getSelectedTab} returns the tab whose C{linkURL}
        attribute exactly matches the path of the L{nevow.url.URL} it is passed
        """

        tabs = list(webnav.Tab(str(i), None, 0, linkURL='/' + str(i))
                        for i in xrange(5))

        for (i, tab) in enumerate(tabs):
            selected = webnav.getSelectedTab(tabs, URL.fromString(tab.linkURL))
            self.assertIdentical(selected, tab)

        selected = webnav.getSelectedTab(tabs, URL.fromString('/XYZ'))
        self.failIf(selected)


    def test_getSelectedTabPrefixMatch(self):
        """
        Check that L{webnav.getSelectedTab} returns the tab whose C{linkURL}
        attribute contains the longest prefix of path segments that appears
        at the beginning of the L{nevow.url.URL} it is passed (if there is not
        an exact match)
        """

        tabs = [webnav.Tab('thing1', None, 0, linkURL='/a/b/c/d'),
                webnav.Tab('thing2', None, 0, linkURL='/a/b/c')]

        def assertSelected(tab):
            selected = webnav.getSelectedTab(tabs, URL.fromString('/a/b/c/d/e'))
            self.assertIdentical(selected, tab)

        assertSelected(tabs[0])
        tabs.reverse()
        assertSelected(tabs[1])

        tabs.append(webnav.Tab('thing3', None, 0, linkURL='a/b/c/e/e'))
        assertSelected(tabs[1])

        t = webnav.Tab('thing4', None, 0, linkURL='/a/b/c/d/e')
        tabs.append(t)
        assertSelected(t)



class FakeTranslator(object):
    """
    A dumb translator which follows a very simple translation rule and can only
    translate in one direction.
    """
    def linkTo(self, obj):
        """
        Return a fake link based on the given object.
        """
        return '/link/' + str(obj)



class RendererTests(unittest.TestCase):
    """
    Tests for certain free functions in L{xmantissa.webnav} which render
    different things.
    """
    def test_startMenuSetsTabURLs(self):
        """
        L{Tabs<Tab>} which have C{None} for a C{linkURL} attribute should have
        a value set for that attribute based on the L{IWebTranslator} passed to
        L{startMenu}.
        """
        tab = webnav.Tab('alpha', 123, 0)
        webnav.startMenu(FakeTranslator(), [tab], tags.span())
        self.assertEqual(tab.linkURL, '/link/123')


    def test_startMenuRenders(self):
        """
        Test that the L{startMenu} renderer creates a tag for each tab, filling
        its I{href}, I{name}, and I{kids} slots.
        """
        tabs = [
            webnav.Tab('alpha', 123, 0),
            webnav.Tab('beta', 234, 0)]
        node = tags.span[tags.div(pattern='tab')]

        tag = webnav.startMenu(FakeTranslator(), tabs, node)
        self.assertEqual(tag.tagName, 'span')
        navTags = list(tag.slotData['tabs'])
        self.assertEqual(len(navTags), 2)
        alpha, beta = navTags
        self.assertEqual(alpha.slotData['name'], 'alpha')
        self.assertEqual(alpha.slotData['href'], '/link/123')
        self.assertEqual(alpha.slotData['kids'], '')
        self.assertEqual(beta.slotData['name'], 'beta')
        self.assertEqual(beta.slotData['href'], '/link/234')
        self.assertEqual(beta.slotData['kids'], '')


    def test_settingsLink(self):
        """
        L{settingsLink} should add a link to the settings item supplied as a
        child of the tag supplied.
        """
        self.storeID = 123
        node = tags.span()
        tag = webnav.settingsLink(FakeTranslator(), self, node)
        self.assertEqual(tag.tagName, 'span')
        self.assertEqual(tag.children, ['/link/123'])


    def _renderAppNav(self, tabs, template=None):
        """
        Render application navigation and return the resulting tag.

        @param template: a Tag containing a template for navigation.
        """
        if template is None:
            template = tags.span[
                tags.div(pattern='app-tab'),
                tags.div(pattern='tab-contents')]
        ctx = context.WebContext(tag=template)
        request = FakeRequest()
        ctx.remember(request)
        return webnav.applicationNavigation(ctx, FakeTranslator(), tabs)


    def test_applicationNavigation(self):
        """
        Test that the L{applicationNavigation} renderer creates a tag for each
        tab, fillings I{name} and I{tab-contents} slots.
        """
        tag = self._renderAppNav([
            webnav.Tab('alpha', 123, 0),
            webnav.Tab('beta', 234, 0)])
        self.assertEqual(tag.tagName, 'span')
        navTags = list(tag.slotData['tabs'])
        self.assertEqual(len(navTags), 2)
        alpha, beta = navTags
        self.assertEqual(alpha.slotData['name'], 'alpha')
        alphaContents = alpha.slotData['tab-contents']
        self.assertEqual(alphaContents.slotData['href'], '/link/123')
        self.assertEqual(beta.slotData['name'], 'beta')
        betaContents = beta.slotData['tab-contents']
        self.assertEqual(betaContents.slotData['href'], '/link/234')


    def test_applicationNavigationChildren(self):
        """
        The L{applicationNavigation} renderer should fill the 'subtabs' slot
        with copies of the 'subtab' pattern for each tab, if that pattern is
        present.  (This is only tested to one level of depth because we
        currently only support one level of depth.)
        """
        tag = self._renderAppNav(
            [webnav.Tab('alpha', 123, 0),
             webnav.Tab('beta', 234, 0, children=[
                        webnav.Tab('gamma', 345, 0),
                        webnav.Tab('delta', 456, 0)])],
            tags.span[tags.div(pattern='app-tab'),
                      tags.div(pattern='tab-contents'),
                      tags.div(pattern='subtab'),
                      tags.div(pattern='subtab-contents',
                               class_='subtab-contents-class')])
        navTags = list(tag.slotData['tabs'])
        self.assertEqual(len(navTags), 2)
        alpha, beta = navTags
        self.assertEqual(alpha.slotData['subtabs'], [])
        self.assertEqual(len(beta.slotData['subtabs']), 2)
        subtab1 = beta.slotData['subtabs'][0]
        self.assertEqual(subtab1.slotData['name'],
                         'gamma')
        self.assertEqual(subtab1.slotData['href'], '/link/345')
        self.assertEqual(subtab1.slotData['tab-contents'].attributes['class'],
                         'subtab-contents-class')
        subtab2 = beta.slotData['subtabs'][1]
        self.assertEqual(subtab2.slotData['name'],
                         'delta')
        self.assertEqual(subtab2.slotData['href'], '/link/456')
        self.assertEqual(subtab2.slotData['tab-contents'].attributes['class'],
                         'subtab-contents-class')


    def test_applicationNavigationMissingSubtabsPattern(self):
        """
        The L{applicationNavigation} renderer should fill the 'subtabs' slot
        with the empty list if the 'subtabs' pattern is not found.  This is to
        ensure that it remains compatible with older customized 'shell'
        templates.
        """
        tag = self._renderAppNav([
                webnav.Tab("alpha", 123, 0,
                           children=[webnav.Tab("beta", 234, 0)])])
        navTags = list(tag.slotData['tabs'])
        self.assertEqual(navTags[0].slotData['subtabs'], [])
