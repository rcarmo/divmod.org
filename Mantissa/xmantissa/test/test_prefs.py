from zope.interface import implements

from twisted.trial.unittest import TestCase

from axiom.item import Item
from axiom.store import Store
from axiom import attributes
from axiom.dependency import installOn

from xmantissa import prefs, ixmantissa, liveform

class WidgetShopPrefCollection(Item, prefs.PreferenceCollectionMixin):
    """
    Basic L{xmantissa.ixmantissa.IPreferenceCollection}, with a single
    preference, C{preferredWidget}
    """
    implements(ixmantissa.IPreferenceCollection)

    installedOn = attributes.reference()
    preferredWidget = attributes.text()
    powerupInterfaces = (ixmantissa.IPreferenceCollection,)

    def getPreferenceParameters(self):
        return (liveform.Parameter('preferredWidget',
                                    liveform.TEXT_INPUT,
                                    unicode,
                                    'Preferred Widget'),)

class PreferencesTestCase(TestCase):
    """
    Test case for basic preference functionality
    """

    def testAggregation(self):
        """
        Assert that L{xmantissa.prefs.PreferenceAggregator} gives us
        the right values for the preference attributes on L{WidgetShopPrefCollection}
        """
        store = Store()

        agg = prefs.PreferenceAggregator(store=store)
        installOn(agg, store)

        coll = WidgetShopPrefCollection(store=store)
        installOn(coll, store)

        coll.preferredWidget = u'Foo'

        self.assertEqual(agg.getPreferenceValue('preferredWidget'), 'Foo')

        coll.preferredWidget = u'Bar'

        self.assertEqual(agg.getPreferenceValue('preferredWidget'), 'Bar')


    def testGetPreferences(self):
        """
        Test that L{prefs.PreferenceCollectionMixin.getPreferences} works
        """
        class TrivialPreferenceCollection(prefs.PreferenceCollectionMixin):
            foo = 'bar'
            def getPreferenceParameters(self):
                return (liveform.Parameter('foo', liveform.TEXT_INPUT, str),)

        self.assertEqual(TrivialPreferenceCollection().getPreferences(),
                         {'foo': 'bar'})


    def testGetPreferencesNone(self):
        """
        Test that L{prefs.PreferenceCollectionMixin.getPreferences} does the
        right thing when the preference collection returns None from
        C{getPreferenceParameters}
        """
        class TrivialPreferenceCollection(prefs.PreferenceCollectionMixin):
            def getPreferenceParameters(self):
                return None

        self.assertEqual(TrivialPreferenceCollection().getPreferences(), {})
