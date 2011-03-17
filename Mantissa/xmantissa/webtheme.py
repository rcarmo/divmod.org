# -*- test-case-name: xmantissa.test.test_theme -*-

import sys, weakref

from zope.interface import implements

from twisted.python import reflect
from twisted.python.util import sibpath
from twisted.python.filepath import FilePath
from twisted.python.components import registerAdapter

from epsilon.structlike import record

from nevow.loaders import xmlfile
from nevow import inevow, tags, athena, page

from axiom.store import Store

from xmantissa import ixmantissa
from xmantissa.ixmantissa import ITemplateNameResolver
from xmantissa.offering import getInstalledOfferings, getOfferings

class ThemeCache(object):
    """
    Collects theme information from the filesystem and caches it.

    @ivar _getAllThemesCache: a list of all themes available on the
    filesystem, or None.

    @ivar _getInstalledThemesCache: a weak-key dictionary of site
    stores to lists of themes from all installed offerings on them.
    """
    def __init__(self):
        self.emptyCache()

    def emptyCache(self):
        """
        Remove cached themes.
        """
        self._getAllThemesCache = None
        self._getInstalledThemesCache = weakref.WeakKeyDictionary()


    def _realGetAllThemes(self):
        """
        Collect themes from all available offerings.
        """
        l = []
        for offering in getOfferings():
            l.extend(offering.themes)
        l.sort(key=lambda o: o.priority)
        l.reverse()
        return l


    def getAllThemes(self):
        """
        Collect themes from all available offerings, or (if called
        multiple times) return the previously collected list.
        """
        if self._getAllThemesCache is None:
            self._getAllThemesCache = self._realGetAllThemes()
        return self._getAllThemesCache


    def _realGetInstalledThemes(self, store):
        """
        Collect themes from all offerings installed on this store.
        """
        l = []
        for offering in getInstalledOfferings(store).itervalues():
            l.extend(offering.themes)
        l.sort(key=lambda o: o.priority)
        l.reverse()
        return l


    def getInstalledThemes(self, store):
        """
        Collect themes from all offerings installed on this store, or (if called
        multiple times) return the previously collected list.
        """
        if not store in self._getInstalledThemesCache:
            self._getInstalledThemesCache[store] = (self.
                                                 _realGetInstalledThemes(store))
        return self._getInstalledThemesCache[store]


#XXX this should be local to something, not process-global.
theThemeCache = ThemeCache()
getAllThemes = theThemeCache.getAllThemes
getInstalledThemes = theThemeCache.getInstalledThemes


class SiteTemplateResolver(object):
    """
    L{SiteTemplateResolver} implements L{ITemplateNameResolver} according to
    that site's policy for loading themes.  Use this class if you are
    displaying a public page at the top level of a site.

    Currently the only available policy is to load all installed themes in
    priority order.  However, in the future, this class may provide more
    sophisticated ways of loading the preferred theme, including interacting
    with administrative tools for interactively ordering theme preference.

    @ivar siteStore: a site store (preferably one with some offerings
    installed, if you want to actually get a template back)
    """
    implements(ITemplateNameResolver)

    def __init__(self, siteStore):
        self.siteStore = siteStore


    def getDocFactory(self, name, default=None):
        """
        Locate a L{nevow.inevow.IDocFactory} object with the given name from
        the themes installed on the site store and return it.
        """
        loader = None
        for theme in getInstalledThemes(self.siteStore):
            loader = theme.getDocFactory(name)
            if loader is not None:
                return loader
        return default

registerAdapter(SiteTemplateResolver, Store, ITemplateNameResolver)


_marker = object()
def _realGetLoader(n, default=_marker):
    """
    Search all themes for a template named C{n}, returning a loader
    for it if found. If not found and a default is passed, the default
    will be returned. Otherwise C{RuntimeError} will be raised.

    This function is deprecated in favor of using a L{ThemedElement}
    for your view code, or calling
    ITemplateNameResolver(userStore).getDocFactory.
    """
    for t in getAllThemes():
        fact = t.getDocFactory(n, None)
        if fact is not None:
            return fact
    if default is _marker:
        raise RuntimeError("No loader for %r anywhere" % (n,))
    return default

