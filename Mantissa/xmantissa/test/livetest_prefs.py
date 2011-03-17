from axiom.store import Store
from axiom.dependency import installOn

from nevow.livetrial.testcase import TestCase
from nevow.athena import expose

from xmantissa import prefs


class _PrefMixin(object):
    def getWidgetDocument(self):
        s = Store()

        self.dpc = prefs.DefaultPreferenceCollection(store=s)
        installOn(s, self.dpc)

        f = prefs.PreferenceCollectionFragment(self.dpc)
        class Tab:
            name = ''
            children = ()

        f.tab = Tab
        f.setFragmentParent(self)
        return f


class GeneralPrefs(_PrefMixin, TestCase):
    """
    Test case which renders L{xmantissa.ixmantissa.DefaultPreferenceCollection}
    and ensures that values changed client-side are correctly persisted
    """
    jsClass = u'Mantissa.Test.GeneralPrefs'

    def checkPersisted(self, itemsPerPage, timezone):
        """
        Assert that our preference collection has had its C{itemsPerPage}
        and C{timezone} attributes set to C{itemsPerPage} and C{timezone}.
        Called after the deferred returned by the liveform controller's
        C{submit} method has fired
        """
        self.assertEquals(self.dpc.itemsPerPage, itemsPerPage)
        self.assertEquals(self.dpc.timezone, timezone)
    expose(checkPersisted)


class PrefCollection(_PrefMixin, TestCase):
    """
    Test case which renders L{xmantissa.ixmantissa.DefaultPreferenceCollection}
    and makes sure that the form appears after submit.
    """
    jsClass = u'Mantissa.Test.PrefCollectionTestCase'
