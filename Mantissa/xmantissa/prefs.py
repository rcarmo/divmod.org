# -*- test-case-name: xmantissa.test.historic -*-

import pytz

from zope.interface import implements

from twisted.python.components import registerAdapter

from nevow import athena, tags, loaders, inevow
from nevow.taglibrary import tabbedPane
from nevow.page import renderer

from axiom.item import Item
from axiom import attributes, upgrade

from xmantissa.webtheme import getLoader
from xmantissa.liveform import ChoiceParameter, LiveForm
from xmantissa import webnav, ixmantissa
from xmantissa.webgestalt import AuthenticationApplication

class PreferenceCollectionMixin:
    """
    Convenience mixin for L{xmantissa.ixmantissa.IPreferenceCollection}
    implementors.  Provides only the C{getPreferences} method.
    """

    def getPreferences(self):
        # this is basically a hack so that PreferenceAggregator can
        # continue work in a similar way
        d = {}
        for param in self.getPreferenceParameters() or ():
            d[param.name] = getattr(self, param.name)
        return d

class DefaultPreferenceCollection(Item, PreferenceCollectionMixin):
    """
    Badly named L{xmantissa.ixmantissa.IPreferenceCollection} which
    encapsulates basic preferences that are useful to Mantissa in
    various places, and probably to Mantissa-based applications as well.
    """

    implements(ixmantissa.IPreferenceCollection)

    typeName = 'mantissa_default_preference_collection'
    schemaVersion = 2

    installedOn = attributes.reference()

    itemsPerPage = attributes.integer(default=10)
    timezone = attributes.text(default=u'US/Eastern')

    powerupInterfaces = (ixmantissa.IPreferenceCollection,)

    def getPreferenceParameters(self):
        return (ChoiceParameter(
                    'timezone',
                    list((c, unicode(c, 'ascii'), c == self.timezone) for c
                            in pytz.common_timezones),
                    'Timezone'),
                ChoiceParameter(
                    'itemsPerPage',
                    list((c, c, c == self.itemsPerPage) for c in (10, 20, 30)),
                    'Items Per Page'))

    def getSections(self):
        authapp = self.store.findUnique(AuthenticationApplication, default=None)
        if authapp is None:
            return None
        return (authapp,)

    def getTabs(self):
        return (webnav.Tab('General', self.storeID, 1.0, authoritative=True),)


upgrade.registerAttributeCopyingUpgrader(DefaultPreferenceCollection, 1, 2)


class PreferenceCollectionLiveForm(LiveForm):
    """
    L{xmantissa.liveform.LiveForm} subclass which switches
    the docfactory, the jsClass, and overrides the submit
    button renderer.
    """
    jsClass = u'Mantissa.Preferences.PrefCollectionLiveForm'

    def __init__(self, *a, **k):
        super(PreferenceCollectionLiveForm, self).__init__(*a, **k)
        self.docFactory = getLoader('liveform-compact')

    def submitbutton(self, request, tag):
        return tags.input(type='submit', name='__submit__', value='Save')
    renderer(submitbutton)


class PreferenceCollectionFragment(athena.LiveElement):
    """
    L{inevow.IRenderer} adapter for L{xmantissa.ixmantissa.IPreferenceCollection}.
    """
    docFactory = loaders.stan(tags.directive('fragments'))
    liveFormClass = PreferenceCollectionLiveForm

    def __init__(self, collection):
        super(PreferenceCollectionFragment, self).__init__()
        self.collection = collection

    def fragments(self, req, tag):
        """
        Render our preference collection, any child preference
        collections we discover by looking at self.tab.children,
        and any fragments returned by its C{getSections} method.

        Subtabs and C{getSections} fragments are rendered as fieldsets
        inside the parent preference collection's tab.
        """
        f = self._collectionToLiveform()
        if f is not None:
            yield tags.fieldset[tags.legend[self.tab.name], f]

        for t in self.tab.children:
            f = inevow.IRenderer(
                    self.collection.store.getItemByID(t.storeID))
            f.tab = t
            if hasattr(f, 'setFragmentParent'):
                f.setFragmentParent(self)
            yield f

        for f in self.collection.getSections() or ():
            f = ixmantissa.INavigableFragment(f)
            f.setFragmentParent(self)
            f.docFactory = getLoader(f.fragmentName)
            yield tags.fieldset[tags.legend[f.title], f]
    renderer(fragments)

    def _collectionToLiveform(self):
        params = self.collection.getPreferenceParameters()
        if not params:
            return None
        f = self.liveFormClass(
                lambda **k: self._savePrefs(params, k),
                params,
                description=self.tab.name)
        f.setFragmentParent(self)
        return f

    def _savePrefs(self, params, values):
        for (k, v) in values.iteritems():
            setattr(self.collection, k, v)
        return self._collectionToLiveform()

# IRenderer(IPreferenceCollection)
#   -> PreferenceCollectionFragment, unless an adapter is registered for a
# specific IPreferenceCollection implementor
registerAdapter(PreferenceCollectionFragment,
                ixmantissa.IPreferenceCollection,
                inevow.IRenderer)

class PreferenceAggregator(Item):
    """
    L{xmantissa.ixmantissa.IPreferenceAggregator} implementor,
    which provides access to the values of preferences by name
    """
    implements(ixmantissa.IPreferenceAggregator)

    schemaVersion = 1
    typeName = 'preference_aggregator'

    _collections = attributes.inmemory()
    installedOn = attributes.reference()

    powerupInterfaces = (ixmantissa.IPreferenceAggregator,)

    def activate(self):
        self._collections = None

    # IPreferenceAggregator
    def getPreferenceCollections(self):
        if self._collections is None:
            self._collections = list(self.store.powerupsFor(ixmantissa.IPreferenceCollection))
        return self._collections

    def getPreferenceValue(self, key):
        for collection in self.getPreferenceCollections():
            for (_key, value) in collection.getPreferences().iteritems():
                if _key == key:
                    return value


class PreferenceEditor(athena.LiveElement):
    """
    L{xmantissa.ixmantissa.INavigableFragment} adapter for
    L{xmantissa.prefs.PreferenceAggregator}.  Responsible for
    rendering all installed L{xmantissa.ixmantissa.IPreferenceCollection}s
    """
    implements(ixmantissa.INavigableFragment)
    title = 'Settings'
    fragmentName = 'preference-editor'

    def __init__(self, aggregator):
        self.aggregator = aggregator
        super(PreferenceEditor, self).__init__()

    def tabbedPane(self, req, tag):
        """
        Render a tabbed pane tab for each top-level
        L{xmantissa.ixmantissa.IPreferenceCollection} tab
        """
        navigation = webnav.getTabs(self.aggregator.getPreferenceCollections())
        pages = list()
        for tab in navigation:
            f = inevow.IRenderer(
                    self.aggregator.store.getItemByID(tab.storeID))
            f.tab = tab
            if hasattr(f, 'setFragmentParent'):
                f.setFragmentParent(self)
            pages.append((tab.name, f))

        f = tabbedPane.TabbedPaneFragment(pages, name='preference-editor')
        f.setFragmentParent(self)
        return f
    renderer(tabbedPane)

    def head(self):
        return tabbedPane.tabbedPaneGlue.inlineCSS

registerAdapter(PreferenceEditor, PreferenceAggregator, ixmantissa.INavigableFragment)