_loaderCache = {}
def _memoizedGetLoader(n, default=_marker):
    """

    Find a loader for a template named C{n}, returning C{default} if
    it is provided. Otherwise raise an error. This function caches
    loaders it finds.

    This function is deprecated in favor of using a L{ThemedElement}
    for your view code, or calling
    ITemplateNameResolver(userStore).getDocFactory.
    """
    if n not in _loaderCache:
        _loaderCache[n] = _realGetLoader(n, default)
    return _loaderCache[n]

getLoader = _memoizedGetLoader

class XHTMLDirectoryTheme(object):
    """
    I am a theme made up of a directory full of XHTML templates.

    The suggested use for this class is to make a subclass,
    C{YourThemeSubclass}, in a module in your Mantissa package, create a
    directory in your package called 'yourpackage/themes/<your theme name>',
    and then pass <your theme name> as the constructor to C{YourThemeSubclass}
    when passing it to the constructor of L{xmantissa.offering.Offering}.  You
    can then avoid calculating the path name in the constructor, since it will
    be calculated based on where your subclass was defined.

    @ivar directoryName: the name of the directory containing the appropriate
        template files.

    @ivar themeName: the name of the theme that this directory represents.
        This will be displayed to the user.

    @ivar stylesheetLocation: A C{list} of C{str} giving the path segments
        beneath the root at which the stylesheet for this theme is available,
        or C{None} if there is no applicable stylesheet.
    """
    implements(ixmantissa.ITemplateNameResolver)

    stylesheetLocation = None

    def __init__(self, themeName, priority=0, directoryName=None):
        """
        Create a theme based off of a directory full of XHTML templates.

        @param themeName: sets my themeName

        @param priority: an integer that affects the ordering of themes
        returned from L{getAllThemes}.

        @param directoryName: If None, calculates the directory name based on
        the module the class is defined in and the given theme name.  For a
        subclass C{bar.baz.FooTheme} defined in C{bar/baz.py} the instance
        C{FooTheme('qux')}, regardless of where it is created, will have a
        default directoryName of {bar/themes/qux/}.
        """

        self.themeName = themeName
        self.priority = priority
        self.cachedLoaders = {}
        if directoryName is None:
            self.directory = FilePath(
                sibpath(sys.modules[self.__class__.__module__].__file__,
                        'themes') + '/' + self.themeName)
        else:
            self.directory = FilePath(directoryName)
        self.directoryName = self.directory.path


    def head(self, request, website):
        """
        Provide content to include in the head of the document.  If you only
        need to provide a stylesheet, see L{stylesheetLocation}.  Otherwise,
        override this.

        @type request: L{inevow.IRequest} provider
        @param request: The request object for which this is a response.

        @param website: The site-wide L{xmantissa.website.WebSite} instance.
            Primarily of interest for its C{rootURL} method.

        @return: Anything providing or adaptable to L{nevow.inevow.IRenderer},
            or C{None} to include nothing.
        """
        stylesheet = self.stylesheetLocation
        if stylesheet is not None:
            root = website.rootURL(request)
            for segment in stylesheet:
                root = root.child(segment)
            return tags.link(rel='stylesheet', type='text/css', href=root)


    # ITemplateNameResolver
    def getDocFactory(self, fragmentName, default=None):
        """
        For a given fragment, return a loaded Nevow template.

        @param fragmentName: the name of the template (can include relative
        paths).

        @param default: a default loader; only used if provided and the
        given fragment name cannot be resolved.

        @return: A loaded Nevow template.
        @type return: L{nevow.loaders.xmlfile}
        """
        if fragmentName in self.cachedLoaders:
            return self.cachedLoaders[fragmentName]
        segments = fragmentName.split('/')
        segments[-1] += '.html'
        file = self.directory
        for segment in segments:
            file = file.child(segment)
        if file.exists():
            loader = xmlfile(file.path)
            self.cachedLoaders[fragmentName] = loader
            return loader
        return default



