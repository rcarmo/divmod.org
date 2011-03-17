# -*- test-case-name: xmantissa.test.test_webnav -*-

from epsilon.structlike import record

from zope.interface import implements

from nevow.inevow import IQ
from nevow import url

from nevow.stan import NodeNotFound

from xmantissa.ixmantissa import ITab
from xmantissa.fragmentutils import dictFillSlots

class TabMisconfiguration(Exception):
    def __init__(self, info, tab):
        Exception.__init__(
            self,
            "Inconsistent tab item factory information",
            info, tab)

TabInfo = record('priority storeID children linkURL authoritative',
                 authoritative=None)

class Tab(object):
    """
    Represent part or all of the layout of a single navigation tab.

    @ivar name: This tab's name.

    @type storeID: C{int}
    @ivar storeID: The Axiom store identifier of the Item to which the user
    should be directed when this tab is activated.

    @ivar priority: A float between 0 and 1 indicating the relative ordering of
    this tab amongst its peers.  Higher priorities sort sooner.

    @ivar children: A tuple of tabs beneath this one.

    @ivar authoritative: A flag indicating whether this instance of the
    conceptual tab with this name takes precedent over any other instance of
    the conceptual tab with this name.  It is an error for two instances of the
    same conceptual tab to be authoritative.

    @type linkURL: C{NoneType} or C{str}
    @ivar linkURL: If not C{None}, the location to which the user should be
    directed when this tab is activated.  This will override whatever value
    is supplied for C{storeID}.
    """

    _item = None
    implements(ITab)

    def __init__(self, name, storeID, priority, children=(),
                 authoritative=True, linkURL=None):
        self.name = name
        self.storeID = storeID
        self.priority = priority
        self.children = tuple(children)
        self.authoritative = authoritative
        self.linkURL = linkURL

    def __repr__(self):
        return '<%s%s %r/%0.3f %r [%r]>' % (self.authoritative and '*' or '',
                                            self.__class__.__name__,
                                            self.name,
                                            self.priority,
                                            self.storeID,
                                            self.children)

    def __iter__(self):
        raise TypeError("%r are not iterable" % (self.__class__.__name__,))

    def __getitem__(self, key):
        """Retrieve a sub-tab from this tab by name.
        """
        tabs = [t for t in self.children if t.name == key]
        assert len(tabs) < 2, "children mis-specified for " + repr(self)
        if tabs:
            return tabs[0]
        raise KeyError(key)

    def pathFromItem(self, item, avatar):
        """
        @param item: A thing that we linked to, and such.

        @return: a list of [child, grandchild, great-grandchild, ...] that
        indicates a path from me to the navigation for that item, or [] if
        there is no path from here to there.
        """
        for subnav in self.children:
            subpath = subnav.pathFromItem(item, avatar)
            if subpath:
                subpath.insert(0, self)
                return subpath
        else:
            myItem = self.loadForAvatar(avatar)
            if myItem is item:
                return [self]
        return []

def getTabs(navElements):
    # XXX TODO: multiple levels of nesting, this is hard-coded to 2.
    # Map primary tab names to a TabInfo
    primary = {}

    # Merge tab information from all nav plugins into one big structure
    for plg in navElements:
        for tab in plg.getTabs():
            if tab.name not in primary:
                primary[tab.name] = TabInfo(
                    priority=tab.priority,
                    storeID=tab.storeID,
                    children=list(tab.children),
                    linkURL=tab.linkURL)
            else:
                info = primary[tab.name]

                if info.authoritative:
                    if tab.authoritative:
                        raise TabMisconfiguration(info, tab)
                else:
                    if tab.authoritative:
                        info.authoritative = True
                        info.priority = tab.priority
                        info.storeID = tab.storeID
                        info.linkURL = tab.linkURL
                info.children.extend(tab.children)

    # Sort the tabs and their children by their priority
    def key(o):
        return -o.priority

    resultTabs = []

    for (name, info) in primary.iteritems():
        info.children.sort(key=key)

        resultTabs.append(
            Tab(name, info.storeID, info.priority, info.children,
                linkURL=info.linkURL))

    resultTabs.sort(key=key)

    return resultTabs

def setTabURLs(tabs, webTranslator):
    """
    Sets the C{linkURL} attribute on each L{Tab} instance
    in C{tabs} that does not already have it set

    @param tabs: sequence of L{Tab} instances
    @param webTranslator: L{xmantissa.ixmantissa.IWebTranslator}
                          implementor

    @return: None
    """

    for tab in tabs:
        if not tab.linkURL:
            tab.linkURL = webTranslator.linkTo(tab.storeID)
        setTabURLs(tab.children, webTranslator)

