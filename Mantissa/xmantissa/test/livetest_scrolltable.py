from nevow.athena import expose
from nevow.livetrial.testcase import TestCase

from axiom.item import Item
from axiom.store import Store
from axiom.attributes import integer
from axiom.dependency import installOn

from xmantissa.scrolltable import SequenceScrollingFragment
from xmantissa.webtheme import getLoader
from xmantissa.webapp import PrivateApplication


class ScrollElement(Item):
    """
    Dummy item used to populate scrolltables for the scrolltable tests.
    """
    column = integer()



class ScrollTableModelTestCase(TestCase):
    """
    Tests for the scrolltable's model class.
    """
    jsClass = u'Mantissa.Test.ScrollTableModelTestCase'



class ScrollTableWidgetTestCase(TestCase):
    """
    Tests for the scrolltable's view class.
    """
    jsClass = u'Mantissa.Test.ScrollTableViewTestCase'

    def __init__(self):
        TestCase.__init__(self)
        self.perTestData = {}


    def getScrollingWidget(self, key, rowCount=10):
        store = Store()
        installOn(PrivateApplication(store=store), store)
        elements = [ScrollElement(store=store, column=i) for i in range(rowCount)]
        columns = [ScrollElement.column]
        f = SequenceScrollingFragment(store, elements, columns)
        f.docFactory = getLoader(f.fragmentName)
        f.setFragmentParent(self)
        self.perTestData[key] = (store, elements, f)
        return f
    expose(getScrollingWidget)


    def changeRowCount(self, key, n):
        store, elements, fragment = self.perTestData[key]
        elements[:] = [ScrollElement(store=store, column=i) for i in range(n)]
    expose(changeRowCount)



class ScrollTableActionsTestCase(ScrollTableWidgetTestCase):
    """
    Tests for scrolltable actions
    """
    jsClass = u'Mantissa.Test.ScrollTableActionsTestCase'

    def getScrollingWidget(self, key, *a, **kw):
        f = ScrollTableWidgetTestCase.getScrollingWidget(self, key, *a, **kw)
        f.jsClass = u'Mantissa.Test.ScrollTableWithActions'

        # close over "key" because actions can't supply additional
        # arguments, and there isn't a use case outside of this test
        def action_delete(scrollElement):
            elements = self.perTestData[key][1]
            elements.remove(scrollElement)

        f.action_delete = action_delete
        return f
    expose(getScrollingWidget)



class ScrollTablePlaceholderRowsTestCase(ScrollTableWidgetTestCase):
    """
    Tests for the scrolltable's placeholder rows
    """
    jsClass = u'Mantissa.Test.ScrollTablePlaceholderRowsTestCase'