class MantissaTheme(XHTMLDirectoryTheme):
    """
    Basic Mantissa-provided theme.

    Most templates in the I{base} theme will usually be satisfied from this
    theme provider.
    """
    stylesheetLocation = ['static', 'mantissa-base', 'mantissa.css']



class ThemedDocumentFactory(record('fragmentName resolverAttribute')):
    """
    A descriptor which finds a template loader based on the Mantissa theme
    system.

    Use this to have the appropriate template loaded automatically at the time
    of first access::

        class YourElement(Element):
            '''
            An element for showing something.
            '''
            docFactory = ThemedDocumentFactory('template-name', 'userStore')

            def __init__(self, store):
                self.userStore = store


    When C{docFactory} is looked up on an instance of YourElement, the
    ITemplateNameResolver powerup on its C{'userStore'} attribute will
    be loaded and asked for the C{'template-name'} template loader.  The
    C{docFactory} attribute access will result in the object in which
    this results.

    @ivar fragmentName: A C{str} giving the name of the template which should
        be loaded.
    @ivar resolverAttribute: A C{str} giving the name of the attribute on
        instances which is adaptable to L{ITemplateNameResolver}.
    """
    def __get__(self, oself, type):
        """
        Get the document loader for C{self.fragmentName}.
        """
        resolver = ITemplateNameResolver(
            getattr(oself, self.resolverAttribute))
        return resolver.getDocFactory(self.fragmentName)



class _ThemedMixin(object):
    """
    Mixin for L{nevow.inevow.IRenderer} implementations which want to use the
    theme system.
    """

    implements(ixmantissa.ITemplateNameResolver)

    def __init__(self, fragmentParent=None):
        """
        Create a themed fragment with the given parent.

        @param fragmentParent: An object to pass to C{setFragmentParent}.  If
        not None, C{self.setFragmentParent} is called immediately.  It is
        suggested but not required that you set this here; if not, the
        resulting fragment will be initialized in an inconsistent state.  You
        must call setFragmentParent to correct this before this fragment is
        rendered.
        """
        super(_ThemedMixin, self).__init__()
        if fragmentParent is not None:
            self.setFragmentParent(fragmentParent)


    def head(self):
        """
        Don't do anything.
        """

    def rend(self, context, data):
        """
        Automatically retrieve my C{docFactory} based on C{self.fragmentName}
        before invoking L{athena.LiveElement.rend}.
        """
        if self.docFactory is None:
            self.docFactory = self.getDocFactory(self.fragmentName)
        return super(_ThemedMixin, self).rend(context, data)


    def pythonClass(self, request, tag):
        """
        This renderer is available on all themed fragments.  It returns the fully
        qualified python name of the class of the fragment being rendered.
        """
        return reflect.qual(self.__class__)
    page.renderer(pythonClass)


    def render_pythonClass(self, ctx, data):
        return self.pythonClass(inevow.IRequest(ctx), ctx.tag)


    # ITemplateNameResolver
    def getDocFactory(self, fragmentName, default=None):
        f = getattr(self.page, "getDocFactory", getLoader)
        return f(fragmentName, default)



class ThemedFragment(_ThemedMixin, athena.LiveFragment):
    """
    Subclass me to create a LiveFragment which supports automatic
    theming. (Deprecated)

    @ivar fragmentName: A short string naming the template from which the
    docFactory for this fragment should be loaded.

    @see ThemedElement
    """
    fragmentName = 'fragment-no-fragment-name-specified'



class ThemedElement(_ThemedMixin, athena.LiveElement):
    """
    Subclass me to create a LiveElement which supports automatic theming.

    @ivar fragmentName: A short string naming the template from which the
    docFactory for this fragment should be loaded.
    """
    fragmentName = 'element-no-fragment-name-specified'
