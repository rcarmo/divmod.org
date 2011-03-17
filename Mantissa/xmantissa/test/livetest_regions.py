"""
Nits for scrolltable region widget.
"""

from zope.interface import implements

from axiom.item import Item
from axiom import attributes
from axiom.store import Store

from nevow.livetrial.testcase import TestCase
from nevow.athena import expose

from xmantissa.ixmantissa import IWebTranslator
from xmantissa.scrolltable import ScrollingElement
from xmantissa.webtheme import getLoader

class FakeTranslator(object):
    """
    Translate webIDs deterministically for ease of testing.

    @ivar store: the axiom store to retrieve items from.
    """
    implements(IWebTranslator)

    def __init__(self, store):
        """
        Create a FakeTranslator from a given axiom store.
        """
        self.store = store


    def fromWebID(self, webID):
        """
        Load an item from a hashed storeID.
        """
        return self.store.getItemByID(int(webID.split('-')[-1]))


    def toWebID(self, item):
        """
        Convert an item into a string identifier by hashing its storeID.
        """
        return 'webID-' + str(item.storeID)



class SampleRowItem(Item):
    """
    A sample item to be used as rows in the tests.
    """
    value = attributes.integer()



class ScrollingElementTestCase(TestCase):
    """
    Nits for L{ScrollingElement}
    """
    jsClass = u'Mantissa.Test.TestRegionLive.ScrollingElementTestCase'

    def getScrollingElement(self, rowCount):
        """
        Get a L{ScrollingElement}
        """
        s = Store()
        for x in xrange(rowCount):
            SampleRowItem(value=(x + 1) * 50, store=s)
        scrollingElement = ScrollingElement(
            s, SampleRowItem, None, (SampleRowItem.value,), None, True,
            FakeTranslator(s))
        scrollingElement.setFragmentParent(self)
        scrollingElement.docFactory = getLoader(
            scrollingElement.fragmentName)
        return scrollingElement
    expose(getScrollingElement)