def getSelectedTab(tabs, forURL):
    """
    Returns the tab that should be selected when the current
    resource lives at C{forURL}.  Call me after L{setTabURLs}

    @param tabs: sequence of L{Tab} instances
    @param forURL: L{nevow.url.URL}

    @return: L{Tab} instance
    """

    flatTabs = []

    def flatten(tabs):
        for t in tabs:
            flatTabs.append(t)
            flatten(t.children)

    flatten(tabs)
    forURL = '/' + forURL.path

    for t in flatTabs:
        if forURL == t.linkURL:
            return t

    flatTabs.sort(key=lambda t: len(t.linkURL), reverse=True)

    for t in flatTabs:
        if not t.linkURL.endswith('/'):
            linkURL = t.linkURL + '/'
        else:
            linkURL = t.linkURL

        if forURL.startswith(linkURL):
            return t



def startMenu(translator, navigation, tag):
    """
    Drop-down menu-style navigation view.

    For each primary navigation element available, a copy of the I{tab}
    pattern will be loaded from the tag.  It will have its I{href} slot
    filled with the URL for that navigation item.  It will have its I{name}
    slot filled with the user-visible name of the navigation element.  It
    will have its I{kids} slot filled with a list of secondary navigation
    for that element.

    For each secondary navigation element available beneath each primary
    navigation element, a copy of the I{subtabs} pattern will be loaded
    from the tag.  It will have its I{kids} slot filled with a self-similar
    structure.

    @type translator: L{IWebTranslator} provider
    @type navigation: L{list} of L{Tab}

    @rtype: {nevow.stan.Tag}
    """
    setTabURLs(navigation, translator)
    getp = IQ(tag).onePattern

    def fillSlots(tabs):
        for tab in tabs:
            if tab.children:
                kids = getp('subtabs').fillSlots('kids', fillSlots(tab.children))
            else:
                kids = ''

            yield dictFillSlots(getp('tab'), dict(href=tab.linkURL,
                                                  name=tab.name,
                                                  kids=kids))
    return tag.fillSlots('tabs', fillSlots(navigation))



def settingsLink(translator, settings, tag):
    """
    Render the URL of the settings page.
    """
    return tag[translator.linkTo(settings.storeID)]



# This is somewhat redundant with startMenu.  The selected/not feature of this
# renderer should be added to startMenu and then templates can just use that
# and this can be deleted.
def applicationNavigation(ctx, translator, navigation):
    """
    Horizontal, primary-only navigation view.

    For the navigation element currently being viewed, copies of the
    I{selected-app-tab} and I{selected-tab-contents} patterns will be
    loaded from the tag.  For all other navigation elements, copies of the
    I{app-tab} and I{tab-contents} patterns will be loaded.

    For either case, the former pattern will have its I{name} slot filled
    with the name of the navigation element and its I{tab-contents} slot
    filled with the latter pattern.  The latter pattern will have its
    I{href} slot filled with a link to the corresponding navigation
    element.

    The I{tabs} slot on the tag will be filled with all the
    I{selected-app-tab} or I{app-tab} pattern copies.

    @type ctx: L{nevow.context.WebContext}
    @type translator: L{IWebTranslator} provider
    @type navigation: L{list} of L{Tab}

    @rtype: {nevow.stan.Tag}
    """
    setTabURLs(navigation, translator)
    selectedTab = getSelectedTab(navigation,
                                 url.URL.fromContext(ctx))

    getp = IQ(ctx.tag).onePattern
    tabs = []

    for tab in navigation:
        if tab == selectedTab or selectedTab in tab.children:
            p = 'selected-app-tab'
            contentp = 'selected-tab-contents'
        else:
            p = 'app-tab'
            contentp = 'tab-contents'

        childTabs = []
        for subtab in tab.children:
            try:
                subtabp = getp("subtab")
            except NodeNotFound:
                continue
            childTabs.append(
                dictFillSlots(subtabp, {
                        'name': subtab.name,
                        'href': subtab.linkURL,
                        'tab-contents': getp("subtab-contents")
                        }))
        tabs.append(dictFillSlots(
                getp(p),
                {'name': tab.name,
                 'tab-contents': getp(contentp).fillSlots(
                        'href', tab.linkURL),
                 'subtabs': childTabs}))

    ctx.tag.fillSlots('tabs', tabs)
    return ctx.tag
