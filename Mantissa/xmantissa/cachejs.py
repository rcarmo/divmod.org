# -*- test-case-name: xmantissa.test.test_cachejs -*-
"""
This module implements a strategy for allowing the browser to cache
JavaScript modules served by Athena.  It's not entirely standalone, as it
requires some cooperation from L{xmantissa.website}, specifically
L{xmantissa.website.MantissaLivePage}.
"""

import sha

from zope.interface import implements

from twisted.python.filepath import FilePath

from nevow.inevow import IResource
from nevow import athena
from nevow import static
from nevow.rend import NotFound, FourOhFour


class CachedJSModule(object):
    """
    Various bits of cached information about a JavaScript module.

    @ivar moduleName: A JavaScript module name, e.g. 'Foo.Bar'.
    @type moduleName: C{str}.

    @ivar filePath: The path to the module on the filesystem.
    @type filePath: L{FilePath}.

    @ivar lastModified: The mtime of L{filePath}, as a POSIX timestamp.
    @type lastModified: C{int}.
    """

    def __init__(self, moduleName, filePath):
        """
        Create a CachedJSModule.
        """
        self.moduleName = moduleName
        self.filePath = filePath
        self.lastModified = 0
        self.maybeUpdate()


    def wasModified(self):
        """
        Check to see if this module has been modified on disk since the last
        time it was cached.

        @return: True if it has been modified, False if not.
        """
        self.filePath.restat()
        mtime = self.filePath.getmtime()
        if mtime >= self.lastModified:
            return True
        else:
            return False


    def maybeUpdate(self):
        """
        Check this cache entry and update it if any filesystem information has
        changed.
        """
        if self.wasModified():
            self.lastModified = self.filePath.getmtime()
            self.fileContents = self.filePath.getContent()
            self.hashValue = sha.new(self.fileContents).hexdigest()



class HashedJSModuleProvider(object):
    """
    An Athena module-serving resource which handles hashed names instead of
    regular module names.

    @ivar moduleCache: a map of JS module names to CachedJSModule objects,
    representing the filesystem locations and contents of the modules.

    @ivar depsMemo: A memo of module dependencies.
    @type depsMemo: C{dict} of C{module name: dependent modules}
    """
    implements(IResource)

    def __init__(self):
        """
        Create a HashedJSModuleProvider.
        """
        self.moduleCache = {}
        self.depsMemo = {}


    def getModule(self, moduleName):
        """
        Retrieve a JavaScript module cache from the file path cache.

        @returns: Module cache for the named module.
        @rtype: L{CachedJSModule}
        """
        if moduleName not in self.moduleCache:
            modulePath = FilePath(
                athena.jsDeps.getModuleForName(moduleName)._cache.path)
            cachedModule = self.moduleCache[moduleName] = CachedJSModule(
                moduleName, modulePath)
        else:
            cachedModule = self.moduleCache[moduleName]
        return cachedModule


    # IResource
    def locateChild(self, ctx, segments):
        """
        Retrieve an L{inevow.IResource} to render the contents of the given
        module.
        """
        if len(segments) != 2:
            return NotFound
        hashCode, moduleName = segments
        cachedModule = self.getModule(moduleName)
        return static.Data(
            cachedModule.fileContents,
            'text/javascript', expires=(60 * 60 * 24 * 365 * 5)), []


    def renderHTTP(self, ctx):
        """
        There is no index of javascript modules; this resource is not
        renderable.
        """
        return FourOhFour()



theHashModuleProvider = HashedJSModuleProvider()

__all__ = ['HashedJSModuleProvider',
           'theHashModuleProvider']
